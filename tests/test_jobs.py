"""Tests for the background job runner, with a fake (display-free) root."""

import threading
import time

from mia.core.common import Cancelled, Progress
from mia.gui import jobs


class FakeRoot:
    """Records the next scheduled callback instead of running an event loop."""

    def __init__(self):
        self.scheduled = None

    def after(self, ms, cb):
        self.scheduled = cb


def pump(root, done, timeout=5.0):
    """Drive the recorded drain callback until the job reports completion."""
    start = time.monotonic()
    while not done["done"] and time.monotonic() - start < timeout:
        cb = root.scheduled
        root.scheduled = None
        if cb is not None:
            cb()
        else:
            time.sleep(0.005)


def test_run_job_delivers_events_and_result():
    root = FakeRoot()
    events = []
    done = {"done": False}

    def work(emit, cancel):
        emit(Progress(1, 2, phase="copy"))
        emit(Progress(2, 2, phase="copy"))
        return "RESULT"

    def on_done(status, payload):
        done.update(done=True, status=status, payload=payload)

    jobs.run_job(root, work, events.append, on_done, poll_ms=1)
    pump(root, done)

    assert done["status"] == "done"
    assert done["payload"] == "RESULT"
    assert len(events) == 2


def test_run_job_reports_error():
    root = FakeRoot()
    done = {"done": False}

    def work(emit, cancel):
        raise ValueError("boom")

    def on_done(status, payload):
        done.update(done=True, status=status, payload=payload)

    jobs.run_job(root, work, lambda p: None, on_done, poll_ms=1)
    pump(root, done)

    assert done["status"] == "error"
    assert isinstance(done["payload"], ValueError)


def test_run_job_cancellation():
    root = FakeRoot()
    done = {"done": False}
    started = threading.Event()

    def work(emit, cancel):
        started.set()
        while not cancel.is_set():
            time.sleep(0.005)
        raise Cancelled()

    def on_done(status, payload):
        done.update(done=True, status=status)

    cancel = jobs.run_job(root, work, lambda p: None, on_done, poll_ms=1)
    assert started.wait(2.0)
    cancel.set()
    pump(root, done)

    assert done["status"] == "cancelled"
