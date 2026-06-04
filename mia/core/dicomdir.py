"""Compile a unified DICOM file-set (with DICOMDIR) from a folder tree.

Wrapped from the original ``build_dicomdir.py``. The magic-byte file discovery,
SOPInstanceUID de-duplication, minimal tag auto-repair for non-conformant
hospital DICOMs, and ``FileSet.write`` output are unchanged. The indexing loop
reports progress and checks a cancel token; the final ``FileSet.write`` is a
single blocking call that cannot be interrupted mid-write (callers surface this
as a non-cancellable step, and the partial output is caught by the non-empty
guard on the next run).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .common import (
    Cancelled,
    CancelToken,
    ConsoleProgress,
    Progress,
    ProgressCallback,
    check_cancel,
    emit,
    format_bytes,
    format_duration,
    is_dicom_file,
)

try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    from pydicom.fileset import FileSet
except ImportError:  # pragma: no cover
    print("ERROR: pydicom not installed.")
    print("Run: pip install pydicom")
    raise


DEFAULT_SOURCE = "./raw_discs"
DEFAULT_OUTPUT = "./Archive"


SKIP_DIR_NAMES = {
    "$RECYCLE.BIN", "System Volume Information",
    ".Trashes", ".Spotlight-V100", ".fseventsd",
}
SKIP_EXTENSIONS = {
    ".exe", ".dll", ".htm", ".html", ".jpg", ".jpeg", ".png",
    ".gif", ".pdf", ".txt", ".ini", ".inf", ".bat", ".css",
    ".js", ".xml", ".doc", ".docx", ".zip", ".log", ".db",
    ".plist", ".xlsx", ".xls", ".csv",
}
SKIP_FILENAMES = {
    "DICOMDIR", "AUTORUN.INF", "README.TXT",
    "INDEX.HTM", "INDEX.HTML", ".DS_STORE",
    "_MANIFEST.TXT",
}

# Tags that the DICOMDIR file-set structure requires to be present.
# Many hospital DICOMs are non-conformant and omit these. We fill in
# minimal placeholder values so the file-set can be built — actual
# patient/study data on the radiology side is unaffected.
REQUIRED_TAGS_DEFAULTS = {
    "PatientID":       "UNKNOWN",
    "PatientName":     "UNKNOWN",
    "StudyID":         "1",
    "StudyDate":       "",
    "StudyTime":       "",
    "AccessionNumber": "",
    "Modality":        "OT",
    "SeriesNumber":    1,
    "InstanceNumber":  1,
}


@dataclass
class DicomdirResult:
    """Outcome of building a DICOMDIR archive."""

    output: str
    added: int
    studies: int
    duplicates: int
    errors: int
    skipped_no_uid: int
    output_size: int
    output_files: int
    elapsed: float
    studies_info: Dict[str, dict] = field(default_factory=dict)


def find_dicom_files(root: str) -> Iterator[str]:
    """Walk root, yield paths to DICOM files."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fn in filenames:
            if fn.startswith(".") or fn.upper() in SKIP_FILENAMES:
                continue
            if Path(fn).suffix.lower() in SKIP_EXTENSIONS:
                continue
            full = os.path.join(dirpath, fn)
            if is_dicom_file(full):
                yield full


def ensure_required_tags(ds) -> List[str]:
    """Fill missing/empty tags with placeholders so FileSet.add() accepts the dataset."""
    repaired = []
    for tag, default in REQUIRED_TAGS_DEFAULTS.items():
        current = getattr(ds, tag, None)
        if current is None or current == "":
            setattr(ds, tag, default)
            repaired.append(tag)
    return repaired


def build_fileset(
    source: str,
    output: str,
    *,
    verbose: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> Optional[DicomdirResult]:
    """Index all DICOM files under source into a FileSet, write to output."""
    emit(progress, Progress(0, 0, kind="info",
                            note=f"Scanning {source} for DICOM files..."))
    files = list(find_dicom_files(source))
    total = len(files)
    emit(progress, Progress(0, total, kind="info",
                            note=f"Found {total} DICOM files"))

    if total == 0:
        return None

    fs = FileSet()

    added = 0
    duplicates = 0
    errors = 0
    skipped_no_uid = 0
    files_repaired = 0
    tags_repaired_total = 0
    seen_sop_uids = set()
    studies_info: Dict[str, dict] = {}

    start = time.time()

    for i, path in enumerate(files, 1):
        check_cancel(cancel)

        try:
            ds = pydicom.dcmread(path, force=True)
        except (InvalidDicomError, Exception) as e:
            errors += 1
            if verbose:
                emit(progress, Progress(i, total, kind="retry",
                                        note=f"ERROR reading {path}: {e}"))
            ds = None

        if ds is not None:
            sop_uid = getattr(ds, "SOPInstanceUID", None)
            if not sop_uid:
                skipped_no_uid += 1
            elif sop_uid in seen_sop_uids:
                duplicates += 1
            else:
                seen_sop_uids.add(sop_uid)

                # Hospital DICOMs frequently lack tags the file-set spec
                # requires. Auto-repair before attempting to add.
                repaired_tags = ensure_required_tags(ds)

                try:
                    fs.add(ds)
                    added += 1
                    if repaired_tags:
                        tags_repaired_total += len(repaired_tags)
                        files_repaired += 1

                    study_uid = str(getattr(ds, "StudyInstanceUID", "unknown"))
                    if study_uid not in studies_info:
                        studies_info[study_uid] = {
                            "date": str(getattr(ds, "StudyDate", "")),
                            "modality": str(getattr(ds, "Modality", "")),
                            "description": str(getattr(ds, "StudyDescription", "")),
                            "count": 0,
                        }
                    studies_info[study_uid]["count"] += 1
                except Exception as e:
                    errors += 1
                    if verbose:
                        emit(progress, Progress(i, total, kind="retry",
                                                note=f"Could not add {path}: {e}"))

        elapsed = time.time() - start
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0
        emit(progress, Progress(i, total, elapsed=elapsed, rate=rate, eta=eta,
                                phase="index"))

    summary = f"Indexed {added} instances into the file-set."
    emit(progress, Progress(total, total, kind="info", note=summary))

    # Write the file-set: copies files into standard structure + creates DICOMDIR
    emit(progress, Progress(total, total, kind="info", phase="write",
                            note=("Writing DICOMDIR and copying files to "
                                  f"{output} (this is the slow part)")))

    os.makedirs(output, exist_ok=True)
    fs.write(output)

    # Tally what we actually produced
    total_size = 0
    file_count = 0
    for dirpath, _, filenames in os.walk(output):
        for fn in filenames:
            try:
                total_size += os.path.getsize(os.path.join(dirpath, fn))
                file_count += 1
            except OSError:
                pass

    return DicomdirResult(
        output=output,
        added=added,
        studies=len(studies_info),
        studies_info=studies_info,
        duplicates=duplicates,
        errors=errors,
        skipped_no_uid=skipped_no_uid,
        output_size=total_size,
        output_files=file_count,
        elapsed=time.time() - start,
    )


def write_readme(output_path: str, result: DicomdirResult, source: str) -> str:
    """Human-readable README in the archive root. Returns its path."""
    readme = os.path.join(output_path, "README.txt")
    with open(readme, "w") as f:
        f.write("DICOM Archive\n")
        f.write("=============\n\n")
        f.write(f"Built : {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"From  : {source}\n\n")
        f.write("This archive is a standards-compliant DICOM file-set\n")
        f.write("(DICOM PS3.10 Media Storage). To use it, point any PACS\n")
        f.write("or DICOM viewer at the DICOMDIR file at the root.\n\n")
        f.write("Summary\n")
        f.write("-------\n")
        f.write(f"Studies      : {result.studies}\n")
        f.write(f"Instances    : {result.added}\n")
        f.write(f"Total size   : {format_bytes(result.output_size)}\n")
        if result.duplicates:
            f.write(f"Duplicates skipped : {result.duplicates}\n")
        if result.errors:
            f.write(f"Parse errors       : {result.errors}\n")
        f.write("\nStudies (chronological)\n")
        f.write("-----------------------\n")
        sorted_studies = sorted(
            result.studies_info.items(),
            key=lambda x: x[1]["date"],
        )
        for i, (_, info) in enumerate(sorted_studies, 1):
            date = info["date"]
            if len(date) == 8:
                date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            desc = info["description"][:55]
            f.write(f"  [{i:2d}] {date}  {info['modality']:3s}  "
                    f"{desc}  ({info['count']} images)\n")
    return readme


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile a DICOM archive with DICOMDIR from a folder tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "By default, reads from './raw_discs' and writes an './Archive'\n"
            "folder in the current directory.\n\n"
            "Examples:\n"
            "  mia-build                            # use defaults\n"
            "  mia-build /custom/path               # override source\n"
            "  mia-build -o /Volumes/USB/Archive    # override output\n"
        ),
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE,
                        help="Source directory of DICOM data (default: ./raw_discs)")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="Output archive directory (default: ./Archive)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Detailed per-file logging")
    args = parser.parse_args(argv)

    source = os.path.expanduser(args.source)
    output = os.path.expanduser(args.output)

    if not os.path.isdir(source):
        print(f"ERROR: {source} is not a directory")
        print("       (did you run the ripper yet to populate raw_discs/?)")
        return 1
    if os.path.exists(output) and os.listdir(output):
        print(f"ERROR: {output} exists and is not empty.")
        print("Choose a different output path or empty the existing one.")
        return 1

    try:
        result = build_fileset(source, output, verbose=args.verbose,
                               progress=ConsoleProgress(verbose=args.verbose))
    except Cancelled:
        print("\nInterrupted. The partial archive should be removed before retrying.")
        return 130

    if result is None:
        print("No DICOM files found. Exiting.")
        return 1

    readme = write_readme(output, result, source)

    print("\n" + "=" * 64)
    print(f"Archive complete: {output}")
    print(f"  Studies      : {result.studies}")
    print(f"  Instances    : {result.added}")
    print(f"  Files on disk: {result.output_files}")
    print(f"  Total size   : {format_bytes(result.output_size)}")
    print(f"  Time         : {format_duration(result.elapsed)}")
    print(f"  README       : {readme}")
    print("\nTo deliver:")
    print(f"  cp -R '{output}' /Volumes/<USB_DRIVE>/")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
