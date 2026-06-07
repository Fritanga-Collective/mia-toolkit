"""Reports & documents: find PDFs that ride on imported media, and wrap PDFs
as Encapsulated PDF DICOM instances so they join a study in the archive/PACS.

Local I/O only. The companion-folder copy (originals → ``Reports/`` on the USB)
is handled by the wizard delivery step (``_copy_reports`` via
``ripper.copy_with_retry``); this module provides discovery, study association,
and the PDF→DICOM encapsulation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from .common import is_dicom_file

# Encapsulated PDF Storage SOP Class (DICOM PS3.6).
ENCAPSULATED_PDF_SOP_CLASS = "1.2.840.10008.5.1.4.1.1.104.1"
# Series number for the document series we add (high, to sort after images).
DOC_SERIES_NUMBER = 901


@dataclass
class StudyRef:
    """A study a document can be attached to, plus a representative instance to
    copy patient/study identity from (so a PACS associates it correctly)."""

    study_uid: str
    label: str
    patient: str
    sample_path: str


def find_pdfs(root: str) -> List[str]:
    """All ``*.pdf`` under ``root`` (the staging dir excluded), sorted."""
    out: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "_documents"]
        for fn in filenames:
            if fn.lower().endswith(".pdf"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def _sample_instance(directory: str) -> Optional[str]:
    """First DICOM file at/under ``directory`` (to read identity from)."""
    for dirpath, _dirnames, filenames in os.walk(directory):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            if is_dicom_file(path):
                return path
    return None


def study_choices(inventory_result) -> List[StudyRef]:
    """Build the association list from an ``inventory.scan_directory`` result,
    most-recent study first."""
    refs: List[StudyRef] = []
    for uid, study in inventory_result.studies.items():
        sample = _sample_instance(study.get("source_path", "")) or ""
        date = study.get("study_date", "") or "????"
        desc = study.get("study_description", "") or study.get("modality", "")
        label = f"{date} · {desc}".strip(" ·")
        refs.append(StudyRef(uid, label, study.get("patient_name", ""), sample))
    refs.sort(key=lambda r: r.label, reverse=True)
    return refs


def study_for_path(pdf_path: str, raw_discs_dir: str) -> Optional[StudyRef]:
    """Default association for an auto-found PDF: the study sitting in the same
    disc folder as the PDF. Returns None if no DICOM is found alongside it."""
    raw = os.path.abspath(raw_discs_dir)
    disc_dir = os.path.dirname(os.path.abspath(pdf_path))
    # Walk up to the immediate child of raw_discs (the disc_NN_… folder).
    while os.path.dirname(disc_dir) != raw and disc_dir != raw \
            and os.path.dirname(disc_dir) not in ("", "/"):
        disc_dir = os.path.dirname(disc_dir)
    sample = _sample_instance(disc_dir)
    if not sample:
        return None
    ds = pydicom.dcmread(sample, stop_before_pixels=True, force=True)
    uid = str(getattr(ds, "StudyInstanceUID", "") or "")
    if not uid:
        return None
    date = str(getattr(ds, "StudyDate", "") or "????")
    desc = str(getattr(ds, "StudyDescription", "")
               or getattr(ds, "Modality", "") or "")
    return StudyRef(uid, f"{date} · {desc}".strip(" ·"),
                    str(getattr(ds, "PatientName", "") or ""), sample)


def _copy_tag(dst: Dataset, src: Dataset, name: str, default: str = "") -> None:
    setattr(dst, name, getattr(src, name, default) or default)


def encapsulate_pdf(pdf_path: str, study: StudyRef, dest_dir: str) -> str:
    """Wrap ``pdf_path`` as an Encapsulated PDF DICOM tied to ``study`` and
    write it under ``dest_dir``. Returns the written file path."""
    with open(pdf_path, "rb") as f:
        pdf = f.read()
    if len(pdf) % 2:                      # DICOM OB values must be even-length
        pdf += b"\x00"

    src = pydicom.dcmread(study.sample_path, stop_before_pixels=True,
                          force=True)
    sop_uid = generate_uid()

    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = ENCAPSULATED_PDF_SOP_CLASS
    meta.MediaStorageSOPInstanceUID = sop_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = Dataset()
    ds.file_meta = meta
    ds.SpecificCharacterSet = "ISO_IR 192"  # UTF-8 (names/titles)
    # Patient + Study identity from a real instance → correct PACS association.
    for tag in ("PatientName", "PatientID", "PatientBirthDate", "PatientSex",
                "StudyInstanceUID", "StudyDate", "StudyTime", "StudyID",
                "AccessionNumber"):
        _copy_tag(ds, src, tag)
    ds.SOPClassUID = ENCAPSULATED_PDF_SOP_CLASS
    ds.SOPInstanceUID = sop_uid
    ds.SeriesInstanceUID = generate_uid()
    ds.SeriesNumber = DOC_SERIES_NUMBER
    ds.InstanceNumber = 1
    ds.Modality = "DOC"
    ds.ConversionType = "WSD"
    ds.BurnedInAnnotation = "NO"
    ds.DocumentTitle = os.path.basename(pdf_path)
    ds.MIMETypeOfEncapsulatedDocument = "application/pdf"
    ds.EncapsulatedDocument = pdf

    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    out = os.path.join(dest_dir, f"{base}_{sop_uid[-8:]}.dcm")
    # Transfer syntax is set in file_meta (Explicit VR LE); enforce a compliant
    # Part-10 file. (Avoids the deprecated is_little_endian/write_like_original.)
    ds.save_as(out, enforce_file_format=True)
    return out
