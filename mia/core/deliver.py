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
import shutil
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .common import (
    CancelToken,
    Progress,
    ProgressCallback,
    check_cancel,
    emit,
)
from .ripper import copy_with_retry


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


def copy_tree_verified(
    src: str,
    dest: str,
    *,
    thorough: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> DeliverResult:
    """Copy every file under ``src`` into ``dest``, verifying and resuming."""
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)

    emit(progress, Progress(0, 0, kind="info", note=f"Preparing to copy to {dest}"))
    files = []
    for dirpath, _, filenames in os.walk(src):
        for fn in filenames:
            files.append(os.path.join(dirpath, fn))
    total = len(files)
    emit(progress, Progress(0, total, kind="info",
                            note=f"{total} files to copy"))

    copied = skipped = failed = 0
    bytes_copied = 0
    failures: List[Tuple[str, str]] = []
    start = time.time()

    for i, sp in enumerate(files, 1):
        check_cancel(cancel)
        rel = os.path.relpath(sp, src)
        dp = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dp), exist_ok=True)

        if os.path.exists(dp) and _matches(sp, dp, thorough):
            skipped += 1
        else:
            ok, note = copy_with_retry(sp, dp)
            verified = ok and _matches(sp, dp, thorough)
            if ok and not verified:  # one more attempt on a bad write
                ok, note = copy_with_retry(sp, dp)
                verified = ok and _matches(sp, dp, thorough)

            if verified:
                copied += 1
                try:
                    bytes_copied += os.path.getsize(dp)
                except OSError:
                    pass
                if note:
                    emit(progress, Progress(i, total, kind="retry",
                                            note=f"{rel} ({note})"))
            else:
                failed += 1
                reason = note or "verification failed"
                failures.append((rel, reason))
                emit(progress, Progress(i, total, kind="fail",
                                        note=f"{rel} ({reason})"))

        elapsed = time.time() - start
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0
        emit(progress, Progress(i, total, elapsed=elapsed, rate=rate, eta=eta,
                                phase="copy"))

    return DeliverResult(
        dest=dest, total_files=total, files_copied=copied,
        files_skipped=skipped, failed=failed, bytes_copied=bytes_copied,
        elapsed=time.time() - start, thorough=thorough, failures=failures,
    )
