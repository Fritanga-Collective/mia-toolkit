#!/usr/bin/env python3
"""
CD Ripper for Medical Imaging Discs
===================================

Copies the contents of a mounted CD/DVD into a local folder tree, with
error handling appropriate for aging hospital media.

Workflow:
  1. Insert the disc and wait for macOS to mount it
  2. Run:  python3 rip_cd.py
  3. Script auto-detects the disc, copies everything, ejects when done
  4. Insert the next disc and repeat

Or specify the source explicitly:
  python3 rip_cd.py /Volumes/MEDICAL_CD
  python3 rip_cd.py /Volumes/CD -o ~/Imaging_Master/raw_discs

Features:
  - Auto-numbers discs (disc_01_..., disc_02_...) so they sort chronologically
  - Retries failed reads 3 times with backoff
  - Falls back to `dd conv=noerror` for unreadable sectors
  - Writes a _manifest.txt per disc with what worked and what didn't
  - Skips files already copied (safe to re-run / resume a partial rip)
  - Ejects the disc when done (macOS)

For badly damaged discs that this script can't recover, install ddrescue
(`brew install ddrescue`) and image the whole disc:
    ddrescue -r3 /dev/disk2 disc.iso disc.log
Then mount the iso (double-click) and run this script on the mount point.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime

DEFAULT_DEST = "./raw_discs"
DEFAULT_RETRIES = 3
RETRY_DELAY_SEC = 2

# Skip macOS / Windows filesystem metadata at disc root
SKIP_DIR_NAMES = {
    "$RECYCLE.BIN", "System Volume Information",
    ".Trashes", ".Spotlight-V100", ".fseventsd", ".TemporaryItems",
}


def detect_mounted_cds_macos():
    """Heuristically find mounted optical media under /Volumes."""
    candidates = []
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


def detect_mounted_cds_linux():
    """Find mounted media on Linux (less reliable, but a sensible fallback)."""
    candidates = []
    user = os.environ.get("USER", "")
    for parent in ("/media", "/mnt", f"/run/media/{user}"):
        if not os.path.isdir(parent):
            continue
        for entry in os.listdir(parent):
            path = os.path.join(parent, entry)
            if os.path.isdir(path):
                candidates.append(path)
    return candidates


def detect_mounted_cds():
    if platform.system() == "Darwin":
        return detect_mounted_cds_macos()
    if platform.system() == "Linux":
        return detect_mounted_cds_linux()
    return []


def next_disc_number(dest_root):
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


def sanitize_label(label):
    """Filesystem-safe disc label."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in label)
    return safe[:40].strip("_")


def format_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, sec = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def copy_with_retry(src, dst, retries=DEFAULT_RETRIES):
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


def rip_disc(source, dest_root, disc_num, verbose=False):
    """Copy everything under `source` into a new disc folder under `dest_root`."""
    label = sanitize_label(os.path.basename(source.rstrip(os.sep)))
    today = datetime.now().strftime("%Y-%m-%d")
    disc_dirname = f"disc_{disc_num:02d}_{today}"
    if label:
        disc_dirname = f"{disc_dirname}_{label}"
    disc_dir = os.path.join(dest_root, disc_dirname)
    os.makedirs(disc_dir, exist_ok=True)

    print(f"\nSource:      {source}")
    print(f"Destination: {disc_dir}\n")

    # First pass: list all files (also tells us total count for progress)
    print("Indexing disc...", end=" ", flush=True)
    all_files = []
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for fn in filenames:
            all_files.append(os.path.join(dirpath, fn))
    total_files = len(all_files)
    print(f"{total_files} files found\n")

    # Second pass: copy
    copied = 0
    skipped = 0
    failed = 0
    bytes_done = 0
    failures = []
    retry_notes = []

    start = time.time()
    last_progress_at = start

    for i, src_path in enumerate(all_files, 1):
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
                if verbose:
                    print(f"  [{i}/{total_files}] {rel}  ({note})")
        else:
            failed += 1
            failures.append((rel, note))
            print(f"  [{i}/{total_files}] FAIL: {rel}  ({note})")

        # Periodic progress (every 2 seconds or every 50 files)
        now = time.time()
        if verbose or (now - last_progress_at) >= 2.0 or i == total_files:
            elapsed = now - start
            rate = i / elapsed if elapsed > 0 else 0
            pct = 100 * i / total_files if total_files else 100
            eta = (total_files - i) / rate if rate > 0 else 0
            print(f"  [{i}/{total_files}] {pct:5.1f}%  "
                  f"{rate:.1f} files/s  ETA {format_duration(eta)}",
                  flush=True)
            last_progress_at = now

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

    # Summary
    print("\n" + "=" * 64)
    print(f"Done in {format_duration(elapsed)}.")
    print(f"  Copied:  {copied}")
    print(f"  Skipped: {skipped} (already existed)")
    print(f"  Failed:  {failed}")
    print(f"  Bytes:   {format_bytes(bytes_done)}")
    print(f"  Manifest: {manifest_path}")
    if retry_notes:
        print(f"\n  {len(retry_notes)} file(s) needed retries — see manifest.")
    if failures:
        print(f"\n  ⚠  {failed} file(s) could not be read.")
        print("     For critical files, try:")
        print("       1. Clean the disc gently (microfiber, center-to-edge)")
        print("       2. Try a different optical drive")
        print("       3. Image the whole disc with ddrescue:")
        print("            brew install ddrescue")
        print("            ddrescue -r3 /dev/disk2 disc.iso disc.log")
        print("          then mount disc.iso and re-run this script on it.")

    return copied, failed


def eject_macos(path):
    try:
        subprocess.run(["diskutil", "eject", path],
                       check=True, capture_output=True, timeout=15)
        print(f"Ejected {os.path.basename(path)}.")
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired):
        print(f"(Couldn't auto-eject — please eject {path} manually.)")


def main():
    parser = argparse.ArgumentParser(
        description="Rip a medical imaging CD into a local folder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 rip_cd.py                          # auto-detect\n"
            "  python3 rip_cd.py /Volumes/MEDICAL_CD\n"
            "  python3 rip_cd.py /Volumes/CD -o ~/Imaging/raw_discs\n"
            "  python3 rip_cd.py /Volumes/CD --no-eject\n"
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
    args = parser.parse_args()

    # Resolve source
    if args.source:
        source = os.path.expanduser(args.source)
        if not os.path.isdir(source):
            print(f"ERROR: {source} is not a directory")
            sys.exit(1)
    else:
        candidates = detect_mounted_cds()
        if not candidates:
            print("No mounted CDs detected.")
            print("Insert a disc and wait for it to mount,")
            print("or pass the path explicitly: python3 rip_cd.py /Volumes/<name>")
            sys.exit(1)
        if len(candidates) > 1:
            print("Multiple candidates found:")
            for c in candidates:
                print(f"  {c}")
            print("\nSpecify one: python3 rip_cd.py <path>")
            sys.exit(1)
        source = candidates[0]
        print(f"Auto-detected disc: {source}")

    dest = os.path.expanduser(args.output)
    os.makedirs(dest, exist_ok=True)
    disc_num = args.disc_num if args.disc_num else next_disc_number(dest)

    copied, failed = rip_disc(source, dest, disc_num, verbose=args.verbose)

    if not args.no_eject and platform.system() == "Darwin" and copied > 0:
        eject_macos(source)

    sys.exit(2 if failed > 0 else 0)


if __name__ == "__main__":
    main()