"""Import studies from a local folder/USB drive or a downloaded ZIP archive.

Both importers funnel into :func:`mia.core.ripper.rip_disc`, which already
copies an arbitrary tree into a numbered ``disc_NN_<date>_<label>`` folder with
per-file retry, resume-on-rerun, a ``_manifest.txt``, and the shared
Progress/cancel contract — so the inventory/archive pipeline needs no changes.
Everything here is local I/O only: no network, ever.
"""

from __future__ import annotations

import os
import tempfile
import time
import zipfile
from dataclasses import dataclass
from typing import Optional

from .common import (
    CancelToken,
    Progress,
    ProgressCallback,
    check_cancel,
    emit,
    is_dicom_file,
)
from .ripper import (
    SKIP_DIR_NAMES,
    RipResult,
    _manifest_safe,
    rip_disc,
    sanitize_label,
)

# Pre-scan is synchronous in the GUI (it only stats files and reads 132 bytes
# each), so cap it for pathological trees; a capped result is still enough to
# populate the confirm dialog.
SCAN_CAP_FILES = 20_000
SCAN_CAP_SECONDS = 10.0

# How many levels of zip-inside-zip to unpack (portals sometimes ship one zip
# per study inside an outer download).
ZIP_NEST_DEPTH = 3

# Decompression-bomb guard: a tiny ZIP can declare/expand to many GB, filling
# the disk — and nested expansion compounds it (scan_zip only sees the top
# level, so the consent dialog can't warn). Cap the cumulative uncompressed
# size across ALL nesting levels, and reject absurdly long member-name
# components (which otherwise raise a raw ENAMETOOLONG mid-extract).
MAX_TOTAL_UNCOMPRESSED = 20 * 1024 ** 3  # 20 GiB, generous for real archives
MAX_MEMBER_NAME = 255                    # per path component (FS limit)


class _ExtractBudget:
    """A shared uncompressed-byte ceiling, decremented as members extract.

    Charged with each member's declared size (zipfile reads only up to the
    declared size, so this bounds what hits the disk). Shared across the
    top-level extract and every nested expansion so the total can't be evaded
    by spreading the payload across levels.
    """

    def __init__(self, limit: Optional[int] = None) -> None:
        # Read the module constant at call time (not as a default) so tests can
        # monkeypatch MAX_TOTAL_UNCOMPRESSED to a small value.
        self.limit = MAX_TOTAL_UNCOMPRESSED if limit is None else limit
        self.remaining = self.limit

    def charge(self, nbytes: int) -> None:
        self.remaining -= nbytes
        if self.remaining < 0:
            raise ValueError(
                "ZIP archive is too large to extract safely "
                f"(exceeds {self.limit} bytes uncompressed) — refusing as a "
                "possible decompression bomb.")


@dataclass
class ScanResult:
    """What a pre-import scan found (backs the GUI confirm dialog)."""

    files: int
    bytes: int
    dicom_files: int  # -1 = not checked (ZIPs are checked during import)
    capped: bool = False


@dataclass
class ImportResult(RipResult):
    """A RipResult plus what kind of source it came from."""

    dicom_files: int = -1
    source_type: str = "folder"


def scan_folder(
    src: str,
    *,
    cap_files: int = SCAN_CAP_FILES,
    cap_seconds: float = SCAN_CAP_SECONDS,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> ScanResult:
    """Count files/bytes and DICOM files under ``src`` (capped, cancellable)."""
    files = 0
    total_bytes = 0
    dicom = 0
    capped = False
    start = time.time()
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fn in filenames:
            check_cancel(cancel)
            path = os.path.join(dirpath, fn)
            try:
                total_bytes += os.path.getsize(path)
            except OSError:
                continue
            files += 1
            if is_dicom_file(path):
                dicom += 1
            if files % 500 == 0:
                emit(progress, Progress(files, 0, kind="info", phase="scan",
                                        note=f"scanned {files} files…"))
            if files >= cap_files or time.time() - start > cap_seconds:
                capped = True
                return ScanResult(files, total_bytes, dicom, capped)
    return ScanResult(files, total_bytes, dicom, capped)


def scan_zip(path: str) -> ScanResult:
    """File count + uncompressed size from the ZIP central directory (fast).

    DICOM detection inside ZIPs happens during the import (``dicom_files=-1``).
    """
    with zipfile.ZipFile(path) as zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        return ScanResult(len(infos), sum(i.file_size for i in infos), -1)


def _count_dicom(root: str) -> int:
    n = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if is_dicom_file(os.path.join(dirpath, fn)):
                n += 1
    return n


def _finish(rip: RipResult, *, source_type: str,
            source_note: Optional[str] = None) -> ImportResult:
    """Wrap a RipResult, counting DICOM files and annotating the manifest."""
    dicom = _count_dicom(rip.disc_dir)
    try:
        with open(rip.manifest_path, "a") as f:
            f.write(f"\nSource type   : {source_type}\n")
            if source_note:
                f.write(f"Original file : {_manifest_safe(source_note)}\n")
            f.write(f"DICOM files   : {dicom}\n")
    except OSError:
        pass
    return ImportResult(
        disc_dir=rip.disc_dir, total_files=rip.total_files, copied=rip.copied,
        skipped=rip.skipped, failed=rip.failed, bytes_copied=rip.bytes_copied,
        elapsed=rip.elapsed, manifest_path=rip.manifest_path,
        failures=rip.failures, retry_notes=rip.retry_notes,
        dicom_files=dicom, source_type=source_type,
    )


def import_folder(
    source: str,
    dest_root: str,
    num: int,
    *,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> ImportResult:
    """Copy a folder/USB tree into the project as a new numbered source."""
    source = os.path.abspath(source)
    if not os.path.isdir(source):
        raise ValueError(f"Not a folder: {source}")
    rip = rip_disc(source, dest_root, num, progress=progress, cancel=cancel)
    return _finish(rip, source_type="folder")


def _safe_extract(zf: zipfile.ZipFile, dest: str, *,
                  budget: _ExtractBudget,
                  progress: Optional[ProgressCallback],
                  cancel: Optional[CancelToken]) -> None:
    """Extract all members, refusing any path that escapes ``dest`` (zip-slip),
    any over-long name component, and charging each member to ``budget``
    (decompression-bomb guard)."""
    dest_real = os.path.realpath(dest)
    members = zf.infolist()
    total = len(members)
    for i, member in enumerate(members, 1):
        check_cancel(cancel)
        target = os.path.realpath(os.path.join(dest, member.filename))
        if target != dest_real and not target.startswith(dest_real + os.sep):
            raise ValueError(f"Unsafe path in ZIP archive: {member.filename!r}")
        if any(len(part) > MAX_MEMBER_NAME
               for part in member.filename.replace("\\", "/").split("/")):
            raise ValueError(
                f"Name too long in ZIP archive: {member.filename[:60]!r}…")
        budget.charge(member.file_size)
        zf.extract(member, dest)
        if i % 100 == 0 or i == total:
            emit(progress, Progress(i, total, kind="info", phase="extract",
                                    note=f"extracting {i}/{total}…"))


def _expand_nested_zips(root: str, *, budget: _ExtractBudget,
                        progress: Optional[ProgressCallback],
                        cancel: Optional[CancelToken]) -> None:
    """Unpack zip-inside-zip up to ZIP_NEST_DEPTH levels (content replaces
    the container; a fake .zip that isn't a real archive is left as-is).
    Shares ``budget`` with the top-level extract so nested expansion can't
    blow past the cumulative limit."""
    for _depth in range(ZIP_NEST_DEPTH):
        nested = [os.path.join(dp, fn)
                  for dp, _dn, fns in os.walk(root)
                  for fn in fns if fn.lower().endswith(".zip")]
        nested = [p for p in nested if zipfile.is_zipfile(p)]
        if not nested:
            return
        for path in nested:
            check_cancel(cancel)
            # Uniquify so a member literally named "x.zip_contents" sitting
            # next to "x.zip" can't make makedirs raise on a non-dir.
            sub = path[:-4] + "_contents"
            n = 1
            while os.path.exists(sub) and not os.path.isdir(sub):
                sub = f"{path[:-4]}_contents_{n}"
                n += 1
            os.makedirs(sub, exist_ok=True)
            with zipfile.ZipFile(path) as zf:
                _safe_extract(zf, sub, budget=budget,
                              progress=progress, cancel=cancel)
            os.remove(path)


def import_zip(
    zip_path: str,
    dest_root: str,
    num: int,
    *,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> ImportResult:
    """Extract a downloaded ZIP (portal-style, nested zips included) into a
    temp dir, then copy it into the project as a new numbered source."""
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"Not a ZIP archive: {zip_path}")
    stem = sanitize_label(
        os.path.splitext(os.path.basename(zip_path))[0]) or "zip_import"
    emit(progress, Progress(0, 0, kind="info", phase="extract",
                            note=f"Extracting {os.path.basename(zip_path)}…"))
    # Extract on the same volume as the project (the system temp volume can be
    # much smaller than an external project drive); fall back to system temp.
    parent = os.path.dirname(os.path.abspath(dest_root))
    try:
        tmp_ctx = tempfile.TemporaryDirectory(prefix=".mia_zip_", dir=parent)
    except OSError:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="mia_zip_")
    budget = _ExtractBudget()
    with tmp_ctx as tmp:
        # Named after the zip so rip_disc derives the right folder label.
        extract_root = os.path.join(tmp, stem)
        os.makedirs(extract_root)
        with zipfile.ZipFile(zip_path) as zf:
            _safe_extract(zf, extract_root, budget=budget,
                          progress=progress, cancel=cancel)
        _expand_nested_zips(extract_root, budget=budget,
                            progress=progress, cancel=cancel)
        rip = rip_disc(extract_root, dest_root, num,
                       progress=progress, cancel=cancel)
    return _finish(rip, source_type="zip",
                   source_note=os.path.basename(zip_path))
