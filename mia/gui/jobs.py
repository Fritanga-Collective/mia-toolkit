"""Run a ``mia_core`` worker on a background thread, safely for Tkinter.

Tkinter is not thread-safe, so the worker runs off the UI thread and pushes
progress events through a :class:`queue.Queue`. The UI thread drains the queue
on a timer (``root.after``) and is the only thread that touches widgets.

``run_job`` is deliberately Tk-agnostic: it only needs an object with an
``after(ms, callable)`` method, which makes it unit-testable with a fake root.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Tuple

from mia_core.common import Cancelled, Progress

# A worker thunk: given an event emitter and a cancel token, do the work and
# return a result. Views wrap a core call, e.g.
#   lambda emit, cancel: ripper.rip_disc(src, dst, n, progress=emit, cancel=cancel)
Work = Callable[[Callable[[Progress], None], threading.Event], Any]
EventCb = Callable[[Progress], None]
# on_done(status, payload): status is "done" | "cancelled" | "error".
# payload is the result, None, or the Exception respectively.
DoneCb = Callable[[str, Any], None]

POLL_MS = 100


def run_job(
    root: Any,
    work: Work,
    on_event: EventCb,
    on_done: DoneCb,
    poll_ms: int = POLL_MS,
) -> threading.Event:
    """Start ``work`` on a daemon thread; pump its events to the UI thread.

    Returns the cancel :class:`threading.Event`; set it (e.g. from a Stop
    button) to ask the worker to abort at its next safe point.
    """
    q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
    cancel = threading.Event()

    def emit(p: Progress) -> None:
        q.put(("event", p))

    def worker() -> None:
        try:
            result = work(emit, cancel)
            q.put(("done", result))
        except Cancelled:
            q.put(("cancelled", None))
        except Exception as exc:  # surfaced to the UI as a plain-language error
            q.put(("error", exc))

    def drain() -> None:
        terminal = None
        while True:
            try:
                kind, payload = q.get_nowait()
            except queue.Empty:
                break
            if kind == "event":
                on_event(payload)
            else:
                terminal = (kind, payload)
                # Keep draining any events queued before the terminal marker.
        if terminal is not None:
            on_done(*terminal)
        else:
            root.after(poll_ms, drain)

    threading.Thread(target=worker, daemon=True).start()
    root.after(poll_ms, drain)
    return cancel
