from mia.core.common import (
    Progress,
    format_bytes,
    format_duration,
    is_dicom_file,
    is_verbose,
)
from tests.helpers import make_dicom
from pydicom.uid import generate_uid


def test_verbose_on_by_default():
    # Verbose detail is captured by default (shown only when the user expands
    # "technical details"); the Help toggle turns it off.
    assert is_verbose() is True


def test_format_bytes():
    assert format_bytes(0) == "0.0 B"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(5 * 1024 ** 3) == "5.0 GB"


def test_format_duration():
    assert format_duration(45) == "45s"
    assert format_duration(90) == "1m 30s"
    assert format_duration(3661) == "1h 1m"


def test_progress_pct():
    assert Progress(0, 0).pct == 100.0          # avoid div-by-zero
    assert Progress(1, 4).pct == 25.0


def test_is_dicom_file_true_for_real_dicom(tmp_path):
    p = make_dicom(tmp_path / "x" / "IM1", study_uid=generate_uid(),
                   series_uid=generate_uid(), sop_uid=generate_uid())
    assert is_dicom_file(p) is True


def test_is_dicom_file_false_for_junk(tmp_path):
    junk = tmp_path / "foo.exe"
    junk.write_bytes(b"MZ" + b"\x00" * 200)
    assert is_dicom_file(str(junk)) is False
    assert is_dicom_file(str(tmp_path / "missing")) is False
