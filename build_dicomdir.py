#!/usr/bin/env python3
"""
DICOMDIR Builder
================

Takes a directory of ripped DICOM data (typically the output of rip_cd.py)
and produces a single standards-compliant DICOM file-set: one DICOMDIR
indexing every study under a normalized DICOM/ST.../SE.../IM... structure.

The result can be loaded into any PACS or DICOM viewer as a single 'CD',
giving the radiologist one entry point to all studies at once.

Usage:
    python3 build_dicomdir.py ~/Imaging_Master/raw_discs -o ~/Archive

Input:
    Any directory tree containing DICOM files (with or without .dcm extension).
    Files anywhere in the tree are found by magic-byte detection.

Output:
    Archive/
    ├── DICOMDIR              <- the file-set index
    ├── PT000000/             <- patient
    │   ├── ST000000/         <- study
    │   │   ├── SE000000/     <- series
    │   │   │   ├── IM000000
    │   │   │   └── ...
    │   │   └── ...
    │   └── ...
    └── README.txt

This whole tree can be copied to a USB drive and handed off — any PACS,
Horos, OsiriX, RadiAnt, Weasis, or 3D Slicer will recognize it.

Requires:
    pip install pydicom --break-system-packages
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import pydicom
    from pydicom.errors import InvalidDicomError
    from pydicom.fileset import FileSet
except ImportError:
    print("ERROR: pydicom not installed.")
    print("Run: pip install pydicom --break-system-packages")
    sys.exit(1)


# Resolve script location so defaults sit next to this file
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = str(SCRIPT_DIR / "raw_discs")
DEFAULT_OUTPUT = str(SCRIPT_DIR / "Archive")


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


def is_dicom_file(path):
    """DICOM files have 'DICM' at offset 128."""
    try:
        with open(path, "rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except (OSError, IOError):
        return False


def find_dicom_files(root):
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


def format_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def format_duration(s):
    if s < 60:
        return f"{s:.0f}s"
    m, sec = divmod(int(s), 60)
    if m < 60:
        return f"{m}m {sec}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


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


def ensure_required_tags(ds):
    """Fill missing/empty tags with placeholders so FileSet.add() accepts the dataset."""
    repaired = []
    for tag, default in REQUIRED_TAGS_DEFAULTS.items():
        current = getattr(ds, tag, None)
        if current is None or current == "":
            setattr(ds, tag, default)
            repaired.append(tag)
    return repaired


def build_fileset(source, output, verbose=False):
    """Index all DICOM files under source into a FileSet, write to output."""
    print(f"Scanning {source} for DICOM files...")
    files = list(find_dicom_files(source))
    total = len(files)
    print(f"Found {total} DICOM files\n")

    if total == 0:
        print("No DICOM files found. Exiting.")
        return None

    fs = FileSet()

    added = 0
    duplicates = 0
    errors = 0
    skipped_no_uid = 0
    files_repaired = 0
    tags_repaired_total = 0
    seen_sop_uids = set()
    studies_info = {}

    start = time.time()
    last_progress = start

    for i, path in enumerate(files, 1):
        try:
            ds = pydicom.dcmread(path, force=True)
        except (InvalidDicomError, Exception) as e:
            errors += 1
            if verbose:
                print(f"  ERROR reading {path}: {e}")
            continue

        sop_uid = getattr(ds, "SOPInstanceUID", None)
        if not sop_uid:
            skipped_no_uid += 1
            continue

        if sop_uid in seen_sop_uids:
            duplicates += 1
            continue
        seen_sop_uids.add(sop_uid)

        # Hospital DICOMs frequently lack tags the file-set spec requires.
        # Auto-repair before attempting to add.
        repaired_tags = ensure_required_tags(ds)
        if repaired_tags and verbose:
            print(f"  Repaired tags {repaired_tags} on {path}")

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
                print(f"  Could not add {path}: {e}")
            continue

        now = time.time()
        if (now - last_progress) >= 2.0 or i == total:
            elapsed = now - start
            rate = i / elapsed if elapsed > 0 else 0
            pct = 100 * i / total
            eta = (total - i) / rate if rate > 0 else 0
            print(f"  [{i}/{total}] {pct:5.1f}%  "
                  f"{rate:.0f} files/s  ETA {format_duration(eta)}",
                  flush=True)
            last_progress = now

    print(f"\nIndexed {added} instances into the file-set.")
    if files_repaired:
        print(f"  Auto-repaired missing tags on {files_repaired} files "
              f"({tags_repaired_total} tag fills)")
    if duplicates:
        print(f"  Skipped {duplicates} duplicates (same SOPInstanceUID)")
    if skipped_no_uid:
        print(f"  Skipped {skipped_no_uid} files missing SOPInstanceUID")
    if errors:
        print(f"  {errors} files could not be parsed")

    # Write the file-set: copies files into standard structure + creates DICOMDIR
    print(f"\nWriting DICOMDIR and copying files to {output}")
    print("(this is the slow part — minutes to an hour for large archives)\n")

    os.makedirs(output, exist_ok=True)
    write_start = time.time()
    fs.write(output)
    write_elapsed = time.time() - write_start
    print(f"Write completed in {format_duration(write_elapsed)}")

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

    return {
        "added": added,
        "studies": len(studies_info),
        "studies_info": studies_info,
        "duplicates": duplicates,
        "errors": errors,
        "skipped_no_uid": skipped_no_uid,
        "output_size": total_size,
        "output_files": file_count,
        "elapsed": time.time() - start,
    }


def write_readme(output_path, stats, source):
    """Human-readable README in the archive root."""
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
        f.write(f"Studies      : {stats['studies']}\n")
        f.write(f"Instances    : {stats['added']}\n")
        f.write(f"Total size   : {format_bytes(stats['output_size'])}\n")
        if stats["duplicates"]:
            f.write(f"Duplicates skipped : {stats['duplicates']}\n")
        if stats["errors"]:
            f.write(f"Parse errors       : {stats['errors']}\n")
        f.write("\nStudies (chronological)\n")
        f.write("-----------------------\n")
        sorted_studies = sorted(
            stats["studies_info"].items(),
            key=lambda x: x[1]["date"],
        )
        for i, (_, info) in enumerate(sorted_studies, 1):
            date = info["date"]
            if len(date) == 8:
                date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            desc = info["description"][:55]
            f.write(f"  [{i:2d}] {date}  {info['modality']:3s}  "
                    f"{desc}  ({info['count']} images)\n")
    print(f"README: {readme}")


def main():
    parser = argparse.ArgumentParser(
        description="Compile a DICOM archive with DICOMDIR from a folder tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "By default, reads from 'raw_discs/' next to this script and writes\n"
            "an 'Archive/' folder next to this script.\n\n"
            "Examples:\n"
            "  python3 build_dicomdir.py                        # use defaults\n"
            "  python3 build_dicomdir.py /custom/path           # override source\n"
            "  python3 build_dicomdir.py -o /Volumes/USB/Archive   # override output\n"
        ),
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE,
                        help="Source directory of DICOM data (default: ./raw_discs next to this script)")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="Output archive directory (default: ./Archive next to this script)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Detailed per-file logging")
    args = parser.parse_args()

    source = os.path.expanduser(args.source)
    output = os.path.expanduser(args.output)

    if not os.path.isdir(source):
        print(f"ERROR: {source} is not a directory")
        print(f"       (did you run rip_cd.py yet to populate raw_discs/?)")
        sys.exit(1)
    if os.path.exists(output) and os.listdir(output):
        print(f"ERROR: {output} exists and is not empty.")
        print("Choose a different output path or empty the existing one.")
        sys.exit(1)

    stats = build_fileset(source, output, verbose=args.verbose)
    if stats is None:
        sys.exit(1)

    write_readme(output, stats, source)

    print("\n" + "=" * 64)
    print(f"Archive complete: {output}")
    print(f"  Studies      : {stats['studies']}")
    print(f"  Instances    : {stats['added']}")
    print(f"  Files on disk: {stats['output_files']}")
    print(f"  Total size   : {format_bytes(stats['output_size'])}")
    print(f"  Time         : {format_duration(stats['elapsed'])}")
    print("\nTo deliver:")
    print(f"  cp -R '{output}' /Volumes/<USB_DRIVE>/")
    print("\nTo test it locally before delivering:")
    print(f"  Open Horos -> File -> Import -> Import Files")
    print(f"  -> point at the DICOMDIR file")
    print("=" * 64)


if __name__ == "__main__":
    main()