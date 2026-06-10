#!/usr/bin/env python3
"""Profile the USB delivery copy to find the speed bottleneck.

The delivery (mia.core.deliver.copy_tree_verified) is I/O-bound, so a plain
CPU profiler is misleading: during the native `ditto`/`robocopy` phase the
Python process only polls a subprocess, and the verify pass is dominated by
filesystem syscalls, not Python. This harness instead measures the thing that
matters — wall-clock per phase and throughput — and A/Bs the two copiers so
you can tell whether the device, the native tool, or our verify pass is the
limit.

What it reports, per run:
  * walk / native-copy / verify-pass seconds (read from the verbose debug log
    the worker already emits)
  * MB/s and files/s for the native phase (small files on exFAT cap on
    files/s long before MB/s — that distinction is the whole diagnosis)
  * total wall time

It runs up to four configurations so the comparison is apples-to-apples:
  native+size, native+thorough(SHA-256), inprocess+size, inprocess+thorough.

Usage:
    # Synthetic tree (defaults: 4000 files x 256 KB ≈ 1 GB of small files,
    # which is the realistic DICOM-on-USB shape) to a real USB mount:
    python scripts/profile_delivery.py --synthetic 4000 --dest /Volumes/USB

    # A real built archive:
    python scripts/profile_delivery.py --src ~/Documents/MedicalArchive/Archive \
        --dest /Volumes/USB

    # Just the native copier, size-only verify (fastest single number):
    python scripts/profile_delivery.py --synthetic 4000 --dest /Volumes/USB \
        --only native-size

To go deeper on the *verify pass* specifically (the only CPU/syscall-heavy
part), wrap a single in-process run in a real profiler — see the banner this
script prints at the end.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time

# Run from a checkout without installing.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mia.core import common, deliver  # noqa: E402

_WALK = re.compile(r"walked (\d+) files in ([\d.]+)s")
_NATIVE = re.compile(r"native copy finished: rc=(-?\d+) in ([\d.]+)s")
_VERIFY = re.compile(r"verify/fill pass: (\d+) copied, (\d+) skipped, "
                     r"(\d+) failed in ([\d.]+)s")


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def make_synthetic(root: str, count: int, size: int) -> tuple[int, int]:
    """Write `count` files of `size` bytes spread across subdirs (mimicking a
    DICOM study/series tree, which is what makes USB copies slow: many small
    files, not a few big ones). Returns (files, total_bytes)."""
    blob = os.urandom(size) if size <= 1_000_000 else os.urandom(1_000_000)
    total = 0
    per_dir = 200
    for i in range(count):
        d = os.path.join(root, f"study_{i // per_dir:04d}",
                         f"series_{(i // 20) % 10:02d}")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"IM{i:06d}")
        with open(p, "wb") as f:
            written = 0
            while written < size:
                chunk = blob[: min(len(blob), size - written)]
                f.write(chunk)
                written += len(chunk)
        total += size
    return count, total


def tree_stats(root: str) -> tuple[int, int]:
    files = bytes_ = 0
    for dp, _, fns in os.walk(root):
        for fn in fns:
            files += 1
            try:
                bytes_ += os.lstat(os.path.join(dp, fn)).st_size
            except OSError:
                pass
    return files, bytes_


def run_one(label: str, src: str, dest: str, *, prefer_native: bool,
            thorough: bool) -> dict:
    """One delivery into a *fresh* dest subdir; returns parsed phase timings."""
    target = os.path.join(dest, f"_profile_{label}")
    if os.path.isdir(target):
        shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target, exist_ok=True)

    events: list = []
    common.set_verbose(True)  # so the worker emits its phase-timing debug notes
    t0 = time.perf_counter()
    try:
        result = deliver.copy_tree_verified(
            src, target, thorough=thorough, prefer_native=prefer_native,
            progress=events.append)
    finally:
        common.set_verbose(False)
    wall = time.perf_counter() - t0

    notes = [e.note for e in events if e.kind == "debug" and e.note]
    out = {"label": label, "wall": wall, "result": result,
           "walk": None, "native": None, "verify": None, "rc": None}
    for n in notes:
        if (m := _WALK.search(n)):
            out["walk"] = float(m.group(2))
        elif (m := _NATIVE.search(n)):
            out["rc"] = int(m.group(1))
            out["native"] = float(m.group(2))
        elif (m := _VERIFY.search(n)):
            out["verify"] = float(m.group(4))
    shutil.rmtree(target, ignore_errors=True)
    return out


def report(runs: list[dict], files: int, total_bytes: int) -> None:
    print()
    print(f"  source: {files} files, {human_bytes(total_bytes)}")
    print("  " + "-" * 76)
    hdr = (f"  {'configuration':<22}{'wall':>8}{'walk':>8}{'native':>9}"
           f"{'verify':>9}{'MB/s*':>9}{'files/s*':>10}")
    print(hdr)
    print("  " + "-" * 76)
    for r in runs:
        native = r["native"]
        mbps = (total_bytes / 1024 / 1024 / native) if native else 0
        fps = (files / native) if native else 0
        print(f"  {r['label']:<22}"
              f"{r['wall']:>7.1f}s"
              f"{(r['walk'] or 0):>7.1f}s"
              f"{(native or 0):>8.1f}s"
              f"{(r['verify'] or 0):>8.1f}s"
              f"{mbps:>9.1f}{fps:>10.0f}")
    print("  " + "-" * 76)
    print("  * MB/s and files/s are for the native phase only "
          "(blank native = in-process copier).")
    print()
    _interpret(runs, files, total_bytes)


def _interpret(runs: list[dict], files: int, total_bytes: int) -> None:
    by = {r["label"]: r for r in runs}
    print("  Reading the result:")
    ns = by.get("native-size")
    nt = by.get("native-thorough")
    ip = by.get("inprocess-size")
    if ns and ns["native"]:
        mbps = total_bytes / 1024 / 1024 / ns["native"]
        fps = files / ns["native"]
        print(f"   • native copy: {mbps:.1f} MB/s, {fps:.0f} files/s. "
              "If MB/s is far below the drive's rated write speed but files/s "
              "is low, the bottleneck is per-file overhead (exFAT metadata), "
              "not bandwidth — the device, not our code.")
        if ns["verify"] and ns["native"] and ns["verify"] > ns["native"]:
            print("   • the SIZE-ONLY verify pass costs more than the copy "
                  "itself → re-stat/open of every file on slow media is the "
                  "bottleneck. Consider trusting ditto's exit code and "
                  "skipping the re-stat when the native tool succeeded.")
    if ns and nt and ns["native"] and nt["native"]:
        dv = (nt["verify"] or 0) - (ns["verify"] or 0)
        print(f"   • SHA-256 (thorough) adds ~{dv:.1f}s to verify → that delta "
              "is CPU-bound hashing; profile it with scalene if it dominates.")
    if ns and ip and ns["wall"] and ip["wall"]:
        ratio = ip["wall"] / ns["wall"]
        if ratio < 0.8:
            verdict = (f"in-process is ~{1 / ratio:.1f}× FASTER than ditto — "
                       "the native tool is a pessimization here; consider "
                       "flipping prefer_native off for this platform")
        elif ratio <= 1.3:
            verdict = ("the two copiers are comparable — the device is the "
                       "limit, not our code")
        else:
            verdict = (f"ditto is ~{ratio:.1f}× faster than in-process — keep "
                       "the native fast-path")
        print(f"   • in-process vs native wall ratio: {ratio:.2f}× → {verdict}.")
    print()
    print("  Deeper dive on the verify pass (the only Python-heavy part):")
    print("    scalene --cli --- scripts/profile_delivery.py "
          "--synthetic 2000 --dest <USB> --only inprocess-thorough")
    print("    pyinstrument scripts/profile_delivery.py "
          "--synthetic 2000 --dest <USB> --only inprocess-thorough")


CONFIGS = {
    "native-size": dict(prefer_native=True, thorough=False),
    "native-thorough": dict(prefer_native=True, thorough=True),
    "inprocess-size": dict(prefer_native=False, thorough=False),
    "inprocess-thorough": dict(prefer_native=False, thorough=True),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--src", help="existing tree to copy (e.g. a built Archive/)")
    g.add_argument("--synthetic", type=int, metavar="N",
                   help="generate N small files as the source instead")
    ap.add_argument("--file-size", type=int, default=256 * 1024,
                    help="synthetic file size in bytes (default 256 KB)")
    ap.add_argument("--dest", required=True,
                    help="destination root (a USB mount to measure the real thing)")
    ap.add_argument("--only", choices=list(CONFIGS),
                    help="run a single configuration instead of all four")
    args = ap.parse_args()

    if not os.path.isdir(args.dest):
        ap.error(f"--dest is not a directory: {args.dest}")

    tmp = None
    if args.synthetic:
        tmp = tempfile.mkdtemp(prefix="mia_profile_src_")
        print(f"  generating {args.synthetic} × {human_bytes(args.file_size)} "
              "synthetic files…", flush=True)
        files, total = make_synthetic(tmp, args.synthetic, args.file_size)
        src = tmp
    else:
        src = os.path.abspath(os.path.expanduser(args.src))
        if not os.path.isdir(src):
            ap.error(f"--src is not a directory: {src}")
        files, total = tree_stats(src)

    try:
        labels = [args.only] if args.only else list(CONFIGS)
        runs = []
        for label in labels:
            print(f"  running {label}…", flush=True)
            runs.append(run_one(label, src, args.dest, **CONFIGS[label]))
        report(runs, files, total)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
