"""Tests for smart, incremental USB re-delivery (mia_core.delivery_target)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from mia_core import delivery_target as dt
from mia_core import diagnostics


# ----- marker round-trip ---------------------------------------------------

def test_marker_round_trip(tmp_path):
    folder = str(tmp_path / "CaseReview_DOE")
    os.makedirs(folder)
    dt.write_marker(folder, patient_name="DOE^JANE", patient_id="P001",
                    when=datetime(2026, 1, 1, tzinfo=timezone.utc))
    info = dt.read_marker(folder)
    assert info is not None
    assert info.patient_name == "DOE^JANE"
    assert info.patient_id == "P001"
    assert info.folder == folder
    assert not info.legacy
    # The raw file is valid JSON with a schema version.
    with open(os.path.join(folder, dt.MARKER_NAME), encoding="utf-8") as f:
        data = json.load(f)
    assert data["schema_version"] == dt.SCHEMA_VERSION


def test_marker_preserves_created_on_update(tmp_path):
    folder = str(tmp_path / "cr")
    os.makedirs(folder)
    dt.write_marker(folder, patient_name="A", patient_id="1",
                    when=datetime(2026, 1, 1, tzinfo=timezone.utc))
    first = dt.read_marker(folder).created
    dt.write_marker(folder, patient_name="A", patient_id="1",
                    when=datetime(2026, 2, 2, tzinfo=timezone.utc))
    info = dt.read_marker(folder)
    assert info.created == first              # created is stable
    assert info.updated != first             # updated advances


def test_read_marker_unknown_folder_is_none(tmp_path):
    folder = str(tmp_path / "RandomData")
    os.makedirs(folder)
    open(os.path.join(folder, "notes.txt"), "w").close()
    assert dt.read_marker(folder) is None


# ----- legacy detection ----------------------------------------------------

def _make_legacy(folder: str) -> None:
    os.makedirs(os.path.join(folder, "Archive"))
    open(os.path.join(folder, "Archive", "DICOMDIR"), "w").close()
    open(os.path.join(folder, "DELIVERY-LOG.txt"), "w").close()


def test_read_marker_legacy_folder(tmp_path):
    folder = str(tmp_path / "CaseReview_20200101")
    _make_legacy(folder)
    info = dt.read_marker(folder)
    assert info is not None
    assert info.legacy
    # No readable DICOMDIR content here, so patient stays unknown.
    assert info.patient_name is None


# ----- find_deliveries -----------------------------------------------------

def test_find_deliveries_marker_and_legacy(tmp_path):
    usb = str(tmp_path)
    marked = os.path.join(usb, "CaseReview_DOE")
    os.makedirs(marked)
    dt.write_marker(marked, patient_name="DOE", patient_id="P1")
    _make_legacy(os.path.join(usb, "CaseReview_old"))
    # A non-MIA folder is ignored.
    os.makedirs(os.path.join(usb, "Vacation Photos"))

    found = dt.find_deliveries(usb)
    folders = {os.path.basename(d.folder) for d in found}
    assert folders == {"CaseReview_DOE", "CaseReview_old"}


# ----- choose_target -------------------------------------------------------

def test_choose_target_new_when_empty(tmp_path):
    dec = dt.choose_target(str(tmp_path), ("DOE^JANE", "P001"))
    assert dec.action == dt.NEW
    assert dec.folder.endswith("CaseReview_DOE_JANE")


def test_choose_target_update_same_patient(tmp_path):
    folder = os.path.join(str(tmp_path), "CaseReview_DOE")
    os.makedirs(folder)
    dt.write_marker(folder, patient_name="DOE^JANE", patient_id="P001")
    dec = dt.choose_target(str(tmp_path), ("DOE^JANE", "P001"))
    assert dec.action == dt.UPDATE
    assert dec.folder == folder


def test_choose_target_update_matches_on_id(tmp_path):
    folder = os.path.join(str(tmp_path), "CaseReview_X")
    os.makedirs(folder)
    dt.write_marker(folder, patient_name="OLD NAME", patient_id="P001")
    # Same ID, different recorded name → still the same patient.
    dec = dt.choose_target(str(tmp_path), ("NEW NAME", "P001"))
    assert dec.action == dt.UPDATE


def test_choose_target_ask_different_patient(tmp_path):
    folder = os.path.join(str(tmp_path), "CaseReview_SMITH")
    os.makedirs(folder)
    dt.write_marker(folder, patient_name="SMITH^JOHN", patient_id="P999")
    dec = dt.choose_target(str(tmp_path), ("DOE^JANE", "P001"))
    assert dec.action == dt.ASK
    assert dec.existing and dec.existing[0].patient_name == "SMITH^JOHN"


def test_choose_target_no_patient_yields_new_generic(tmp_path):
    dec = dt.choose_target(str(tmp_path), (None, None))
    assert dec.action == dt.NEW
    assert os.path.basename(dec.folder) == dt.GENERIC_FOLDER


def test_choose_target_new_avoids_unrelated_nonempty_folder(tmp_path):
    # A pre-existing, non-MIA folder with the stable name (no marker, no legacy
    # structure) must not be proposed as the fresh destination.
    clash = os.path.join(str(tmp_path), "CaseReview_DOE_JANE")
    os.makedirs(clash)
    with open(os.path.join(clash, "someone-elses.txt"), "w") as f:
        f.write("not ours")
    dec = dt.choose_target(str(tmp_path), ("DOE^JANE", "P001"))
    assert dec.action == dt.NEW
    assert dec.folder != clash
    assert os.path.basename(dec.folder) == "CaseReview_DOE_JANE_2"


def test_choose_target_new_reuses_empty_folder(tmp_path):
    # An existing but *empty* folder of the stable name is safe to reuse.
    empty = os.path.join(str(tmp_path), "CaseReview_DOE_JANE")
    os.makedirs(empty)
    dec = dt.choose_target(str(tmp_path), ("DOE^JANE", "P001"))
    assert dec.action == dt.NEW
    assert dec.folder == empty


# ----- archive_identity ----------------------------------------------------

def _studies(*entries):
    return {f"uid{i}": {"patient_name": n, "patient_id": p}
            for i, (n, p) in enumerate(entries)}


def test_identity_dominant_single_patient():
    studies = _studies(("DOE^JANE", "P001"), ("DOE^JANE", "P001"))
    assert dt.archive_identity(studies) == ("DOE^JANE", "P001")


def test_identity_mismatch_yields_none():
    studies = _studies(("DOE^JANE", "P001"), ("SMITH^JOHN", "P002"))
    assert dt.archive_identity(studies) == (None, None)


def test_identity_unknown_placeholder_is_empty():
    studies = _studies(("UNKNOWN", "UNKNOWN"))
    assert dt.archive_identity(studies) == (None, None)


def test_identity_name_only_when_id_missing():
    studies = _studies(("DOE^JANE", ""), ("DOE^JANE", ""))
    assert dt.archive_identity(studies) == ("DOE^JANE", None)


# ----- find_orphans --------------------------------------------------------

def test_find_orphans(tmp_path):
    src = tmp_path / "src"            # freshly built archive (source)
    dest = tmp_path / "dest"         # CaseReview folder on the USB
    (src).mkdir()
    (dest / "Archive").mkdir(parents=True)

    # Source has a.dcm and b.dcm.
    (src / "a.dcm").write_text("a")
    (src / "b.dcm").write_text("b")
    # Dest already has a.dcm (kept), b.dcm (kept), plus stale.dcm (orphan).
    (dest / "Archive" / "a.dcm").write_text("a")
    (dest / "Archive" / "b.dcm").write_text("b")
    (dest / "Archive" / "stale.dcm").write_text("old")

    orphans = dt.find_orphans(str(src), str(dest))
    assert orphans == [os.path.join("Archive", "stale.dcm")]


def test_remove_orphans_prunes_empty_dirs(tmp_path):
    dest = tmp_path / "dest"
    nested = dest / "Archive" / "SUB"
    nested.mkdir(parents=True)
    (nested / "stale.dcm").write_text("x")
    rel = os.path.join("Archive", "SUB", "stale.dcm")

    removed = dt.remove_orphans(str(dest), [rel])
    assert removed == 1
    assert not (nested).exists()              # empty dir pruned
    assert dest.exists()                      # but not above dest


# ----- redaction → generic folder name -------------------------------------

def test_safe_folder_name_patient():
    assert dt.safe_folder_name("DOE^JANE") == "CaseReview_DOE_JANE"


def test_safe_folder_name_none_is_generic():
    assert dt.safe_folder_name(None) == dt.GENERIC_FOLDER


def test_safe_folder_name_redacted_is_generic(monkeypatch):
    monkeypatch.setattr(diagnostics, "_REDACT", True)
    assert diagnostics.redacting()
    assert dt.safe_folder_name("DOE^JANE") == dt.GENERIC_FOLDER
