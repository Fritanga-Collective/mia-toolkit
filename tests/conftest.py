"""Shared test fixtures: synthesize small, valid DICOM files on disk.

We generate fixtures with pydicom rather than depending on the sample
``raw_discs/`` so tests are fast, deterministic, and self-contained. The
non-fixture helpers live in ``tests/helpers.py`` so they import cleanly under
any pytest invocation.
"""

from __future__ import annotations

import pytest
from pydicom.uid import generate_uid

from tests.helpers import CT_STORAGE, make_dicom


@pytest.fixture
def dataset_dir(tmp_path):
    """A realistic tree: two studies (different patients), a cross-disc duplicate,
    a tag-incomplete file, plus non-DICOM junk that must be skipped.

    Returns (root_path, expected) where expected carries the counts tests assert.
    """
    root = tmp_path / "raw_discs"

    s1 = generate_uid()   # study 1 (MR, patient P001)
    s2 = generate_uid()   # study 2 (CT, patient P002)
    se1, se2, se3 = generate_uid(), generate_uid(), generate_uid()
    se4 = generate_uid()

    # Study 1 / Series 1: two T1 instances
    dup_sop = generate_uid()
    make_dicom(root / "disc_01" / "IM0001", study_uid=s1, series_uid=se1,
               sop_uid=dup_sop, series_desc="Ax T1", series_number=1,
               instance_number=1)
    make_dicom(root / "disc_01" / "IM0002", study_uid=s1, series_uid=se1,
               sop_uid=generate_uid(), series_desc="Ax T1", series_number=1,
               instance_number=2)
    # Study 1 / Series 2: post-contrast (Spanish-ish label)
    make_dicom(root / "disc_01" / "IM0003", study_uid=s1, series_uid=se2,
               sop_uid=generate_uid(), series_desc="T1 POST GADOLINIO",
               series_number=2)
    # Study 1 / Series 3: FLAIR
    make_dicom(root / "disc_01" / "IM0004", study_uid=s1, series_uid=se3,
               sop_uid=generate_uid(), series_desc="Ax FLAIR", series_number=3)

    # Study 2 (CT, different patient): one CTA series
    make_dicom(root / "disc_02" / "IM0001", study_uid=s2, series_uid=se4,
               sop_uid=generate_uid(), sop_class=CT_STORAGE, modality="CT",
               series_desc="CTA HEAD", series_number=1, patient_id="P002",
               patient_name="DOE^JOHN", study_date="20210320",
               institution="Hospital B")

    # A cross-disc DUPLICATE of study1/series1/IM0001 (same SOPInstanceUID)
    make_dicom(root / "disc_03" / "IM0001", study_uid=s1, series_uid=se1,
               sop_uid=dup_sop, series_desc="Ax T1", series_number=1,
               instance_number=1)

    # A tag-incomplete file (missing Modality, StudyID, InstanceNumber) that
    # the DICOMDIR builder must auto-repair rather than reject.
    make_dicom(root / "disc_03" / "IM0009", study_uid=s1, series_uid=se1,
               sop_uid=generate_uid(), series_desc="Ax T1", series_number=1,
               omit=("Modality", "StudyID", "InstanceNumber"))

    # Non-DICOM junk that must be skipped.
    (root / "disc_01" / "AUTORUN.EXE").write_bytes(b"MZ\x00\x00not a dicom")
    (root / "disc_01" / "INDEX.HTM").write_text("<html></html>")
    (root / "disc_01" / "README.TXT").write_text("viewer instructions")
    (root / "disc_01" / "DICOMDIR").write_bytes(b"\x00" * 132)  # not magic at 128

    expected = {
        "unique_instances": 6,   # 7 written, 1 is a duplicate SOPInstanceUID
        "duplicates": 1,
        "studies": 2,
        "patient_ids": {"P001", "P002"},
    }
    return str(root), expected


@pytest.fixture
def fake_disc(tmp_path):
    """A plain folder of files (no DICOM needed) to exercise the ripper's copy."""
    src = tmp_path / "MEDICAL_CD"
    (src / "DICOM" / "ST0001").mkdir(parents=True)
    (src / "DICOM" / "ST0001" / "IM0001").write_bytes(b"a" * 2048)
    (src / "DICOM" / "ST0001" / "IM0002").write_bytes(b"b" * 4096)
    (src / "VIEWER").mkdir()
    (src / "VIEWER" / "run.exe").write_bytes(b"MZ" + b"\x00" * 100)
    (src / "README.TXT").write_text("hi")
    # A metadata dir the ripper must skip.
    (src / ".Spotlight-V100").mkdir()
    (src / ".Spotlight-V100" / "junk").write_bytes(b"x" * 10)
    return str(src)
