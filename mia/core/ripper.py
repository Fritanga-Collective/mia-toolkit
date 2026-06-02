"""Rip a medical imaging CD into a local folder.

Wrapped from the original ``rip_cd.py``. The copy algorithm — per-file retry
with backoff and a ``dd conv=noerror`` fallback for damaged sectors, plus
resume-on-rerun by skipping same-size files — is unchanged. Progress is
reported through a callback and the copy loop checks a cancel token between
files, so an interrupted rip leaves a partial folder that a later run resumes.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

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
)

DEFAULT_DEST = "./raw_discs"
DEFAULT_RETRIES = 3
RETRY_DELAY_SEC = 2

# Skip macOS / Windows filesystem metadata at disc root
SKIP_DIR_NAMES = {
    "$RECYCLE.BIN", "System Volume Information",
    ".Trashes", ".Spotlight-V100", ".fseventsd", ".TemporaryItems",
}


@dataclass
class RipResult:
    """Outcome of ripping one disc."""

    disc_dir: str
    total_files: int
    copied: int
    skipped: int
    failed: int
    bytes_copied: int
    elapsed: float
    manifest_path: str
    failures: List[Tuple[str, str]] = field(default_factory=list)
    retry_notes: List[Tuple[str, str]] = field(default_factory=list)


def detect_mounted_cds_macos() -> List[str]:
    """Heuristically find mounted optical media under /Volumes."""
    candidates: List[str] = []
    if not os.path.isdir("/Volumes"):
        return candidates

    for entry in os.listdir("/Volumes"):
        path = os.path.join("/Volumes", entry)
        if not os.path.isdir(path) or entry.startswith("."):
            continue
        # The boot drive is mounted here too; skip it.
        if entry in ("Macintosh HD", "Macintosh HD - Data"):
            continue
        try:
            files = os.listdir(path)
        except (PermissionError, OSError):
            continue
        files_upper = [f.upper() for f in files]
        # Medical CDs almost always have one of these at the root
        if any(name in files_upper for name in ("DICOMDIR", "DICOM", "IMAGES")):
            candidates.append(path)
            continue
        # Fallback: a Windows viewer .exe is a strong signal too
        if any(f.lower().endswith(".exe") for f in files):
            candidates.append(path)
    return candidates


def detect_mounted_cds_linux() -> List[str]:
    """Find mounted media on Linux (less reliable, but a sensible fallback)."""
    candidates: List[str] = []
    user = os.environ.get("USER", "")
    for parent in ("/media", "/mnt", f"/run/media/{user}"):
        if not os.path.isdir(parent):
            continue
        for entry in os.listdir(parent):
            path = os.path.join(parent, entry)
            if os.path.isdir(path):
                candidates.append(path)
    return candidates


def detect_mounted_cds() -> List[str]:
    if platform.system() == "Darwin":
        return detect_mounted_cds_macos()
    if platform.system() == "Linux":
        return detect_mounted_cds_linux()
    return []


def next_disc_number(dest_root: str) -> int:
    """Auto-increment based on existing disc_NN folders."""
    if not os.path.isdir(dest_root):
        return 1
    existing = []
    for entry in os.listdir(dest_root):
        if entry.startswith("disc_"):
            parts = entry.split("_")
            if len(parts) >= 2 and parts[1].isdigit():
                existing.append(int(parts[1]))
    return max(existing) + 1 if existing else 1


def sanitize_label(label: str) -> str:
    """Filesystem-safe disc label."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in label)
    return safe[:40].strip("_")


def copy_with_retry(src: str, dst: str, retries: int = DEFAULT_RETRIES) -> Tuple[bool, Optional[str]]:
    """
    Copy a single file. Returns (success: bool, note: str|None).

    Retries on OSError up to `retries` times, then falls back to dd with
    error tolerance for badly damaged sectors.
    """
    last_err = None
    for attempt in range(retries):
        try:
            shutil.copy2(src, dst)
            if os.path.getsize(src) == os.path.getsize(dst):
                if attempt > 0:
                    return True, f"ok (retry {attempt + 1})"
                return True, None
            last_err = "size mismatch after copy"
        except (OSError, IOError) as e:
            last_err = str(e)
        if attempt < retries - 1:
            time.sleep(RETRY_DELAY_SEC * (attempt + 1))

    # All retries failed -> try dd as last resort
    if shutil.which("dd"):
        try:
            # Remove any partial file from previous attempt
            if os.path.exists(dst):
                os.remove(dst)
            result = subprocess.run(
                ["dd", f"if={src}", f"of={dst}",
                 "bs=4096", "conv=noerror,sync"],
                capture_output=True, timeout=300,
            )
            if result.returncode == 0 and os.path.exists(dst) \
                    and os.path.getsize(dst) > 0:
                return True, f"recovered with dd (errors filled, orig: {last_err})"
        except (subprocess.TimeoutExpired, OSError) as e:
            last_err = f"{last_err}; dd also failed: {e}"

    return False, last_err


def rip_disc(
    source: str,
    dest_root: str,
    disc_num: int,
    *,
    verbose: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancel: Optional[CancelToken] = None,
) -> RipResult:
    """Copy everything under `source` into a new disc folder under `dest_root`."""
    label = sanitize_label(os.path.basename(source.rstrip(os.sep)))
    today = datetime.now().strftime("%Y-%m-%d")
    disc_dirname = f"disc_{disc_num:02d}_{today}"
    if label:
        disc_dirname = f"{disc_dirname}_{label}"
    disc_dir = os.path.join(dest_root, disc_dirname)
    os.makedirs(disc_dir, exist_ok=True)

    emit(progress, Progress(0, 0, kind="info", phase="index",
                            note=f"Source:      {source}"))
    emit(progress, Progress(0, 0, kind="info", phase="index",
                            note=f"Destination: {disc_dir}"))

    # First pass: list all files (also tells us total count for progress)
    emit(progress, Progress(0, 0, kind="info", phase="index",
                            note="Indexing disc..."))
    all_files = []
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fn in filenames:
            all_files.append(os.path.join(dirpath, fn))
    total_files = len(all_files)
    emit(progress, Progress(0, total_files, kind="info", phase="index",
                            note=f"{total_files} files found"))

    # Second pass: copy
    copied = 0
    skipped = 0
    failed = 0
    bytes_done = 0
    failures: List[Tuple[str, str]] = []
    retry_notes: List[Tuple[str, str]] = []

    start = time.time()

    for i, src_path in enumerate(all_files, 1):
        check_cancel(cancel)

        rel = os.path.relpath(src_path, source)
        dst_path = os.path.join(disc_dir, rel)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        # Resume support: skip if already present with matching size
        if os.path.exists(dst_path):
            try:
                if os.path.getsize(src_path) == os.path.getsize(dst_path):
                    skipped += 1
                    continue
            except OSError:
                pass

        success, note = copy_with_retry(src_path, dst_path)
        if success:
            copied += 1
            try:
                bytes_done += os.path.getsize(dst_path)
            except OSError:
                pass
            if note:
                retry_notes.append((rel, note))
                emit(progress, Progress(i, total_files, kind="retry",
                                        note=f"[{i}/{total_files}] {rel}  ({note})"))
        else:
            failed += 1
            failures.append((rel, note or ""))
            emit(progress, Progress(i, total_files, kind="fail",
                                    note=f"[{i}/{total_files}] {rel}  ({note})"))

        elapsed = time.time() - start
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total_files - i) / rate if rate > 0 else 0
        emit(progress, Progress(i, total_files, elapsed=elapsed, rate=rate,
                                eta=eta, phase="copy"))

    elapsed = time.time() - start

    # Manifest
    manifest_path = os.path.join(disc_dir, "_manifest.txt")
    with open(manifest_path, "w") as f:
        f.write("CD Rip Manifest\n")
        f.write("================\n")
        f.write(f"Source        : {source}\n")
        f.write(f"Destination   : {disc_dir}\n")
        f.write(f"Date          : {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Total files   : {total_files}\n")
        f.write(f"Copied OK     : {copied}\n")
        f.write(f"Skipped (existed) : {skipped}\n")
        f.write(f"Failed        : {failed}\n")
        f.write(f"Bytes copied  : {bytes_done} ({format_bytes(bytes_done)})\n")
        f.write(f"Duration      : {format_duration(elapsed)}\n")
        if retry_notes:
            f.write(f"\nFiles that needed retries or dd recovery ({len(retry_notes)}):\n")
            for path, note in retry_notes:
                f.write(f"  - {path}  [{note}]\n")
        if failures:
            f.write(f"\nFiles that COULD NOT be copied ({len(failures)}):\n")
            for path, err in failures:
                f.write(f"  - {path}  ({err})\n")

    return RipResult(
        disc_dir=disc_dir,
        total_files=total_files,
        copied=copied,
        skipped=skipped,
        failed=failed,
        bytes_copied=bytes_done,
        elapsed=elapsed,
        manifest_path=manifest_path,
        failures=failures,
        retry_notes=retry_notes,
    )


def eject_macos(path: str) -> None:
    try:
        subprocess.run(["diskutil", "eject", path],
                       check=True, capture_output=True, timeout=15)
        print(f"Ejected {os.path.basename(path)}.")
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired):
        print(f"(Couldn't auto-eject — please eject {path} manually.)")


def _print_summary(result: RipResult) -> None:
    print("\n" + "=" * 64)
    print(f"Done in {format_duration(result.elapsed)}.")
    print(f"  Copied:  {result.copied}")
    print(f"  Skipped: {result.skipped} (already existed)")
    print(f"  Failed:  {result.failed}")
    print(f"  Bytes:   {format_bytes(result.bytes_copied)}")
    print(f"  Manifest: {result.manifest_path}")
    if result.retry_notes:
        print(f"\n  {len(result.retry_notes)} file(s) needed retries — see manifest.")
    if result.failures:
        print(f"\n  ⚠  {result.failed} file(s) could not be read.")
        print("     For critical files, try:")
        print("       1. Clean the disc gently (microfiber, center-to-edge)")
        print("       2. Try a different optical drive")
        print("       3. Image the whole disc with ddrescue:")
        print("            brew install ddrescue")
        print("            ddrescue -r3 /dev/disk2 disc.iso disc.log")
        print("          then mount disc.iso and re-run this script on it.")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rip a medical imaging CD into a local folder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  mia-rip                          # auto-detect\n"
            "  mia-rip /Volumes/MEDICAL_CD\n"
            "  mia-rip /Volumes/CD -o ~/Imaging/raw_discs\n"
            "  mia-rip /Volumes/CD --no-eject\n"
        ),
    )
    parser.add_argument("source", nargs="?",
                        help="Source path (auto-detects if omitted)")
    parser.add_argument("-o", "--output", default=DEFAULT_DEST,
                        help=f"Destination root (default: {DEFAULT_DEST})")
    parser.add_argument("-n", "--disc-num", type=int, default=None,
                        help="Disc number (default: auto-increment)")
    parser.add_argument("--no-eject", action="store_true",
                        help="Don't eject when done")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print every file as it copies")
    args = parser.parse_args(argv)

    # Resolve source
    if args.source:
        source = os.path.expanduser(args.source)
        if not os.path.isdir(source):
            print(f"ERROR: {source} is not a directory")
            return 1
    else:
        candidates = detect_mounted_cds()
        if not candidates:
            print("No mounted CDs detected.")
            print("Insert a disc and wait for it to mount,")
            print("or pass the path explicitly: mia-rip /Volumes/<name>")
            return 1
        if len(candidates) > 1:
            print("Multiple candidates found:")
            for c in candidates:
                print(f"  {c}")
            print("\nSpecify one: mia-rip <path>")
            return 1
        source = candidates[0]
        print(f"Auto-detected disc: {source}")

    dest = os.path.expanduser(args.output)
    os.makedirs(dest, exist_ok=True)
    disc_num = args.disc_num if args.disc_num else next_disc_number(dest)

    try:
        result = rip_disc(source, dest, disc_num, verbose=args.verbose,
                          progress=ConsoleProgress(verbose=args.verbose))
    except Cancelled:
        print("\nInterrupted. Re-run to resume (already-copied files are skipped).")
        return 130

    _print_summary(result)

    if not args.no_eject and platform.system() == "Darwin" and result.copied > 0:
        eject_macos(source)

    return 2 if result.failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
