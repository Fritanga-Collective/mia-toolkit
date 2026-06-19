"""Shared helpers for the worker modules.

Everything here is transport-agnostic. Workers report progress by calling a
``ProgressCallback`` with :class:`Progress` events and check an optional
:class:`CancelToken` between units of work, raising :class:`Cancelled` when a
cancel is observed. The command-line shims pass :class:`ConsoleProgress` as the
callback to reproduce the original console output; the GUI will pass its own.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional, Protocol


class Cancelled(Exception):
    """Raised inside a worker when its cancel token is observed set.

    Callers (CLI or GUI) catch this to treat the operation as interrupted.
    Workers always raise it at a safe point (between files), so partially
    written output can be cleanly resumed on a later run.
    """


class CancelToken(Protocol):
    """Anything with a ``threading.Event``-style ``is_set()`` works."""

    def is_set(self) -> bool:  # pragma: no cover - structural type
        ...


@dataclass
class Progress:
    """One progress update from a worker.

    ``kind`` distinguishes ordinary progress ticks from one-off notes so a
    consumer can, for example, print failures immediately while throttling the
    running percentage line.
    """

    done: int
    total: int
    elapsed: float = 0.0
    rate: float = 0.0
    eta: float = 0.0
    note: Optional[str] = None
    # "progress" | "info" | "retry" | "fail" | "debug" | "warn"
    # "warn" is a proactive, user-facing caution (e.g. a slow-media heads-up)
    # that isn't a failure — the UI shows it prominently but the job continues.
    kind: str = "progress"
    phase: str = ""
    # When True the worker can't give a meaningful done/total ratio (e.g. an
    # opaque OS bulk-copy): the UI should show an animated "working" bar, not a
    # made-up percentage/ETA.
    indeterminate: bool = False
    # Position within the current named group (e.g. one DICOM study) when the
    # work is chunked: done/total still drive the overall bar, but a consumer
    # can show "image {group_done} of {group_total}" for the chunk in progress.
    group_done: int = 0
    group_total: int = 0

    @property
    def pct(self) -> float:
        return 100.0 * self.done / self.total if self.total else 100.0


ProgressCallback = Callable[[Progress], None]
# THREADING CONTRACT: a ProgressCallback may be invoked from more than one
# thread for a single operation — e.g. ``deliver.copy_tree_verified`` emits the
# per-file debug stream from its ThreadPoolExecutor workers and ditto's verbose
# output from a stderr reader thread, alongside main-thread ticks. Callbacks
# MUST be thread-safe / self-marshalling. The GUI satisfies this: ``jobs`` hands
# workers an emitter that only does ``queue.Queue.put`` (thread-safe) and drains
# it on the Tk thread via ``root.after``; ``ConsoleProgress`` just prints. Don't
# touch Tk widgets or non-thread-safe aggregators directly from a callback.


# Process-global verbose switch. Workers consult is_verbose() before emitting
# kind="debug" timing/per-file notes (extra detail for diagnosing slowness), so
# the gating happens at the source rather than every consumer filtering it. On
# by default: the detail is captured into the collapsed technical pane + session
# log and only shown when the user expands "technical details", so the main view
# stays clean while the diagnostic trail is always there. (The CLI exposes a
# --verbose flag via ConsoleProgress; the GUI has no separate toggle.)
_VERBOSE = True


def is_verbose() -> bool:
    return _VERBOSE


def set_verbose(on: bool) -> None:
    global _VERBOSE
    _VERBOSE = bool(on)


def emit_debug(callback: Optional[ProgressCallback], note: str,
               phase: str = "") -> None:
    """Emit a kind="debug" note, but only when verbose mode is on. Cheap no-op
    otherwise, so call sites can wrap timing details without their own guard."""
    if callback is not None and _VERBOSE:
        callback(Progress(0, 0, kind="debug", note=note, phase=phase))


def emit(callback: Optional[ProgressCallback], progress: Progress) -> None:
    """Send a progress event if a callback was provided."""
    if callback is not None:
        callback(progress)


def emit_warn(callback: Optional[ProgressCallback], note: str,
              phase: str = "") -> None:
    """Emit a kind="warn" note — a proactive, user-facing caution (not a
    failure). Always sent when a callback exists (unlike emit_debug, which is
    verbose-gated): a slow-media heads-up is worth showing even in quiet mode."""
    if callback is not None:
        callback(Progress(0, 0, kind="warn", note=note, phase=phase))


def check_cancel(cancel: Optional[CancelToken]) -> None:
    """Raise :class:`Cancelled` if the token is set. No-op when token is None."""
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, sec = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def manifest_safe(text: str) -> str:
    """Escape control chars (newlines, etc.) before writing a path into a
    plain-text manifest. A filename can legally contain a newline on Unix;
    left raw it could forge manifest lines (e.g. a fake 'Total files : 9')."""
    return text.encode("unicode_escape").decode("ascii")


def is_dicom_file(path: str) -> bool:
    """DICOM files have the magic bytes 'DICM' at offset 128."""
    try:
        with open(path, "rb") as f:
            f.seek(128)
            return f.read(4) == b"DICM"
    except (OSError, IOError):
        return False


class ConsoleProgress:
    """A progress callback that prints to stdout like the original scripts.

    Running progress lines are throttled to ``interval`` seconds (or printed on
    every tick in verbose mode); ``info`` and ``fail`` notes print immediately,
    and ``retry`` notes print only in verbose mode.
    """

    def __init__(self, verbose: bool = False, interval: float = 2.0) -> None:
        self.verbose = verbose
        self.interval = interval
        self._last = 0.0

    def __call__(self, p: Progress) -> None:
        if p.kind == "info":
            if p.note is not None:
                print(p.note, flush=True)
            return
        if p.kind == "fail":
            print(f"  FAIL: {p.note}", flush=True)
            return
        if p.kind == "warn":
            if p.note is not None:
                print(f"  WARNING: {p.note}", flush=True)
            return
        if p.kind == "retry":
            if self.verbose and p.note is not None:
                print(f"  {p.note}", flush=True)
            return
        if p.kind == "debug":
            if self.verbose and p.note is not None:
                print(f"  [debug] {p.note}", flush=True)
            return
        now = time.time()
        if p.indeterminate:
            # No meaningful ratio — show a plain "working" heartbeat, not a
            # made-up percentage/ETA.
            if self.verbose or (now - self._last) >= self.interval:
                print(f"  copying… ({format_duration(p.elapsed)} elapsed)",
                      flush=True)
                self._last = now
            return
        if self.verbose or (now - self._last) >= self.interval or p.done == p.total:
            print(
                f"  [{p.done}/{p.total}] {p.pct:5.1f}%  "
                f"{p.rate:.1f} files/s  ETA {format_duration(p.eta)}",
                flush=True,
            )
            self._last = now
