"""Shared test fixtures: synthesize small, valid DICOM files on disk.

We generate fixtures with pydicom rather than depending on the sample
``raw_discs/`` so tests are fast, deterministic, and self-contained.
"""

from __future__ import annotations

import os
from typing import Iterable

import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

MR_STORAGE = "1.2.840.10008.5.1.4.1.1.4"
CT_STORAGE = "1.2.840.10008.5.1.4.1.1.2"


def make_dicom(
    path,
    *,
    study_uid: str,
    series_uid: str,
    sop_uid: str,
    sop_class: str = MR_STORAGE,
    modality: str = "MR",
    series_desc: str = "Ax T1",
    series_number: int = 1,
    instance_number: int = 1,
    patient_id: str = "P001",
    patient_name: str = "DOE^JANE",
    patient_birth: str = "19600101",
    study_date: str = "20200115",
    study_time: str = "120000",
    study_desc: str = "BRAIN",
    institution: str = "Hospital A",
    omit: Iterable[str] = (),
) -> str:
    """Write one minimal but file-format-compliant DICOM file. Returns its path."""
    omit = set(omit)
    ds = Dataset()

    def setif(name, value):
        if name not in omit:
            setattr(ds, name, value)

    # UIDs are always needed for FileSet to organize records.
    ds.SOPClassUID = sop_class
    ds.SOPInstanceUID = sop_uid
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = series_uid

    setif("PatientID", patient_id)
    setif("PatientName", patient_name)
    setif("PatientBirthDate", patient_birth)
    setif("Modality", modality)
    setif("SeriesDescription", series_desc)
    setif("SeriesNumber", series_number)
    setif("InstanceNumber", instance_number)
    setif("StudyDate", study_date)
    setif("StudyTime", study_time)
    setif("StudyDescription", study_desc)
    setif("InstitutionName", institution)
    setif("StudyID", "1")

    fm = FileMetaDataset()
    fm.MediaStorageSOPClassUID = sop_class
    fm.MediaStorageSOPInstanceUID = sop_uid
    fm.TransferSyntaxUID = ExplicitVRLittleEndian
    fm.ImplementationClassUID = generate_uid()
    ds.file_meta = fm

    path = str(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ds.save_as(path, enforce_file_format=True)
    return path


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


class CancelNow:
    """A cancel token that is already set (simulates an immediate cancel)."""

    def is_set(self) -> bool:
        return True
