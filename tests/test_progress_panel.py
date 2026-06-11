"""Panel behavior that needs a real Tk: the working spinner, the indeterminate
native-copy phase, and debug-note routing. Skipped where there's no display."""

import pytest

pytest.importorskip("tkinter")

from mia.core import diagnostics  # noqa: E402
from mia.core.common import Progress  # noqa: E402
from mia.gui.progress_panel import ProgressLogPanel  # noqa: E402
from tests.helpers import new_tk_root_or_skip  # noqa: E402


@pytest.fixture
def panel():
    root = new_tk_root_or_skip()
    p = ProgressLogPanel(root)
    yield p
    root.destroy()


def test_session_start_runs_spinner_and_close_stops_it(panel, tmp_path):
    panel.start_session_log(str(tmp_path / "logs"))
    panel.set_status("Working")
    panel.update()
    assert panel._spinning and panel._spin_job is not None
    # A frame is prefixed onto the base status; the base text is preserved.
    assert panel.status.cget("text").endswith("Working")
    assert panel._base_status == "Working"

    panel.close_session_log()
    panel.update()
    assert not panel._spinning and panel._spin_job is None
    assert panel.status.cget("text") == "Working"  # frame prefix cleared


def test_indeterminate_then_determinate_switches_bar_mode(panel):
    panel.on_event(Progress(0, 100, elapsed=120.0, phase="copy",
                            indeterminate=True))
    panel.update()
    assert str(panel.bar["mode"]) == "indeterminate"
    assert "100" in panel._base_status  # localized "Copying 100 files…"

    panel.on_event(Progress(50, 100, elapsed=121.0, phase="copy"))
    panel.update()
    assert str(panel.bar["mode"]) == "determinate"


def test_debug_event_goes_only_to_technical_log(panel):
    before = len(panel._tech_lines)
    panel.on_event(Progress(0, 0, kind="debug", note="walked 9 files in 0.1s"))
    assert len(panel._tech_lines) == before + 1
    assert "walked 9 files" in panel._tech_lines[-1]


def test_anonymize_scrubs_logs(panel):
    # --anonymize: log lines are scrubbed before they hit the pane / file /
    # in-memory buffer, so a screencast leaks no PHI.
    diagnostics.set_redact(True)
    try:
        panel.log_technical("/Users/jane/raw_discs/disc_01_SMITH/IM1")
        panel.log_plain("copying /Volumes/PATIENT_USB/disc_02_LOPEZ/IM2")
    finally:
        diagnostics.set_redact(False)
    joined = "\n".join(panel._tech_lines)
    assert "jane" not in joined and "SMITH" not in joined
    plain = panel.plain_log.get("1.0", "end")
    assert "PATIENT_USB" not in plain and "LOPEZ" not in plain
