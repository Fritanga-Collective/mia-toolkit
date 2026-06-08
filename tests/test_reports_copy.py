"""Companion-report copy: a symlinked source document must land as real file
contents on the USB, not a broken link (copy_with_retry uses
follow_symlinks=False as a disc-rip security guard). GUI-module import is
guarded so headless CI without Tk skips cleanly."""

from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("tkinter")
from mia.gui.wizard.steps import _copy_reports  # noqa: E402


class _Result:
    def __init__(self):
        self.failed = 0
        self.failures = []


def _symlink_or_skip(target, link):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError) as e:
        pytest.skip(f"symlinks unavailable here: {e}")


def test_copy_reports_resolves_symlink(tmp_path):
    real = tmp_path / "real_report.pdf"
    real.write_bytes(b"%PDF-1.4 real report body\n")
    link = tmp_path / "report.pdf"
    _symlink_or_skip(str(real), str(link))

    dest = tmp_path / "USB"
    copied = _copy_reports([{"path": str(link), "embed_study": None}], str(dest))

    out = dest / "Reports" / "report.pdf"
    assert copied == 1
    assert out.exists() and not out.is_symlink()         # a real file…
    assert out.read_bytes().startswith(b"%PDF-1.4 real report body")  # …with contents


def test_copy_reports_broken_symlink_counts_failure(tmp_path):
    link = tmp_path / "report.pdf"
    _symlink_or_skip(str(tmp_path / "missing.pdf"), str(link))
    result = _Result()
    _copy_reports([{"path": str(link), "embed_study": None}],
                  str(tmp_path / "USB"), result)
    assert result.failed == 1


def test_copy_reports_plain_file(tmp_path):
    f = tmp_path / "labs.pdf"
    f.write_bytes(b"%PDF-1.4 labs\n")
    dest = tmp_path / "USB"
    assert _copy_reports([{"path": str(f), "embed_study": None}], str(dest)) == 1
    assert (dest / "Reports" / "labs.pdf").read_bytes().startswith(b"%PDF-1.4 labs")
