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
import shutil
import subprocess
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
)
from .ripper import copy_with_retry

# Parallel workers for the verify/copy pass. USB write bandwidth is the real
# ceiling; concurrency hides per-file latency (thousands of small DICOM files),
# it doesn't push past the device — so keep it modest.
_MAX_WORKERS = min(8, (os.cpu_count() or 4))
_PROGRESS_MIN_INTERVAL = 0.2  # seconds; throttle per-file emits


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
    the verify/fill pass that follows, which counts actual files."""
    system = platform.system()
    if system == "Windows":
        cmd = ["robocopy", src, dest, "/E", "/MT:8", "/R:1", "/W:1",
               "/NFL", "/NDL", "/NJH", "/NP"]
        ok_codes = range(0, 8)            # robocopy: <8 == success
    elif system == "Darwin":
        cmd = ["ditto", src, dest]
        ok_codes = (0,)
    elif system == "Linux":
        cmd = ["cp", "-a", src + "/.", dest + "/"]
        ok_codes = (0,)
    else:
        return False
    if shutil.which(cmd[0]) is None:
        return False
    emit_debug(progress, f"native copy: {' '.join(cmd)}", phase="copy")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    except OSError:
        return False
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
    prefer_native: bool = True,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> DeliverResult:
    """Copy every file under ``src`` into ``dest``, verifying and resuming.

    A native tool (robocopy/ditto/cp) does the bulk copy fast when available;
    then a parallel verify/fill pass guarantees every file is present and
    size-correct (SHA-256 when ``thorough``), copying anything the native tool
    missed. With no native tool the parallel pass does the whole copy itself.
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
        if os.path.exists(dp) and _matches(sp, dp, thorough):
            return ("skip", rel, 0, None)
        # Create the parent lazily (no upfront pre-create). exist_ok swallows
        # the benign race between pool threads writing into the same folder.
        try:
            os.makedirs(os.path.dirname(dp), exist_ok=True)
        except FileExistsError:
            pass
        ok, note = copy_with_retry(sp, dp, cancel=cancel)
        verified = ok and _matches(sp, dp, thorough)
        if ok and not verified:                 # one retry on a bad write
            ok, note = copy_with_retry(sp, dp, cancel=cancel)
            verified = ok and _matches(sp, dp, thorough)
        if verified:
            try:
                nbytes = os.path.getsize(dp)
            except OSError:
                nbytes = 0
            return ("copy", rel, nbytes, note)
        return ("fail", rel, 0, note or "verification failed")

    # Managed without `with`: a `with` block's __exit__ calls shutdown(wait=True),
    # which would block on running copies and negate cancel_futures on cancel.
    # We shutdown(wait=False, cancel_futures=True) so cancel returns promptly;
    # in-flight tasks bail fast because copy_with_retry now sees the cancel
    # token. Workers finish their current (single, small) file and exit.
    pool = ThreadPoolExecutor(max_workers=_MAX_WORKERS)
    try:
        futures = {pool.submit(handle, sp): sp for sp in files}
        for fut in as_completed(futures):
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            status, rel, nbytes, note = fut.result()
            done += 1
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
                                        rate=rate, eta=eta, phase="copy"))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    emit_debug(progress,
               f"verify/fill pass: {copied} copied, {skipped} skipped, "
               f"{failed} failed in {time.time() - verify_start:.1f}s")

    return DeliverResult(
        dest=dest, total_files=total, files_copied=copied,
        files_skipped=skipped, failed=failed, bytes_copied=bytes_copied,
        elapsed=time.time() - start, thorough=thorough, failures=failures,
    )
