import os

from mia.gui.project import Project


def test_paths_derive_from_root(tmp_path):
    p = Project(str(tmp_path / "proj"))
    assert p.raw_discs_dir.endswith(os.path.join("proj", "raw_discs"))
    assert p.archive_dir.endswith(os.path.join("proj", "Archive"))
    assert p.inventory_path.endswith("dicom_inventory.xlsx")


def test_disc_detection_and_counts(tmp_path):
    p = Project(str(tmp_path / "proj"))
    p.ensure_dirs()
    assert p.disc_count() == 0
    assert not p.has_discs()

    os.makedirs(os.path.join(p.raw_discs_dir, "disc_01_2026-01-01_A"))
    os.makedirs(os.path.join(p.raw_discs_dir, "disc_02_2026-01-02_B"))
    # A non-disc folder must not be counted.
    os.makedirs(os.path.join(p.raw_discs_dir, "notes"))
    assert p.disc_count() == 2
    assert p.has_discs()


def test_has_archive(tmp_path):
    p = Project(str(tmp_path / "proj"))
    p.ensure_dirs()
    assert not p.has_archive()
    os.makedirs(p.archive_dir)
    open(os.path.join(p.archive_dir, "DICOMDIR"), "w").close()
    assert p.has_archive()
