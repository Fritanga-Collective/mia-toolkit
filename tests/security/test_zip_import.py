"""Adversarial regression tests for the ZIP import path (mia_core.importer).

Each test pins a defense the 2026-06-07 security audit either confirmed or
added. Malicious archives are synthesized in tmp_path — none are committed as
binaries. See docs/SECURITY-AUDIT.md for the finding each test corresponds to.
"""

from __future__ import annotations

import os
import zipfile

import pytest

from mia_core import importer
from mia_core.importer import _ExtractBudget, _safe_extract, import_zip


def _zip(path, members):
    """members: list of (arcname, bytes). Returns the zip path."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, data in members:
            zf.writestr(arcname, data)
    return str(path)


# ---- zip-slip (defense confirmed by the audit; locked here) ----------------

@pytest.mark.parametrize("evil", [
    "../escape.txt",
    "a/../../escape.txt",
    "/abs/escape.txt",
])
def test_safe_extract_rejects_traversal(tmp_path, evil):
    src = _zip(tmp_path / "evil.zip", [(evil, b"x")])
    dest = tmp_path / "out"
    dest.mkdir()
    with zipfile.ZipFile(src) as zf:
        with pytest.raises(ValueError):
            _safe_extract(zf, str(dest), budget=_ExtractBudget(),
                          progress=None, cancel=None)
    # Nothing landed outside dest.
    assert not (tmp_path / "escape.txt").exists()


def test_import_zip_rejects_traversal(tmp_path):
    src = _zip(tmp_path / "evil.zip", [("../pwned.txt", b"x"), ("ok.txt", b"y")])
    with pytest.raises(ValueError):
        import_zip(src, str(tmp_path / "proj"), 1)
    assert not (tmp_path / "pwned.txt").exists()


# ---- A3/A4: decompression-bomb caps ----------------------------------------

def test_single_member_bomb_refused(tmp_path, monkeypatch):
    # Tiny compressed, large declared/expanded — must be refused, not written.
    monkeypatch.setattr(importer, "MAX_TOTAL_UNCOMPRESSED", 1_000_000)
    src = _zip(tmp_path / "bomb.zip", [("big.bin", b"\0" * 5_000_000)])
    with pytest.raises(ValueError, match="decompression bomb"):
        import_zip(src, str(tmp_path / "proj"), 1)


def test_nested_bomb_shares_budget(tmp_path, monkeypatch):
    # An inner zip whose expansion would blow the cumulative budget.
    monkeypatch.setattr(importer, "MAX_TOTAL_UNCOMPRESSED", 1_000_000)
    inner = _zip(tmp_path / "inner.zip", [("big.bin", b"\0" * 5_000_000)])
    with open(inner, "rb") as f:
        inner_bytes = f.read()
    outer = _zip(tmp_path / "outer.zip", [("inner.zip", inner_bytes)])
    with pytest.raises(ValueError, match="decompression bomb"):
        import_zip(outer, str(tmp_path / "proj"), 1)


def test_budget_charges_cumulatively():
    budget = _ExtractBudget(limit=100)
    budget.charge(60)
    with pytest.raises(ValueError):
        budget.charge(60)  # 120 > 100


# ---- A9: over-long member name -> clean error, not raw OSError --------------

def test_long_member_name_clean_error(tmp_path):
    src = _zip(tmp_path / "long.zip", [("B" * 300 + ".txt", b"x")])
    with pytest.raises(ValueError, match="too long"):
        import_zip(src, str(tmp_path / "proj"), 1)


# ---- A10: "*.zip_contents" collision must not crash ------------------------

def test_zip_contents_name_collision(tmp_path):
    # "inner.zip" expands into a dir named "inner_contents" (the ".zip" suffix
    # is dropped). Carry a regular file with exactly that name next to it so
    # the expansion would hit a pre-existing non-dir — must uniquify, not crash.
    inner = _zip(tmp_path / "inner.zip", [("scan.dcm", b"DICMDATA")])
    with open(inner, "rb") as f:
        inner_bytes = f.read()
    outer = _zip(tmp_path / "outer.zip", [
        ("inner.zip", inner_bytes),
        ("inner_contents", b"i am a regular file, not a directory"),
    ])
    # Should complete without raising (FileExistsError/NotADirectoryError).
    result = import_zip(outer, str(tmp_path / "proj"), 1)
    assert os.path.isdir(result.disc_dir)
