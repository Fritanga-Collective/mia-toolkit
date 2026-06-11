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
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

_HOME = os.path.expanduser("~")

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


def environment() -> Dict[str, str]:
    """Non-identifying runtime facts useful for diagnosis."""
    try:
        from mia import __version__ as ver
    except Exception:
        ver = "?"
    return {
        "app_version": str(ver),
        "frozen": "yes" if getattr(sys, "frozen", False) else "no (source)",
        "os": platform.platform(),
        "arch": platform.machine(),
        "python": platform.python_version(),
    }


# Per-file / clinical lines: high volume, low diagnostic value, highest PHI
# surface — dropped from the report (we keep their count for context).
_DROP = re.compile(r"^(?:copying |ditto: (?!.*\brc=)|indexing study:)", re.I)


def filter_log(lines: List[str]) -> Tuple[List[str], int]:
    """Keep milestones/timings/errors; drop the per-file copy stream and
    clinical study-description lines. Returns (kept, dropped_count). Lines are
    ``"HH:MM:SS  <note>"``; we match on the note."""
    kept, dropped = [], 0
    for line in lines:
        note = line.split("  ", 1)[1] if "  " in line else line
        if _DROP.match(note.strip()):
            dropped += 1
        else:
            kept.append(line)
    return kept, dropped


def build_report(notes: str, log_lines: List[str], *,
                 extra: Optional[Dict[str, str]] = None,
                 when: Optional[str] = None,
                 max_log_lines: int = 400) -> str:
    """Assemble the anonymized report. ``notes`` is the user's free text;
    ``log_lines`` the panel's technical log; ``extra`` optional GUI fields
    (language, screen). All log content is scrubbed; the tail is capped."""
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

    kept, dropped = filter_log(log_lines)
    if len(kept) > max_log_lines:
        clipped = len(kept) - max_log_lines
        kept = kept[-max_log_lines:]
    else:
        clipped = 0
    out += ["", "## Activity log (anonymized)"]
    if dropped:
        out.append(f"({dropped} per-file/detail lines omitted for privacy)")
    if clipped:
        out.append(f"(…{clipped} earlier lines trimmed; showing the last "
                   f"{max_log_lines})")
    out.append(scrub("\n".join(kept)) if kept else "(no activity recorded)")
    out += ["", "— end of report —"]
    return "\n".join(out)
