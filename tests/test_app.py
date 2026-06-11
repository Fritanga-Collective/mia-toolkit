"""App shell: the --anonymize flag and the persistent Feedback button. The
arg-parse test is pure; the button test needs a real Tk and skips without one."""

import pytest

from mia.gui import app as app_mod


def test_parse_anonymize_flag():
    assert app_mod._parse([]).anonymize is False
    assert app_mod._parse(["--anonymize"]).anonymize is True


def test_feedback_link_in_launcher_footer():
    tk = pytest.importorskip("tkinter")
    from tests.helpers import new_tk_root_or_skip
    probe = new_tk_root_or_skip()
    probe.destroy()
    a = app_mod.App()
    a.root.withdraw()
    try:
        assert callable(a.send_feedback)

        def texts(w, out):
            try:
                out.append(str(w.cget("text")))
            except tk.TclError:
                pass
            for c in w.winfo_children():
                texts(c, out)

        found = []
        texts(a._current, found)            # the launcher (home) is current
        assert any("Feedback" in t for t in found)
        assert any("Read our blog" in t for t in found)
    finally:
        try:
            a.root.destroy()
        except tk.TclError:
            pass
