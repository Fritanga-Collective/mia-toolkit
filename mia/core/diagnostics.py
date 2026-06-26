"""Build an anonymized diagnostic report the user can review and email us.

The app never phones home; this is the opposite of telemetry. The *user*
chooses to generate a report, sees exactly what it contains, and sends it
themselves. Because the technical log can carry PHI — usernames in home paths,
USB *volume* names, disc-folder labels and patient folders on the source media,
DICOM UIDs — everything is run through :func:`scrub` first, and the riskiest
high-volume lines (the per-file copy stream, clinical study descriptions) are
dropped entirely. Bias is toward over-redaction: an unrecognized path segment
becomes ``<x>``. The user is the final reviewer before anything is sent.
"""

from __future__ import annotations

import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

_HOME = os.path.expanduser("~")

# Throughput floor mirrored from deliver._SLOW_FILES_PER_SEC so the report's
# verdict and the worker's proactive warning agree on what "slow" means.
_SLOW_FILES_PER_SEC = 2.0
# Above this, a run is reading at (or near) the healthy FAT/exFAT rate, so the
# verdict should call it normal rather than "slow but expected". Set a touch
# below the observed ~7-9 files/s healthy band to leave honest headroom.
_HEALTHY_FILES_PER_SEC = 6.0

# Process-global "redact the displayed logs" switch, set by the --anonymize CLI
# flag. When on, the GUI runs each log line through scrub() before showing or
# writing it, so the technical pane, plain log, and session file are safe to
# show on a screencast while still reading realistically. Off by default.
_REDACT = False


def set_redact(on: bool) -> None:
    global _REDACT
    _REDACT = bool(on)


def redacting() -> bool:
    return _REDACT

# Path segments that are safe to keep — project/DICOM structure + code/runtime
# anchors (so tracebacks stay readable). Patient data never matches these;
# anything else in a path is redacted to <x>.
_STRUCT = {
    # mount / system roots (never PHI; keeping them readable)
    "volumes", "users", "home", "mnt", "media", "tmp", "var", "private",
    "opt", "usr", "applications", "programs", "program files", "appdata",
    "documents", "desktop", "downloads",
    # project / DICOM structure
    "raw_discs", "archive", "dicom", "viewer", "reports", "_documents",
    "dicomdir", "_manifest.txt", "delivery-log.txt", "readme.txt",
    "medicalarchive", "casereview",
    # code / runtime (so tracebacks stay readable)
    "mia", "core", "gui", "wizard", "i18n", "scripts", "tests", "packaging",
    "site-packages", "lib", "bin", "frozen", "contents", "resources",
    "pydicom", "openpyxl", "_internal", "dist", "build",
}
_CODE_EXT = {"py", "pyc", "pyo", "pyd", "so", "dylib"}

_USER = re.compile(r"(/(?:Users|home)/)[^/\s]+", re.I)
_WINUSER = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s]+", re.I)
_VOL = re.compile(r"(/(?:Volumes|mnt)/)[^/\s]+|(/media/)[^/\s]+(?:/[^/\s]+)?", re.I)
_UID = re.compile(r"\b\d+(?:\.\d+){3,}\b")
_DISC = re.compile(r"\bdisc_(\d+)[^/\\\s]*", re.I)          # disc_01_2020_SMITH -> disc_01
# A run of >=2 path segments (abs or relative), so free text like "verify/fill"
# is still segment-scrubbed but lone words are left alone.
_PATH = re.compile(r"(?:[A-Za-z]:)?(?:[\\/][^\\/\s]+){2,}|[\w.\-]+(?:[\\/][^\\/\s]+)+")


def _seg(seg: str) -> str:
    if seg == "" or seg in ("~", ".", ".."):
        return seg
    if seg.startswith("<") and seg.endswith(">"):
        return seg                                  # an earlier-pass placeholder
    low = seg.lower()
    if low in _STRUCT:
        return seg
    if re.fullmatch(r"disc_\d+", low):
        return seg
    if re.fullmatch(r"(?:im|st|se|pt|ps|rt|sr|em)[\w.\-]*", low):
        return seg
    if re.fullmatch(r"\d+", seg):
        return seg
    if re.fullmatch(r"python\d[\w.\-]*", low):
        return seg
    if "." in seg:
        ext = seg.rsplit(".", 1)[1].lower()
        if ext in _CODE_EXT:
            return seg                              # source files aren't PHI
        if re.fullmatch(r"[a-z0-9]{1,5}", ext):
            return "<x>." + ext                     # keep extension, drop stem
    return "<x>"


def _scrub_path(m: "re.Match") -> str:
    p = m.group(0)
    drive = ""
    dm = re.match(r"([A-Za-z]:)(.*)", p)
    if dm:
        drive, p = dm.group(1), dm.group(2)
    sep = "\\" if "\\" in p else "/"
    return drive + sep.join(_seg(s) for s in re.split(r"[\\/]", p))


def scrub(text: str) -> str:
    """Redact PHI/identifiers from free text. Over-redacts by design."""
    if not text:
        return text
    if _HOME and _HOME != "/" and _HOME in text:
        text = text.replace(_HOME, "~")
    text = _USER.sub(r"\1<user>", text)
    text = _WINUSER.sub(r"\1<user>", text)
    text = _VOL.sub(lambda m: (m.group(1) or m.group(2)) + "<drive>", text)
    text = _UID.sub("<uid>", text)
    text = _DISC.sub(r"disc_\1", text)
    text = _PATH.sub(_scrub_path, text)
    return text


def environment(app_version: Optional[str] = None) -> Dict[str, str]:
    """Non-identifying runtime facts useful for diagnosis.

    ``app_version`` is the *application's* version, which the library cannot
    know on its own — the host app injects it (the GUI passes it through the
    report's ``extra`` fields). When absent it reads as ``"?"``. The library
    always reports its OWN version as ``core_version`` (no reverse import of
    the application package — keeps ``mia.core`` standalone)."""
    from . import __version__ as core_ver
    return {
        "app_version": str(app_version) if app_version else "?",
        "core_version": str(core_ver),
        # Was "frozen: yes" (the PyInstaller flag), which read like "the app
        # froze." Say what it actually means to a maintainer triaging a report.
        "build": "packaged app" if getattr(sys, "frozen", False)
        else "source checkout",
        "os": platform.platform(),
        "arch": platform.machine(),
        "python": platform.python_version(),
    }


def _fmt_size(n: Optional[int]) -> str:
    """Human bytes for a report; 'unknown' when we couldn't read it."""
    if not isinstance(n, int) or n < 0:
        return "unknown"
    x = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if x < 1024:
            return f"{x:.1f} {unit}"
        x /= 1024
    return f"{x:.1f} TB"


def _filesystem(path: str) -> str:
    """Best-effort filesystem type for the volume holding ``path``. Per-OS,
    each branch falling back to 'unknown'. Never raises. A path that doesn't
    exist has no volume to describe → 'unknown' (we don't guess from root)."""
    if not path or not os.path.exists(path):
        return "unknown"
    try:
        system = platform.system()
        if system == "Darwin":
            # diskutil wants a mount point (e.g. /Volumes/USB), not an arbitrary
            # path inside it, and it reports failure via an "Error" key in the
            # plist (returncode stays 0). Walk up to the nearest mount point.
            probe = os.path.abspath(path)
            for _ in range(64):
                if os.path.ismount(probe) or probe == os.sep:
                    break
                parent = os.path.dirname(probe)
                if parent == probe:
                    break
                probe = parent
            out = subprocess.run(
                ["diskutil", "info", "-plist", probe],
                capture_output=True, timeout=5)
            if out.returncode == 0 and out.stdout:
                info = plistlib.loads(out.stdout)
                if not info.get("Error"):
                    fs = info.get("FilesystemName") or info.get(
                        "FilesystemType")
                    if fs:
                        return str(fs)
        elif system == "Windows":
            # fsutil fsinfo volumeinfo <root> prints a "File System Name : NTFS"
            # style line. Use the drive root of the path.
            drive = os.path.splitdrive(os.path.abspath(path))[0] or "C:"
            out = subprocess.run(
                ["fsutil", "fsinfo", "volumeinfo", drive + "\\"],
                capture_output=True, text=True, timeout=5)
            if out.returncode == 0 and out.stdout:
                for line in out.stdout.splitlines():
                    if "file system name" in line.lower():
                        return line.split(":", 1)[1].strip() or "unknown"
        elif system == "Linux":
            # Match the longest mountpoint that is a prefix of our path.
            target = os.path.abspath(path)
            best_fs, best_len = "unknown", -1
            with open("/proc/mounts", encoding="utf-8", errors="replace") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        mp, fstype = parts[1], parts[2]
                        if target == mp or target.startswith(mp.rstrip("/") + "/"):
                            if len(mp) > best_len:
                                best_fs, best_len = fstype, len(mp)
            return best_fs
    except Exception:
        pass
    return "unknown"


def media_info(path: str) -> Dict[str, str]:
    """Best-effort, non-raising facts about the volume holding ``path``:
    ``{filesystem, total, free}``. Each key falls back to 'unknown'. Used to
    give a slow-copy report context (e.g. exFAT on a small drive). Never raises
    on a bad/missing path — diagnosis must not crash the reporter."""
    from . import deliver  # local import: deliver imports common, not us

    info = {"filesystem": "unknown", "total": "unknown", "free": "unknown"}
    if not path:
        return info
    info["filesystem"] = _filesystem(path)
    # Total: walk up to the nearest existing parent (mirrors deliver.free_space).
    try:
        p = os.path.abspath(path)
        while p and not os.path.exists(p):
            parent = os.path.dirname(p)
            if parent == p:
                break
            p = parent
        usage = shutil.disk_usage(p or os.sep)
        info["total"] = _fmt_size(usage.total)
    except Exception:
        pass
    try:
        info["free"] = _fmt_size(deliver.free_space(path))
    except Exception:
        pass
    return info


def verdict(summary: Dict) -> str:
    """A conservative, caveated read of a run summary for the report. Never an
    accusation — copy media is genuinely slow, and we'd rather say 'consistent
    with normal overhead' than wrongly condemn a healthy drive. Thresholds come
    from in-house delivery profiling (healthy FAT/exFAT ≈ 7-9 files/s)."""
    failed = int(summary.get("failed", 0) or 0)
    retries = int(summary.get("retries", 0) or 0)
    fps = float(summary.get("files_per_sec", 0) or 0)
    fs = str(summary.get("filesystem", "") or "").lower()
    if summary.get("cancelled"):
        return ("The copy was stopped before it finished (cancelled). Re-run to "
                "resume; this is not a fault.")
    if failed > 0 or retries > 0:
        return ("Errors or retries happened during the copy — the drive, cable, "
                "or port may be failing. Try another drive/port and re-run.")
    if 0 < fps < _SLOW_FILES_PER_SEC:
        return ("Unusually slow (well under ~2 files/s) with no errors — "
                "possible failing/counterfeit drive, a bad port, or a USB hub. "
                "Worth trying a known-good drive plugged straight in.")
    fatlike = any(t in fs for t in ("fat", "exfat", "msdos"))
    if fatlike and 0 < fps < _HEALTHY_FILES_PER_SEC:
        return ("Slow but consistent with normal small-file overhead for many "
                "DICOM files on FAT/exFAT (the per-file metadata cost) — not a "
                "fault.")
    if fps > 0:
        return "Throughput looks normal; no problem indicators."
    return "Not enough information to judge throughput."


# Per-file / clinical lines: high volume, low diagnostic value, highest PHI
# surface — dropped from the report (we keep their count for context). We drop
# only the per-file *copy* stream: the in-process "Copying …" lines and ditto's
# verbose "ditto: Copying …" items. Other ditto lines are kept — ditto reports
# real errors as "ditto: ditto: <message>" (its own stderr, re-prefixed), and
# those are low-volume and valuable for diagnosis.
_DROP = re.compile(r"^(?:copying |ditto: copying |indexing study:)", re.I)
# Progress heartbeats emitted by Presenter.feed, e.g.
# "[412/640] 64.4%  9/s  ETA 2m 3s". High volume, zero diagnostic value now
# that the run summary carries throughput — drop them too (count kept).
_TICK = re.compile(r"^\[\d+/\d+\]")


def filter_log(lines: List[str]) -> Tuple[List[str], int]:
    """Keep milestones/timings/errors/warnings; drop the per-file copy stream,
    clinical study-description lines, and the progress heartbeats (the summary
    now carries throughput). Returns (kept, dropped_count). Lines are
    ``"HH:MM:SS  <note>"``; we match on the note."""
    kept, dropped = [], 0
    for line in lines:
        note = line.split("  ", 1)[1] if "  " in line else line
        stripped = note.strip()
        if _DROP.match(stripped) or _TICK.match(stripped):
            dropped += 1
        else:
            kept.append(line)
    return kept, dropped


def _render_summary(summary: Dict) -> List[str]:
    """The '## Last operation' + '## Media' + verdict block. All values are
    non-PHI numbers/labels except slowest-file rel paths, which are scrubbed."""
    def g(key, default="?"):
        v = summary.get(key)
        return default if v is None else v

    out = ["## Last operation",
           f"- operation: {g('op', 'copy to USB')}",
           f"- result: {g('result')}",
           f"- files copied: {g('files_copied')}",
           f"- files skipped (already present): {g('files_skipped')}",
           f"- files failed: {g('failed')}",
           f"- retries (recovered after a bad write): {g('retries', 0)}",
           f"- elapsed: {float(g('elapsed', 0) or 0):.1f}s",
           f"- throughput: {float(g('files_per_sec', 0) or 0):.1f} files/s, "
           f"{float(g('mb_per_sec', 0) or 0):.1f} MB/s"]
    if summary.get("slow_media"):
        out.append("- slow-media warning was shown during this run")
    out += ["", "## Media",
            f"- filesystem: {g('filesystem', 'unknown')}",
            f"- free: {g('free', 'unknown')}",
            f"- total: {g('total', 'unknown')}"]
    out += ["", "## Verdict", verdict(summary)]
    return out


def build_report(notes: str, log_lines: List[str], *,
                 extra: Optional[Dict[str, str]] = None,
                 when: Optional[str] = None,
                 summary: Optional[Dict] = None,
                 max_log_lines: int = 400) -> str:
    """Assemble the anonymized report. ``notes`` is the user's free text;
    ``log_lines`` the panel's technical log; ``extra`` optional GUI fields
    (language, screen); ``summary`` an optional structured run summary (from a
    recent delivery) rendered before the activity log. All log content and the
    slowest-file paths are scrubbed; the tail is capped."""
    env = environment()
    if extra:
        env.update({k: str(v) for k, v in extra.items()})
    stamp = when or time.strftime("%Y-%m-%d %H:%M:%S")

    out = ["MIA Toolkit — diagnostic report",
           f"Generated: {stamp}",
           "",
           "This report is anonymized: no patient names, no file contents, no "
           "DICOM identifiers. Review it below before sending — nothing is sent "
           "automatically.",
           "",
           "## Environment"]
    out += [f"- {k}: {v}" for k, v in env.items()]

    out += ["", "## What happened (your words)",
            (notes.strip() or "(none provided)")]

    if summary:
        out.append("")
        out += _render_summary(summary)

    kept, dropped = filter_log(log_lines)
    if len(kept) > max_log_lines:
        clipped = len(kept) - max_log_lines
        kept = kept[-max_log_lines:]
    else:
        clipped = 0
    out += ["", "## Activity log (anonymized)"]
    if dropped:
        out.append(f"({dropped} per-file/heartbeat/detail lines omitted)")
    if clipped:
        out.append(f"(…{clipped} earlier lines trimmed; showing the last "
                   f"{max_log_lines})")
    out.append(scrub("\n".join(kept)) if kept else "(no activity recorded)")

    if summary and summary.get("slowest_files"):
        out += ["", "## Slowest files (anonymized)"]
        for rel, secs in summary["slowest_files"]:
            out.append(f"- {scrub(str(rel))}: {float(secs):.2f}s")

    out += ["", "— end of report —"]
    return "\n".join(out)
