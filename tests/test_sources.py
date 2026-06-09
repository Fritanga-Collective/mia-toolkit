"""Tests for source identity / already-imported detection (mia.core.sources)
and RipSessionController's session-vs-busy callback split."""

from __future__ import annotations

import os

import pytest
from pydicom.uid import generate_uid

from mia.core import ripper, sources
from tests.helpers import make_dicom


def _disc(root, name, study_uid, *, manifest=True):
    d = root / name
    make_dicom(str(d / "IM1"), study_uid=study_uid, series_uid=generate_uid(),
               sop_uid=generate_uid())
    make_dicom(str(d / "IM2"), study_uid=study_uid, series_uid=generate_uid(),
               sop_uid=generate_uid())
    if manifest:
        (d / "_manifest.txt").write_text("CD Rip Manifest\n", encoding="utf-8")
    return d


# ---- sampling / recording / dedup ------------------------------------------

def test_sample_study_uids(tmp_path):
    s = generate_uid()
    d = _disc(tmp_path, "disc_01_x", s)
    assert sources.sample_study_uids(str(d)) == {s}


def test_record_and_read_back(tmp_path):
    raw = tmp_path / "raw_discs"
    s = generate_uid()
    d = _disc(raw, "disc_01_x", s)
    rec = sources.record_study_uids(str(d))
    assert rec == {s}
    # Recorded line is read back without re-sampling.
    assert sources.project_study_uids(str(raw)) == {s}
    assert "Study UIDs" in (d / "_manifest.txt").read_text(encoding="utf-8")


def test_project_uids_fallback_for_manifestless_disc(tmp_path):
    raw = tmp_path / "raw_discs"
    s1, s2 = generate_uid(), generate_uid()
    d1 = _disc(raw, "disc_01_a", s1)
    sources.record_study_uids(str(d1))                 # manifest has the line
    _disc(raw, "disc_02_b", s2, manifest=False)        # no manifest at all
    assert sources.project_study_uids(str(raw)) == {s1, s2}  # live fallback


def test_looks_already_imported(tmp_path):
    raw = tmp_path / "raw_discs"
    s = generate_uid()
    d = _disc(raw, "disc_01_x", s)
    sources.record_study_uids(str(d))
    # A USB that is a copy of the same study → already imported.
    usb = tmp_path / "usb"
    make_dicom(str(usb / "A"), study_uid=s, series_uid=generate_uid(),
               sop_uid=generate_uid())
    assert sources.looks_already_imported(str(usb), str(raw)) is True
    # A different patient's study → not already imported.
    other = tmp_path / "other"
    make_dicom(str(other / "B"), study_uid=generate_uid(),
               series_uid=generate_uid(), sop_uid=generate_uid())
    assert sources.looks_already_imported(str(other), str(raw)) is False


def test_looks_already_imported_empty_source(tmp_path):
    # A source with no DICOM never counts as "already imported".
    raw = tmp_path / "raw_discs"
    raw.mkdir()
    junk = tmp_path / "junk"
    junk.mkdir()
    (junk / "readme.txt").write_text("not dicom")
    assert sources.looks_already_imported(str(junk), str(raw)) is False


# ---- is_optical ------------------------------------------------------------

def test_is_optical_unknown_is_false(tmp_path):
    assert ripper.is_optical(str(tmp_path)) is False  # not optical → prompt


def test_is_optical_linux_fs_type(monkeypatch, tmp_path):
    monkeypatch.setattr(ripper.platform, "system", lambda: "Linux")
    mounts = tmp_path / "mounts"
    mounts.write_text("/dev/sr0 /media/CD iso9660 ro 0 0\n"
                      "/dev/sdb1 /media/USB exfat rw 0 0\n")
    real_open = open

    def fake_open(path, *a, **k):
        return real_open(mounts if path == "/proc/mounts" else path, *a, **k)

    monkeypatch.setattr("builtins.open", fake_open)
    assert ripper.is_optical("/media/CD") is True
    assert ripper.is_optical("/media/USB") is False


# ---- controller session-vs-busy callbacks ---------------------------------

class _FakeRoot:
    def after(self, _ms, _cb):
        return None  # never auto-fire the poll in the test


class _FakePanel:
    def __getattr__(self, _name):
        return lambda *a, **k: None


def test_controller_session_and_busy_callbacks(tmp_path):
    from mia.gui.rip_session import RipSessionController
    sess, busy = [], []
    c = RipSessionController(
        _FakeRoot(), _FakePanel(), get_dest=lambda: str(tmp_path),
        on_state_changed=busy.append, on_session_changed=sess.append)
    assert c.start() is True
    # Starting opens the session but is NOT busy (it idle-polls) — so Next must
    # stay usable in the wizard.
    assert sess == [True]
    assert busy == []
    c.stop()                       # idle stop → _end
    assert sess[-1] is False
    assert busy[-1] is False
