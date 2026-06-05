"""Tests for mia.core.importer — folder/USB and ZIP import sources."""

from __future__ import annotations

import os
import threading
import zipfile

import pytest
from pydicom.uid import generate_uid

from mia.core import importer
from mia.core.common import Cancelled

from tests.helpers import make_dicom


def _make_source(root, n_dicom: int = 3, junk: bool = True):
    """A folder shaped like a hospital USB: DICOM + viewer junk."""
    study = generate_uid()
    series = generate_uid()
    dicom_dir = os.path.join(root, "DICOM")
    os.makedirs(dicom_dir, exist_ok=True)
    for i in range(n_dicom):
        make_dicom(os.path.join(dicom_dir, f"IM{i:04d}"),
                   study_uid=study, series_uid=series,
                   sop_uid=generate_uid(), instance_number=i + 1)
    if junk:
        with open(os.path.join(root, "VIEWER.exe"), "wb") as f:
            f.write(b"MZ fake viewer")
        with open(os.path.join(root, "report.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 fake report")
    return root


# ----- scan_folder ---------------------------------------------------------

def test_scan_folder_counts(tmp_path):
    src = _make_source(str(tmp_path / "HOSPITAL_USB"), n_dicom=3)
    scan = importer.scan_folder(src)
    assert scan.files == 5            # 3 DICOM + 2 junk
    assert scan.dicom_files == 3
    assert scan.bytes > 0
    assert not scan.capped


def test_scan_folder_cap(tmp_path):
    src = _make_source(str(tmp_path / "SRC"), n_dicom=4)
    scan = importer.scan_folder(src, cap_files=2)
    assert scan.capped
    assert scan.files == 2


def test_scan_zip_counts(tmp_path):
    src = _make_source(str(tmp_path / "SRC"), n_dicom=2)
    zip_path = str(tmp_path / "studies.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for dirpath, _dn, fns in os.walk(src):
            for fn in fns:
                p = os.path.join(dirpath, fn)
                zf.write(p, os.path.relpath(p, src))
    scan = importer.scan_zip(zip_path)
    assert scan.files == 4
    assert scan.dicom_files == -1     # checked during import, not pre-scan
    assert scan.bytes > 0


# ----- import_folder -------------------------------------------------------

def test_import_folder_basic(tmp_path):
    src = _make_source(str(tmp_path / "HOSPITAL_USB"), n_dicom=3)
    dest = str(tmp_path / "proj" / "raw_discs")
    res = importer.import_folder(src, dest, 1)

    base = os.path.basename(res.disc_dir)
    assert base.startswith("disc_01_")
    assert base.endswith("HOSPITAL_USB")
    assert res.copied == 5            # full-fidelity: junk copied too
    assert res.failed == 0
    assert res.dicom_files == 3
    assert res.source_type == "folder"
    assert os.path.exists(os.path.join(res.disc_dir, "VIEWER.exe"))
    with open(res.manifest_path) as f:
        manifest = f.read()
    assert "Source type   : folder" in manifest
    assert "DICOM files   : 3" in manifest


def test_import_folder_is_resumable(tmp_path):
    src = _make_source(str(tmp_path / "USB"), n_dicom=2)
    dest = str(tmp_path / "raw")
    first = importer.import_folder(src, dest, 1)
    # Re-import into the same numbered folder: everything skips.
    second = importer.import_folder(src, dest, 1)
    assert second.disc_dir == first.disc_dir
    assert second.copied == 0
    assert second.skipped == first.total_files


def test_import_folder_cancel(tmp_path):
    src = _make_source(str(tmp_path / "USB"), n_dicom=2)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        importer.import_folder(src, str(tmp_path / "raw"), 1, cancel=cancel)


def test_import_folder_rejects_files(tmp_path):
    f = tmp_path / "not_a_dir.txt"
    f.write_text("x")
    with pytest.raises(ValueError):
        importer.import_folder(str(f), str(tmp_path / "raw"), 1)


def test_imported_folder_visible_to_project(tmp_path):
    from mia.gui.project import Project
    project = Project(root=str(tmp_path / "MedicalArchive"))
    project.ensure_dirs()
    src = _make_source(str(tmp_path / "USB"), n_dicom=1)
    importer.import_folder(src, project.raw_discs_dir, 1)
    assert project.disc_count() == 1
    assert project.has_discs()


# ----- import_zip ----------------------------------------------------------

def _zip_of(tmp_path, name="portal_download.zip", *, n_dicom=2,
            nested=False, junk=True):
    src = _make_source(str(tmp_path / "_zip_src"), n_dicom=n_dicom, junk=junk)
    if nested:
        inner_src = _make_source(str(tmp_path / "_inner"), n_dicom=1,
                                 junk=False)
        inner_zip = str(tmp_path / "_zip_src" / "study2.zip")
        with zipfile.ZipFile(inner_zip, "w") as zf:
            for dirpath, _dn, fns in os.walk(inner_src):
                for fn in fns:
                    p = os.path.join(dirpath, fn)
                    zf.write(p, os.path.relpath(p, inner_src))
    zip_path = str(tmp_path / name)
    with zipfile.ZipFile(zip_path, "w") as zf:
        for dirpath, _dn, fns in os.walk(src):
            for fn in fns:
                p = os.path.join(dirpath, fn)
                zf.write(p, os.path.relpath(p, src))
    return zip_path


def test_import_zip_basic(tmp_path):
    zip_path = _zip_of(tmp_path, n_dicom=2)
    dest = str(tmp_path / "raw")
    res = importer.import_zip(zip_path, dest, 1)
    assert os.path.basename(res.disc_dir).endswith("portal_download")
    assert res.dicom_files == 2
    assert res.failed == 0
    assert res.source_type == "zip"
    with open(res.manifest_path) as f:
        manifest = f.read()
    assert "Source type   : zip" in manifest
    assert "portal_download.zip" in manifest


def test_import_zip_nested(tmp_path):
    zip_path = _zip_of(tmp_path, n_dicom=2, nested=True)
    res = importer.import_zip(zip_path, str(tmp_path / "raw"), 1)
    assert res.dicom_files == 3       # 2 outer + 1 from the nested zip
    # The nested container itself is not copied — only its contents.
    leftover_zips = [fn for _dp, _dn, fns in os.walk(res.disc_dir)
                     for fn in fns if fn.endswith(".zip")]
    assert leftover_zips == []


def test_import_zip_rejects_zip_slip(tmp_path):
    zip_path = str(tmp_path / "evil.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.txt", "escape attempt")
    with pytest.raises(ValueError, match="Unsafe path"):
        importer.import_zip(zip_path, str(tmp_path / "raw"), 1)
    assert not (tmp_path / "evil.txt").exists()


def test_import_zip_rejects_non_zip(tmp_path):
    fake = tmp_path / "fake.zip"
    fake.write_bytes(b"this is not a zip")
    with pytest.raises(ValueError, match="Not a ZIP"):
        importer.import_zip(str(fake), str(tmp_path / "raw"), 1)


def test_import_zip_zero_dicom_reported(tmp_path):
    src_dir = tmp_path / "_junk"
    src_dir.mkdir()
    (src_dir / "notes.txt").write_text("no images here")
    zip_path = str(tmp_path / "junk.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(str(src_dir / "notes.txt"), "notes.txt")
    res = importer.import_zip(zip_path, str(tmp_path / "raw"), 1)
    assert res.dicom_files == 0
