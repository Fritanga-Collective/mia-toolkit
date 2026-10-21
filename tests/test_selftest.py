"""The headless ``--selftest`` used to smoke-test installed builds (G15)."""

from __future__ import annotations

import importlib.util
import os

import pytest

from mia import __version__, selftest

LAUNCH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "packaging", "macos", "launch.py")


def _load_launch():
    spec = importlib.util.spec_from_file_location("mia_launch", LAUNCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_selftest_passes_and_writes_report(tmp_path, monkeypatch, capsys):
    report = tmp_path / "report.txt"
    monkeypatch.setenv(selftest.REPORT_ENV, str(report))
    assert selftest.run() == 0
    out = capsys.readouterr().out
    assert out.startswith("selftest OK")
    assert __version__ in out
    assert "DICOMDIR built with 2 images" in out
    assert report.read_text(encoding="utf-8").startswith("selftest OK")


def test_selftest_cleans_up_its_working_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(selftest.tempfile, "tempdir", str(tmp_path))
    assert selftest.run() == 0
    # (pydicom's FileSet may keep its own staging dir until garbage-collected;
    # only our named working folder must be gone.)
    assert not [p for p in tmp_path.iterdir() if p.name.startswith("mia-selftest-")]


def test_selftest_fails_when_archive_build_breaks(tmp_path, monkeypatch, capsys):
    from mia_core import dicomdir

    monkeypatch.setattr(dicomdir, "build_fileset", lambda *a, **k: None)
    report = tmp_path / "report.txt"
    monkeypatch.setenv(selftest.REPORT_ENV, str(report))
    assert selftest.run() == 1
    assert "selftest FAILED" in capsys.readouterr().out
    assert "no DICOM files" in report.read_text(encoding="utf-8")


def test_selftest_fails_when_an_extra_import_fails(capsys):
    def boom():
        raise ImportError("No module named 'tkinter'")

    assert selftest.run(extra_imports=boom) == 1
    assert "tkinter" in capsys.readouterr().out


@pytest.mark.parametrize("argv,expected", [
    (["mia", "--selftest"], True),
    (["mia", "--self-test"], True),
    (["mia"], False),
    (["mia", "--version"], False),
    (["--selftest"], False),  # argv[0] is the program, never a flag
])
def test_wants_selftest(argv, expected):
    assert selftest.wants_selftest(argv) is expected


def test_launch_dispatches_selftest_without_starting_gui(monkeypatch):
    launch = _load_launch()
    seen = {}

    def fake_run(extra_imports=None):
        seen["extra"] = extra_imports
        return 0

    monkeypatch.setattr(selftest, "run", fake_run)
    assert launch.main(["mia", "--self-test"]) == 0
    assert seen["extra"] is launch._gui_imports


def test_launch_version_flag(capsys):
    launch = _load_launch()
    assert launch.main(["mia", "--version"]) == 0
    assert capsys.readouterr().out.strip() == f"MIA Toolkit {__version__}"
