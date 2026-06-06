"""Tests for the user-initiated update check."""

from __future__ import annotations

import json

import pytest

from mia import __version__
from mia.gui import updates


def test_parse_version():
    assert updates.parse_version("0.1.5") == (0, 1, 5)
    assert updates.parse_version("v1.2.3") == (1, 2, 3)
    assert updates.parse_version("1.2.3-rc1") == (1, 2, 3)
    assert updates.parse_version("") == (0,)
    assert updates.parse_version("10.0.0") > updates.parse_version("9.9.9")


def _serve(tmp_path, payload) -> str:
    f = tmp_path / "version.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    return f.as_uri()


def test_check_newer(tmp_path):
    url = _serve(tmp_path, {"version": "99.0.0"})
    result = updates.check(url=url)
    assert result.newer
    assert result.latest == "99.0.0"
    assert result.current == __version__


def test_check_up_to_date(tmp_path):
    url = _serve(tmp_path, {"version": __version__})
    assert not updates.check(url=url).newer


def test_check_older_remote_is_not_newer(tmp_path):
    url = _serve(tmp_path, {"version": "0.0.1"})
    assert not updates.check(url=url).newer


def test_check_raises_on_garbage(tmp_path):
    f = tmp_path / "version.json"
    f.write_text("not json", encoding="utf-8")
    with pytest.raises(Exception):
        updates.check(url=f.as_uri())


def test_check_raises_on_unreachable(tmp_path):
    with pytest.raises(Exception):
        updates.check(url=(tmp_path / "missing.json").as_uri())


def test_repo_version_json_is_valid():
    data = json.load(open("website/version.json", encoding="utf-8"))
    assert {"version", "mac", "win", "notes"} <= set(data)
    assert data["mac"]["url"].endswith(".dmg")
    assert len(data["mac"]["sha256"]) == 64
