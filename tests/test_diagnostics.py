"""The diagnostic-report scrubber is safety-critical: it must strip PHI from a
medical app's logs before the user emails them. These tests bias toward proving
PHI does NOT survive."""

import os

from mia.core import diagnostics as dx


def test_scrub_redacts_home_and_username():
    home = os.path.expanduser("~")
    assert dx.scrub(f"Preparing to copy to {home}/Documents/x").startswith(
        "Preparing to copy to ~/")
    s = dx.scrub("File \"/Users/janedoe/Documents/MedicalArchive/Archive\"")
    assert "janedoe" not in s
    w = dx.scrub(r"path C:\Users\JaneDoe\AppData\file")
    assert "JaneDoe" not in w


def test_scrub_redacts_volume_and_disc_label():
    s = dx.scrub("Fast-copying to /Volumes/SMITH_JOHN_CD/CaseReview")
    assert "SMITH_JOHN" not in s and "/Volumes/<drive>" in s
    d = dx.scrub("Could not add /x/raw_discs/disc_03_2021_GARCIA_MARIA/IM0009")
    assert "GARCIA" not in d and "MARIA" not in d
    assert "disc_03" in d                      # disc number kept, label gone


def test_scrub_redacts_dicom_uid():
    s = dx.scrub("study 1.2.840.113619.2.55.3.604688.1 added")
    assert "1.2.840" not in s and "<uid>" in s


def test_scrub_redacts_patient_folder_keeps_structure():
    line = "copy raw_discs/disc_01/DOE^JANE/BRAIN MRI/IM0001"
    s = dx.scrub(line)
    assert "DOE" not in s and "JANE" not in s
    assert "raw_discs" in s and "disc_01" in s and "IM0001" in s


def test_scrub_keeps_code_paths_readable():
    # App/library tracebacks aren't PHI and stay useful.
    s = dx.scrub("/x/site-packages/pydicom/fileset.py line 42, in write")
    assert "pydicom" in s and "fileset.py" in s


def test_scrub_leaves_plain_text_alone():
    assert dx.scrub("7 studies, 1840 images copied in 41.2s") == (
        "7 studies, 1840 images copied in 41.2s")


def test_filter_drops_per_file_and_clinical_lines():
    lines = [
        "10:00:01  walked 6400 files in 0.3s",
        "10:00:02  copying disc_01/DOE^JANE/IM0001",
        "10:00:02  ditto: Copying /Volumes/X/IM0002",
        "10:00:03  indexing study: MR BRAIN POST GADOLINIO",
        "10:00:59  native copy finished: rc=0 in 41.2s",
        "10:01:00  verify/fill pass: 6400 copied, 0 skipped, 0 failed in 2.0s",
    ]
    kept, dropped = dx.filter_log(lines)
    assert dropped == 3
    joined = "\n".join(kept)
    assert "walked 6400" in joined and "native copy finished" in joined
    assert "DOE" not in joined and "BRAIN" not in joined


def test_build_report_is_anonymized_end_to_end():
    home = os.path.expanduser("~")
    log = [
        f"10:00:00  Preparing to copy to {home}/Documents/MedicalArchive/Archive",
        "10:00:02  copying disc_01/DOE^JANE/SECRET STUDY/IM0001",
        "10:00:03  ERROR reading /Volumes/PATIENT_USB/disc_02_2020_LOPEZ/IM2",
        "10:00:59  native copy finished: rc=0 in 41.2s",
    ]
    report = dx.build_report("It froze on the second study.", log,
                             extra={"language": "es", "screen": "Build & deliver"})
    # No PHI tokens anywhere in the assembled report.
    for leak in ("DOE", "JANE", "LOPEZ", "PATIENT_USB", "SECRET"):
        assert leak not in report, f"PHI leaked: {leak}"
    assert os.path.basename(home) not in report or home == "/"
    # Useful content survives.
    assert "It froze on the second study." in report
    assert "## Environment" in report and "app_version" in report
    assert "language: es" in report
    assert "rc=0 in 41.2s" in report             # kept, scrubbed line


def test_environment_has_core_fields():
    env = dx.environment()
    assert set(env) >= {"app_version", "frozen", "os", "arch", "python"}
