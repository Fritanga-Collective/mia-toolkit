"""Turn structured worker events into human text.

Two audiences from one event stream:

* **plain** — friendly, throttled lines for the always-visible log
  ("Copying file 412 of 640…", "Recovered a file after a retry.").
* **technical** — the raw ``note`` or a compact progress heartbeat for the
  expandable "technical details" pane and the session log file.

The progress *bar* is driven directly from :class:`Progress` by the view and is
never throttled; only the textual log lines are rate-limited here so a
multi-thousand-file run doesn't scroll into a blur (or flood the widget).
"""

from __future__ import annotations

import errno
import time
import traceback
from typing import Callable, Optional, Tuple

from mia.core.common import Progress, format_duration
from .i18n import _

PlainTech = Tuple[Optional[str], Optional[str]]


class Presenter:
    """Stateful so it can throttle per-file progress ticks to ~1/second.

    ``clock`` is injectable for testing.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 interval: float = 1.0) -> None:
        self._clock = clock
        self._interval = interval
        self._last_tick = float("-inf")

    def feed(self, p: Progress) -> PlainTech:
        """Return (plain_line | None, technical_line | None) for one event."""
        # Events that carry a note (info / retry / fail) are milestones — always
        # shown. The raw note (which may contain file paths) goes to technical;
        # plain gets a friendly summary.
        if p.note is not None:
            return self._plain_for_note(p), p.note

        # A pure progress tick: throttle, but always emit the final 100% tick.
        now = self._clock()
        if not (p.done == p.total or (now - self._last_tick) >= self._interval):
            return None, None
        self._last_tick = now

        technical = (f"[{p.done}/{p.total}] {p.pct:4.1f}%  "
                     f"{p.rate:.0f}/s  ETA {format_duration(p.eta)}")
        return self._plain_tick(p), technical

    @staticmethod
    def _plain_for_note(p: Progress) -> Optional[str]:
        if p.kind == "retry":
            return _("Recovered a file after a retry.")
        if p.kind == "fail":
            return _("⚠ Could not read a file (see technical details).")
        return p.note  # info notes are already user-facing

    @staticmethod
    def _plain_tick(p: Progress) -> str:
        if p.phase == "copy":
            # When copying study-by-study, count images within the current
            # study (the milestone above names which one) instead of an opaque
            # "file 1212 of 11165".
            if p.group_total:
                return _("Copying image {done} of {total}…").format(
                    done=p.group_done, total=p.group_total)
            tmpl = _("Copying file {done} of {total}…")
        elif p.phase == "scan":
            tmpl = _("Scanning file {done} of {total}…")
        elif p.phase == "index":
            tmpl = _("Indexing image {done} of {total}…")
        else:
            tmpl = _("Working… {done} of {total}")
        return tmpl.format(done=p.done, total=p.total)


def humanize_exception(exc: BaseException) -> str:
    """A plain-language, traceback-free message for an unexpected failure."""
    if isinstance(exc, PermissionError):
        return _("Permission denied. The destination may be read-only or locked. "
                 "Try a different folder, or check the drive isn't write-protected.")
    if isinstance(exc, FileNotFoundError):
        return _("A needed file or folder was not found. A disc may have been "
                 "ejected too early, or a folder was moved.")
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.ENOSPC:
        return _("The disk is full. Free up space or choose a drive with more room.")
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EROFS:
        return _("That location is read-only. Choose a different destination folder.")
    return _("Something went wrong. See the technical details below.")


def exception_detail(exc: BaseException) -> str:
    """The full traceback as text — for the technical pane and log file only."""
    return "".join(
        traceback.format_exception(type(exc), exc, exc.__traceback__)
    )
