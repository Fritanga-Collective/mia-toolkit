import os

import pytest

from mia_core.common import Cancelled
from mia_core import ripper
from tests.helpers import CancelNow


def test_sanitize_label():
    assert ripper.sanitize_label("MEDICAL CD!") == "MEDICAL_CD"
    assert ripper.sanitize_label("a/b\\c:d") == "a_b_c_d"
    assert ripper.sanitize_label("x" * 80) == "x" * 40


def test_next_disc_number(tmp_path):
    assert ripper.next_disc_number(str(tmp_path)) == 1
    (tmp_path / "disc_01_2020-01-01_A").mkdir()
    (tmp_path / "disc_04_2020-01-02_B").mkdir()
    assert ripper.next_disc_number(str(tmp_path)) == 5


def test_rip_copies_all_files_and_skips_metadata(fake_disc, tmp_path):
    dest = tmp_path / "out"
    result = ripper.rip_disc(fake_disc, str(dest), 1)

    # 4 real files (2 IMs, run.exe, README.TXT); the .Spotlight-V100 dir is skipped
    assert result.total_files == 4
    assert result.copied == 4
    assert result.failed == 0
    assert os.path.isdir(result.disc_dir)
    assert os.path.exists(result.manifest_path)
    assert not os.path.exists(os.path.join(result.disc_dir, ".Spotlight-V100"))
    # Files landed where expected
    assert os.path.exists(os.path.join(result.disc_dir, "DICOM", "ST0001", "IM0001"))


def test_rip_is_resumable(fake_disc, tmp_path):
    dest = tmp_path / "out"
    first = ripper.rip_disc(fake_disc, str(dest), 1)
    assert first.copied == 4

    # Re-run into the SAME disc number -> everything already present -> skipped
    second = ripper.rip_disc(fake_disc, str(dest), 1)
    assert second.copied == 0
    assert second.skipped == 4
    assert second.failed == 0


def test_rip_reports_progress(fake_disc, tmp_path):
    events = []
    ripper.rip_disc(fake_disc, str(tmp_path / "out"), 1, progress=events.append)

    copy_events = [e for e in events if e.phase == "copy"]
    assert copy_events, "expected at least one copy progress event"
    last = copy_events[-1]
    assert last.done == last.total == 4
    assert last.pct == 100.0


def test_rip_cancellation(fake_disc, tmp_path):
    with pytest.raises(Cancelled):
        ripper.rip_disc(fake_disc, str(tmp_path / "out"), 1, cancel=CancelNow())
