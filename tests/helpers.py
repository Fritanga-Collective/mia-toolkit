"""Shared test helpers (importable from tests and from conftest).

These live in a normal module rather than ``conftest.py`` so test files can
``from tests.helpers import ...`` regardless of how pytest is invoked (the
``pythonpath = ["."]`` setting in pyproject puts the repo root on sys.path).
"""

from __future__ import annotations

import os
from typing import Iterable

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


class CancelNow:
    """A cancel token that is already set (simulates an immediate cancel)."""

    def is_set(self) -> bool:
        return True
