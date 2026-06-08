"""Tests for reports/documents: PDF discovery, study association, and wrapping
a PDF as an Encapsulated PDF DICOM that rides in the DICOMDIR."""

from __future__ import annotations

import os

import pydicom
from pydicom.uid import generate_uid

from mia.core import dicomdir, documents, inventory
from tests.helpers import make_dicom


def _make_disc(tmp_path, name="disc_01_2020_X", patient_id="P1"):
    disc = tmp_path / "raw_discs" / name
    suid = generate_uid()
    make_dicom(str(disc / "IM1"), study_uid=suid, series_uid=generate_uid(),
               sop_uid=generate_uid(), patient_id=patient_id,
               patient_name="DOE^JANE", study_desc="BRAIN")
    return disc, suid


def test_find_pdfs(tmp_path):
    disc, _ = _make_disc(tmp_path)
    (disc / "report.pdf").write_bytes(b"%PDF-1.4 report\n")
    (disc / "labs.PDF").write_bytes(b"%PDF-1.4 labs\n")
    (disc / "viewer.exe").write_bytes(b"MZ junk")
    found = documents.find_pdfs(str(tmp_path / "raw_discs"))
    assert {os.path.basename(p) for p in found} == {"report.pdf", "labs.PDF"}


def test_find_pdfs_excludes_only_named_staging(tmp_path):
    raw = tmp_path / "raw_discs"
    staged = raw / "_documents"
    staged.mkdir(parents=True)
    (staged / "x.pdf").write_bytes(b"%PDF-1.4\n")
    # The staging dir is excluded by path…
    assert documents.find_pdfs(str(raw), exclude_dir=str(staged)) == []
    # …but a disc that happens to contain its own _documents folder is NOT.
    disc_docs = raw / "disc_01" / "_documents"
    disc_docs.mkdir(parents=True)
    (disc_docs / "report.pdf").write_bytes(b"%PDF-1.4\n")
    found = documents.find_pdfs(str(raw), exclude_dir=str(staged))
    assert [os.path.basename(p) for p in found] == ["report.pdf"]


def test_study_for_path_outside_raw_returns_none(tmp_path):
    # A PDF outside raw_discs must not trigger an arbitrary-tree walk / loop.
    pdf = tmp_path / "elsewhere" / "x.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"%PDF-1.4\n")
    assert documents.study_for_path(str(pdf), str(tmp_path / "raw_discs")) is None


def test_study_for_path_matches_same_disc(tmp_path):
    disc, suid = _make_disc(tmp_path)
    pdf = disc / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 report\n")
    ref = documents.study_for_path(str(pdf), str(tmp_path / "raw_discs"))
    assert ref is not None and ref.study_uid == suid


def test_encapsulate_pdf_roundtrip(tmp_path):
    disc, suid = _make_disc(tmp_path)
    pdf = disc / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 odd-length-body")  # odd length → must be padded
    ref = documents.study_for_path(str(pdf), str(tmp_path / "raw_discs"))
    out = documents.encapsulate_pdf(str(pdf), ref, str(tmp_path / "staged"))

    ds = pydicom.dcmread(out)
    assert ds.SOPClassUID == documents.ENCAPSULATED_PDF_SOP_CLASS
    assert ds.Modality == "DOC"
    assert str(ds.StudyInstanceUID) == suid
    assert ds.MIMETypeOfEncapsulatedDocument == "application/pdf"
    body = bytes(ds.EncapsulatedDocument)
    assert body.startswith(b"%PDF-1.4 odd-length-body")
    assert len(body) % 2 == 0  # even-length OB


def test_encapsulated_doc_rides_in_dicomdir(tmp_path):
    disc, suid = _make_disc(tmp_path)
    pdf = disc / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 report\n")
    ref = documents.study_for_path(str(pdf), str(tmp_path / "raw_discs"))
    # Encapsulate into the staging dir under raw_discs (as the wizard does).
    staged = tmp_path / "raw_discs" / "_documents"
    documents.encapsulate_pdf(str(pdf), ref, str(staged))

    res = dicomdir.build_fileset(str(tmp_path / "raw_discs"),
                                 str(tmp_path / "Archive"))
    assert res.added == 2          # the image + the encapsulated doc
    assert res.studies == 1        # joined the same study
    assert os.path.exists(tmp_path / "Archive" / "DICOMDIR")


def test_raw_pdf_excluded_from_archive_and_inventory(tmp_path):
    # A raw PDF sitting in raw_discs (not encapsulated) must NOT appear in the
    # DICOMDIR or the inventory — only the encapsulated copy rides.
    disc, _ = _make_disc(tmp_path)
    (disc / "loose.pdf").write_bytes(b"%PDF-1.4 loose\n")
    res = dicomdir.build_fileset(str(tmp_path / "raw_discs"),
                                 str(tmp_path / "Archive"))
    assert res.added == 1  # only the DICOM image
    inv = inventory.scan_directory(str(tmp_path / "raw_discs"))
    assert inv.study_count == 1


def test_study_choices_from_inventory(tmp_path):
    _make_disc(tmp_path)
    inv = inventory.scan_directory(str(tmp_path / "raw_discs"))
    refs = documents.study_choices(inv)
    assert len(refs) == 1
    assert refs[0].sample_path and os.path.exists(refs[0].sample_path)
