"""Portable, verified, resumable copy of a finished archive onto a USB drive.

USB media is slow and error-prone, so this gives the guarantees people reach for
rsync to get — without depending on rsync (modern macOS ships *openrsync*, which
lacks ``--info=progress2`` / ``--partial`` / ``--checksum``, and Windows has no
rsync at all):

* **resume** — files already present with a matching size (and SHA-256 when
  ``thorough``) are skipped, so a re-run after a yanked USB picks up where it left
  off;
* **integrity** — every copied file is verified (size always; SHA-256 when
  ``thorough``) and recopied once on mismatch;
* **robustness** — copying reuses :func:`mia.core.ripper.copy_with_retry`
  (retry + backoff), already tested for flaky media.

Same ``Progress`` / cancel contract as the other workers, so it drops straight
into the GUI plumbing. A Windows ``robocopy`` fast-path can be added later.
"""

from __future__ import annotations

import hashlib
import os
import platform
import random
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .common import (
    Cancelled,
    CancelToken,
    Progress,
    ProgressCallback,
    check_cancel,
    emit,
    emit_debug,
    is_verbose,
)
from .ripper import copy_with_retry

# Parallel workers for the verify/copy pass. USB write bandwidth is the real
# ceiling; concurrency hides per-file latency (thousands of small DICOM files),
# it doesn't push past the device — so keep it modest.
_MAX_WORKERS = min(8, (os.cpu_count() or 4))
_PROGRESS_MIN_INTERVAL = 0.2  # seconds; throttle per-file emits

# How many random files to content-verify (SHA-256) when sampled verification
# is on. A failing drive corrupts broadly, so a small random sample reliably
# catches it: P(catch | fraction f corrupt) = 1 - (1-f)**N, so N≈64 gives ~96%
# detection of any 5%-corruption event for a few seconds of read-back — almost
# the assurance of hashing everything, at a tiny fraction of the cost. Full
# per-file hashing stays available via thorough=True.
DEFAULT_VERIFY_SAMPLE = 64


def free_space(path: str) -> int:
    """Free bytes on the volume that contains (the nearest existing parent of) path."""
    p = os.path.abspath(path)
    while p and not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    try:
        return shutil.disk_usage(p or os.sep).free
    except OSError:
        return 0


def dir_size(path: str) -> int:
    """Total bytes of all files under ``path``."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total


def _sha256(path: str, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _matches(src: str, dst: str, thorough: bool) -> bool:
    """Does dst already faithfully hold src? Size always; content when thorough."""
    try:
        if os.path.getsize(src) != os.path.getsize(dst):
            return False
    except OSError:
        return False
    if thorough:
        try:
            return _sha256(src) == _sha256(dst)
        except OSError:
            return False
    return True


@dataclass
class DeliverResult:
    dest: str
    total_files: int
    files_copied: int
    files_skipped: int
    failed: int
    bytes_copied: int
    elapsed: float
    thorough: bool
    content_verified: int = 0   # files checked by SHA-256 (all if thorough)
    failures: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        return self.failed == 0


def _native_bulk_copy(src: str, dest: str, *, total_files: int = 0,
                      progress: Optional[ProgressCallback] = None,
                      cancel: Optional[CancelToken] = None) -> bool:
    """Best-effort fast bulk copy with the OS's own tool (robocopy /MT on
    Windows, ditto on macOS, cp -a on Linux). Returns True if a tool ran to
    completion; False (tool missing/failed) so the verify pass copies it all.
    Raises Cancelled if the user cancels mid-copy. Integrity is NOT assumed —
    the verify/fill pass always runs afterwards.

    The tools don't expose per-file progress, and the obvious proxy (the drop
    in the destination volume's free space) jitters badly on USB/exFAT — free
    space doesn't update live as the tool writes, so a derived done/ETA bounces
    and reads as nonsense ("11974h"). So while the tool runs we emit an honest
    *indeterminate* "Copying… (elapsed)" event every couple of seconds: an
    animated bar with no fake percentage. The real determinate bar belongs to
    the verify/fill pass that follows, which counts actual files.

    When verbose mode is on, ditto gets ``-v`` so it streams a line per item to
    stderr; we forward those to the technical log (kind="debug") on a reader
    thread, which is exactly what's needed to see *which* file a slow USB copy
    is stalling on."""
    system = platform.system()
    verbose = is_verbose()
    if system == "Windows":
        cmd = ["robocopy", src, dest, "/E", "/MT:8", "/R:1", "/W:1",
               "/NFL", "/NDL", "/NJH", "/NP"]
        ok_codes = range(0, 8)            # robocopy: <8 == success
    elif system == "Darwin":
        # -v makes ditto name each item it copies (to stderr) — only worth the
        # noise when the user has asked for the verbose technical log.
        cmd = ["ditto", "-v", src, dest] if verbose else ["ditto", src, dest]
        ok_codes = (0,)
    elif system == "Linux":
        cmd = ["cp", "-a", src + "/.", dest + "/"]
        ok_codes = (0,)
    else:
        return False
    if shutil.which(cmd[0]) is None:
        return False
    emit_debug(progress, f"native copy: {' '.join(cmd)}", phase="copy")
    # Capture ditto's verbose stream so we can forward it; otherwise discard
    # both streams. (Only ditto streams useful per-file lines on -v here.)
    # Pass text/errors only when capturing — `errors` implicitly enables text
    # mode, which is meaningless (and confusing) for the DEVNULL path.
    capture = verbose and system == "Darwin"
    text_kw = dict(text=True, errors="replace") if capture else {}
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
            **text_kw)
    except OSError:
        return False

    reader: Optional[threading.Thread] = None
    if capture and proc.stderr is not None:
        def _forward(stream) -> None:
            try:
                for line in stream:
                    line = line.rstrip("\n")
                    if line:
                        emit_debug(progress, f"ditto: {line}", phase="copy")
            except (OSError, ValueError):
                pass  # stream closed when the proc is terminated — fine
        reader = threading.Thread(target=_forward, args=(proc.stderr,),
                                  daemon=True)
        reader.start()

    start = time.time()
    last_poll = 0.0
    try:
        while proc.poll() is None:
            if cancel is not None and cancel.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise Cancelled()
            now = time.time()
            if progress is not None and now - last_poll >= 2.0:
                last_poll = now
                # No note/percentage — an honest indeterminate tick. The GUI
                # builds the localized "Copying N files… (Xm elapsed)" status
                # from total/elapsed; the CLI shows a plain elapsed line.
                emit(progress, Progress(0, total_files, elapsed=now - start,
                                        phase="copy", indeterminate=True))
            time.sleep(0.2)
    except Cancelled:
        raise
    finally:
        if reader is not None:
            reader.join(timeout=2)  # let the last verbose lines flush
    elapsed = time.time() - start
    emit_debug(progress,
               f"native copy finished: rc={proc.returncode} in {elapsed:.1f}s",
               phase="copy")
    return proc.returncode in ok_codes


def copy_tree_verified(
    src: str,
    dest: str,
    *,
    thorough: bool = False,
    verify_sample: int = 0,
    prefer_native: bool = True,
    groups: Optional[List[Tuple[str, List[str]]]] = None,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> DeliverResult:
    """Copy every file under ``src`` into ``dest``, verifying and resuming.

    A native tool (robocopy/ditto/cp) does the bulk copy fast when available;
    then a parallel verify/fill pass guarantees every file is present and
    size-correct, copying anything the native tool missed. With no native tool
    the parallel pass does the whole copy itself.

    Content (SHA-256) verification has three levels: ``thorough=True`` hashes
    every file; ``verify_sample=N`` hashes N random files (cheap insurance that
    catches a broadly-failing drive — see ``DEFAULT_VERIFY_SAMPLE``); neither
    means size-only. Size verification can't detect a write that returned the
    right length but the wrong bytes (e.g. a counterfeit/fake-capacity stick),
    which is what the content sample is for.

    ``groups`` lets the caller announce progress in meaningful chunks (e.g. one
    per DICOM study): an ordered list of ``(label, [absolute source paths])``.
    The verify/fill pass then runs group-by-group, emitting the (already
    localized) ``label`` as an ``info`` milestone before each, while the overall
    bar still tracks every file. Files under ``src`` not in any group are copied
    last without a milestone. ``groups=None`` is the original flat behavior.
    To see per-group milestones tracking the *real* copy, pass
    ``prefer_native=False`` so the in-process pass does the copying.
    """
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    check_cancel(cancel)

    emit(progress, Progress(0, 0, kind="info", note=f"Preparing to copy to {dest}"))
    walk_start = time.time()
    files = []
    for dirpath, _, filenames in os.walk(src):
        for fn in filenames:
            files.append(os.path.join(dirpath, fn))
    total = len(files)
    start = time.time()
    emit_debug(progress, f"walked {total} files in {start - walk_start:.1f}s")

    # Pick the files to content-verify (SHA-256). thorough = all of them;
    # otherwise a random sample so a broadly-failing drive is still caught
    # cheaply. A set for O(1) per-file lookup in the pool.
    if thorough:
        sampled = set(files)
    elif verify_sample > 0 and files:
        sampled = set(random.sample(files, min(verify_sample, len(files))))
    else:
        sampled = set()
    if sampled and not thorough:
        emit_debug(progress, f"content-verifying {len(sampled)} of {total} "
                             "files (random sample)")

    # No upfront destination-tree pre-create: on slow USB/exFAT that mkdir storm
    # was minutes of dead time before the first byte moved. The native tool
    # makes its own dirs; the verify/fill pass makes each parent lazily (below).

    # Fast bulk copy with the OS tool (best-effort accelerator). It emits an
    # indeterminate "working" tick while running so the UI doesn't look frozen.
    if prefer_native:
        emit(progress, Progress(0, total, kind="info",
                                note=f"Fast-copying {total} files to {dest}…"))
        _native_bulk_copy(src, dest, total_files=total,
                          progress=progress, cancel=cancel)  # may raise Cancelled

    emit(progress, Progress(0, total, kind="info",
                            note=f"Verifying {total} files…"))
    verify_start = time.time()

    copied = skipped = failed = 0
    bytes_copied = 0
    failures: List[Tuple[str, str]] = []
    done = 0
    last_emit = 0.0

    def handle(sp: str) -> Tuple[str, str, int, Optional[str]]:
        """Returns (status, rel, nbytes, note). status in skip/copy/fail."""
        rel = os.path.relpath(sp, src)
        dp = os.path.join(dest, rel)
        deep = sp in sampled            # content-check this file, not just size
        if os.path.exists(dp) and _matches(sp, dp, deep):
            return ("skip", rel, 0, None)
        # Create the parent lazily (no upfront pre-create). exist_ok already
        # swallows the benign race between pool threads writing into the same
        # folder; a surviving OSError is real (e.g. a path component is a file,
        # or the drive is full/read-only) — count it as this file's failure so
        # one bad path doesn't abort the whole delivery.
        try:
            os.makedirs(os.path.dirname(dp), exist_ok=True)
        except OSError as e:
            return ("fail", rel, 0, f"could not create folder: {e}")
        emit_debug(progress, f"copying {rel}", phase="copy")  # per-file stream
        ok, note = copy_with_retry(sp, dp, cancel=cancel)
        verified = ok and _matches(sp, dp, deep)
        if ok and not verified:                 # one retry on a bad write
            ok, note = copy_with_retry(sp, dp, cancel=cancel)
            verified = ok and _matches(sp, dp, deep)
        if verified:
            try:
                nbytes = os.path.getsize(dp)
            except OSError:
                nbytes = 0
            return ("copy", rel, nbytes, note)
        return ("fail", rel, 0, note or "verification failed")

    # Order the work into (optionally labeled) groups so the pass can announce
    # progress per group (e.g. per study). Each caller group keeps only files
    # actually under src; anything left over (DICOMDIR, README…) trails in a
    # final unlabeled group. No groups -> one anonymous group == flat behavior.
    if groups:
        walked = set(files)
        real_src = os.path.realpath(src)
        assigned: set = set()
        work_groups: List[Tuple[Optional[str], List[str]]] = []
        for label, gfiles in groups:
            members = []
            for gf in gfiles:
                # Normalize the caller's path into the exact form os.walk(src)
                # produced — handles /var↔/private/var symlinks (the caller may
                # have resolved them, we didn't) so grouping doesn't silently
                # fall through to the unlabeled tail.
                cand = os.path.join(
                    src, os.path.relpath(os.path.realpath(gf), real_src))
                if cand in walked and cand not in assigned:
                    members.append(cand)
                    assigned.add(cand)
            if members:
                work_groups.append((label, members))
        leftovers = [f for f in files if f not in assigned]
        if leftovers:
            work_groups.append((None, leftovers))
    else:
        work_groups = [(None, files)]

    # Managed without `with`: a `with` block's __exit__ calls shutdown(wait=True),
    # which would block on running copies and negate cancel_futures on cancel.
    # We shutdown(wait=False, cancel_futures=True) so cancel returns promptly;
    # in-flight tasks bail fast because copy_with_retry now sees the cancel
    # token. Workers finish their current (single, small) file and exit.
    pool = ThreadPoolExecutor(max_workers=_MAX_WORKERS)
    try:
        for label, gfiles in work_groups:
            if label:                       # announce the group (e.g. a study)
                emit(progress, Progress(done, total, kind="info",
                                        phase="copy", note=label))
            # Per-group image counter for the plain line (labeled groups only;
            # the unlabeled tail falls back to the overall file count).
            g_total = len(gfiles) if label else 0
            g_done = 0
            futures = {pool.submit(handle, sp): sp for sp in gfiles}
            for fut in as_completed(futures):
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                status, rel, nbytes, note = fut.result()
                done += 1
                if label:
                    g_done += 1
                if status == "skip":
                    skipped += 1
                elif status == "copy":
                    copied += 1
                    bytes_copied += nbytes
                    if note:
                        emit(progress, Progress(done, total, kind="retry",
                                                note=f"{rel} ({note})"))
                else:
                    failed += 1
                    failures.append((rel, note))
                    emit(progress, Progress(done, total, kind="fail",
                                            note=f"{rel} ({note})"))
                now = time.time()
                if now - last_emit >= _PROGRESS_MIN_INTERVAL or done == total:
                    last_emit = now
                    rate = done / (now - start) if now > start else 0
                    eta = (total - done) / rate if rate > 0 else 0
                    emit(progress, Progress(done, total, elapsed=now - start,
                                            rate=rate, eta=eta, phase="copy",
                                            group_done=g_done,
                                            group_total=g_total))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    emit_debug(progress,
               f"verify/fill pass: {copied} copied, {skipped} skipped, "
               f"{failed} failed in {time.time() - verify_start:.1f}s")

    return DeliverResult(
        dest=dest, total_files=total, files_copied=copied,
        files_skipped=skipped, failed=failed, bytes_copied=bytes_copied,
        elapsed=time.time() - start, thorough=thorough,
        content_verified=len(sampled), failures=failures,
    )
