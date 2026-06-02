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
    kind: str = "progress"  # "progress" | "info" | "retry" | "fail"
    phase: str = ""

    @property
    def pct(self) -> float:
        return 100.0 * self.done / self.total if self.total else 100.0


ProgressCallback = Callable[[Progress], None]


def emit(callback: Optional[ProgressCallback], progress: Progress) -> None:
    """Send a progress event if a callback was provided."""
    if callback is not None:
        callback(progress)


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
        if p.kind == "retry":
            if self.verbose and p.note is not None:
                print(f"  {p.note}", flush=True)
            return
        now = time.time()
        if self.verbose or (now - self._last) >= self.interval or p.done == p.total:
            print(
                f"  [{p.done}/{p.total}] {p.pct:5.1f}%  "
                f"{p.rate:.1f} files/s  ETA {format_duration(p.eta)}",
                flush=True,
            )
            self._last = now
