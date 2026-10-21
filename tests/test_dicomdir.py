import os

import pytest
from pydicom.fileset import FileSet

from mia_core import dicomdir
from mia_core.common import Cancelled
from tests.helpers import CancelNow


def test_build_dedups_and_repairs(dataset_dir, tmp_path):
    root, expected = dataset_dir
    out = tmp_path / "Archive"
    result = dicomdir.build_fileset(root, str(out))

    assert result is not None
    # The cross-disc duplicate (same SOPInstanceUID) is dropped...
    assert result.duplicates == expected["duplicates"]
    # ...and the tag-incomplete file is repaired and added, not errored.
    assert result.errors == 0
    assert result.added == expected["unique_instances"]
    assert result.studies == expected["studies"]


def test_build_writes_loadable_dicomdir(dataset_dir, tmp_path):
    root, _ = dataset_dir
    out = tmp_path / "Archive"
    result = dicomdir.build_fileset(root, str(out))

    dicomdir_path = out / "DICOMDIR"
    assert dicomdir_path.exists()

    # Re-open the produced file-set and confirm the instance count round-trips.
    fs = FileSet(str(dicomdir_path))
    assert len(list(fs)) == result.added


def test_study_groups_partitions_built_archive_by_study(dataset_dir, tmp_path):
    root, expected = dataset_dir
    out = tmp_path / "Archive"
    result = dicomdir.build_fileset(root, str(out))

    groups = dicomdir.study_groups(str(out))
    assert len(groups) == expected["studies"]                 # 2 studies
    assert len({g["uid"] for g in groups}) == len(groups)     # distinct UIDs
    assert sum(g["count"] for g in groups) == result.added    # every instance
    for g in groups:
        assert g["paths"] and g["count"] == len(g["paths"])
        for p in g["paths"]:
            assert os.path.isabs(p) and os.path.exists(p)
            assert os.path.abspath(str(out)) in p             # under the archive


def test_study_groups_missing_index_returns_empty(tmp_path):
    assert dicomdir.study_groups(str(tmp_path)) == []         # no DICOMDIR


def test_build_writes_readme(dataset_dir, tmp_path):
    root, _ = dataset_dir
    out = tmp_path / "Archive"
    result = dicomdir.build_fileset(root, str(out))
    readme = dicomdir.write_readme(str(out), result, root)
    assert os.path.exists(readme)
    text = open(readme).read()
    # Human-first entry point: leads with how to open, names viewers + DICOMDIR.
    assert "HOW TO OPEN THESE MEDICAL IMAGES" in text
    assert "Horos" in text and "DICOMDIR" in text


def test_build_emits_write_phase_progress(dataset_dir, tmp_path):
    # The final FileSet.write() is the slow phase; it must not be a silent black
    # box. Collect progress and assert we announce the write phase + finish it,
    # so the UI can't sit frozen at 100% with no heartbeat.
    root, _ = dataset_dir
    events = []
    dicomdir.build_fileset(root, str(tmp_path / "Archive"),
                           progress=lambda p: events.append(p))
    phases = [getattr(e, "phase", None) for e in events]
    assert "write" in phases
    notes = " ".join(getattr(e, "note", "") or "" for e in events)
    assert "Archive written." in notes


def test_build_empty_source_returns_none(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert dicomdir.build_fileset(str(empty), str(tmp_path / "out")) is None


def test_find_dicom_files_skips_junk(dataset_dir):
    root, expected = dataset_dir
    # 7 DICOM instances written (incl. the duplicate); junk excluded.
    assert len(list(dicomdir.find_dicom_files(root))) == 7


def test_build_cancellation(dataset_dir, tmp_path):
    root, _ = dataset_dir
    with pytest.raises(Cancelled):
        dicomdir.build_fileset(root, str(tmp_path / "out"), cancel=CancelNow())
