"""Quit confirmation: every close path asks first, and a confirmed quit stops
running work safely before tearing down. Needs a real Tk; skipped without one."""

import pytest

tk = pytest.importorskip("tkinter")

from mia.gui import app as app_mod  # noqa: E402
from tests.helpers import new_tk_root_or_skip  # noqa: E402


@pytest.fixture
def app():
    # Probe for a usable window server (and skip in CI) *before* building the
    # App, which creates its own root — App() would otherwise hang on a runner.
    probe = new_tk_root_or_skip()
    probe.destroy()
    a = app_mod.App()
    a.root.withdraw()
    yield a
    try:
        a.root.destroy()
    except tk.TclError:
        pass


def _fake_view(busy, calls):
    class V:
        def is_busy(self):
            return busy

        def stop(self):
            calls.append("stop")

        def on_leave(self):
            calls.append("on_leave")

    return V()


def test_quit_declined_does_not_destroy(app, monkeypatch):
    monkeypatch.setattr(app_mod.messagebox, "askyesno", lambda *a, **k: False)
    destroyed = []
    monkeypatch.setattr(app.root, "destroy", lambda: destroyed.append(True))
    app.request_quit()
    assert not destroyed


def test_quit_confirmed_when_idle_destroys(app, monkeypatch):
    monkeypatch.setattr(app_mod.messagebox, "askyesno", lambda *a, **k: True)
    destroyed = []
    monkeypatch.setattr(app.root, "destroy", lambda: destroyed.append(True))
    app.request_quit()
    assert destroyed


def test_quit_while_busy_stops_work_then_destroys(app, monkeypatch):
    calls = []
    app._current = _fake_view(busy=True, calls=calls)
    monkeypatch.setattr(app_mod.messagebox, "askyesno", lambda *a, **k: True)
    destroyed = []
    monkeypatch.setattr(app.root, "destroy", lambda: destroyed.append(True))
    app.request_quit()
    assert "stop" in calls          # work was signalled to stop safely
    assert destroyed                # ...before we tore the window down
