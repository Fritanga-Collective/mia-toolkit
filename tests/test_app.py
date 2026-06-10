"""App shell: the --anonymize flag and the persistent Feedback button. The
arg-parse test is pure; the button test needs a real Tk and skips without one."""

import pytest

from mia.gui import app as app_mod


def test_parse_anonymize_flag():
    assert app_mod._parse([]).anonymize is False
    assert app_mod._parse(["--anonymize"]).anonymize is True


def test_feedback_button_present_and_callable():
    tk = pytest.importorskip("tkinter")
    from tests.helpers import new_tk_root_or_skip
    probe = new_tk_root_or_skip()
    probe.destroy()
    a = app_mod.App()
    a.root.withdraw()
    try:
        assert "Feedback" in a._feedback_btn.cget("text")
        assert callable(a.send_feedback)
    finally:
        try:
            a.root.destroy()
        except tk.TclError:
            pass
