"""Tests for the DELIVERY-LOG.txt changelog written on each USB delivery."""

from __future__ import annotations

import os
from datetime import datetime

from mia_core import dicomdir


def _result(studies_info):
    return dicomdir.DicomdirResult(
        output="x", added=sum(s["count"] for s in studies_info.values()),
        studies=len(studies_info), duplicates=0, errors=0, skipped_no_uid=0,
        output_size=0, output_files=0, elapsed=0.0, studies_info=studies_info)


def test_delivery_log_creates_header_and_lists_studies(tmp_path):
    res = _result({
        "1.2.3": {"date": "20200115", "modality": "MR",
                  "description": "BRAIN", "count": 240},
        "1.2.4": {"date": "20210304", "modality": "CT",
                  "description": "CHEST", "count": 120},
    })
    path = dicomdir.write_delivery_log(str(tmp_path), res,
                                       when=datetime(2026, 6, 9, 14, 30, 0))
    text = open(path, encoding="utf-8").read()
    assert os.path.basename(path) == "DELIVERY-LOG.txt"
    assert "MIA Toolkit — Delivery log" in text          # header
    assert "[2026-06-09T14:30:00]  2 studies, 360 images copied" in text
    assert "2020-01-15  MR   BRAIN  (240 images)" in text
    assert "2021-03-04  CT   CHEST  (120 images)" in text


def test_delivery_log_appends_second_entry(tmp_path):
    res = _result({"1.2.3": {"date": "20200115", "modality": "MR",
                             "description": "BRAIN", "count": 5}})
    dicomdir.write_delivery_log(str(tmp_path), res,
                                when=datetime(2026, 6, 9, 9, 0, 0))
    dicomdir.write_delivery_log(str(tmp_path), res,
                                when=datetime(2026, 6, 10, 9, 0, 0))
    text = open(tmp_path / "DELIVERY-LOG.txt", encoding="utf-8").read()
    assert text.count("MIA Toolkit — Delivery log") == 1  # header once
    assert "[2026-06-09T09:00:00]" in text
    assert "[2026-06-10T09:00:00]" in text                # changelog grows


def test_delivery_log_handles_missing_result(tmp_path):
    path = dicomdir.write_delivery_log(str(tmp_path), None,
                                       when=datetime(2026, 6, 9, 0, 0, 0))
    assert ("[2026-06-09T00:00:00]  archive copied"
            in open(path, encoding="utf-8").read())
