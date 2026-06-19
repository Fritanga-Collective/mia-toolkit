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


def test_scrub_redacts_linux_media_and_mnt_mounts():
    # Regression: the /media/ branch uses the second capture group; scrub must
    # not raise IndexError and must redact the mount label.
    m = dx.scrub("Mounted /media/jdoe/PATIENT_USB and read it")
    assert "jdoe" not in m and "PATIENT_USB" not in m and "/media/<drive>" in m
    n = dx.scrub("Copying to /mnt/SMITH_CD/IM0001")
    assert "SMITH" not in n and "/mnt/<drive>" in n


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


def test_filter_keeps_ditto_errors_drops_copy_stream():
    # ditto -v streams "Copying …" per file (re-prefixed "ditto: Copying …"),
    # but reports real errors as "ditto: ditto: <message>". Drop the former,
    # keep the latter — it's the diagnostic signal.
    lines = [
        "10:00:02  ditto: Copying /Volumes/X/IM0001",
        "10:00:03  ditto: ditto: Cannot get the real path for source '/Volumes/X'",
    ]
    kept, dropped = dx.filter_log(lines)
    assert dropped == 1
    joined = "\n".join(kept)
    assert "Cannot get the real path" in joined


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
    assert set(env) >= {"app_version", "build", "os", "arch", "python"}
    # "build" replaces the old "frozen" flag (which read like "the app froze").
    assert "frozen" not in env
    assert env["build"] in ("packaged app", "source checkout")


def test_redact_toggle():
    assert dx.redacting() is False
    dx.set_redact(True)
    try:
        assert dx.redacting() is True
    finally:
        dx.set_redact(False)
    assert dx.redacting() is False


def test_build_report_caps_log_for_email_body():
    log = [f"10:00:{i:02d}  step {i}" for i in range(10)]
    report = dx.build_report("", log, max_log_lines=2)
    assert "trimmed" in report                 # cap marker present
    assert "step 9" in report                  # keeps the tail
    assert "step 0" not in report              # drops the head


def test_filter_drops_progress_heartbeats_keeps_milestones():
    # The "[done/total] pct% rate/s ETA" heartbeats are tick spam now that the
    # summary carries throughput — drop them, keep milestones/errors/warnings.
    lines = [
        "10:00:01  walked 6400 files in 0.3s",
        "10:00:02  [1/6400]  0.0%  0/s  ETA 0s",
        "10:00:30  [3200/6400] 50.0%  9/s  ETA 5m 0s",
        "10:00:31  slow media: ~1.2 files/s — the USB drive may be failing",
        "10:01:00  verify/fill pass: 6400 copied, 0 skipped, 0 failed in 2.0s",
    ]
    kept, dropped = dx.filter_log(lines)
    assert dropped == 2                          # both [n/n] ticks
    joined = "\n".join(kept)
    assert "walked 6400" in joined
    assert "slow media" in joined                # warning kept
    assert "verify/fill pass" in joined
    assert "[3200/6400]" not in joined


def test_environment_build_label():
    assert dx.environment()["build"] in ("packaged app", "source checkout")


def test_media_info_unknown_on_bogus_path_no_raise():
    info = dx.media_info("/this/path/does/not/exist/ever/12345")
    assert set(info) == {"filesystem", "total", "free"}
    # Must never raise; filesystem of a non-existent path is "unknown".
    assert info["filesystem"] == "unknown"


def test_media_info_real_path_reports_total_free():
    info = dx.media_info(os.path.expanduser("~"))
    # On a real path total/free should resolve (filesystem may still be unknown
    # if the OS probe isn't available in CI).
    assert info["total"] != "unknown"
    assert info["free"] != "unknown"


def test_verdict_thresholds():
    # Errors/retries -> failing-drive language.
    assert "failing" in dx.verdict(
        {"failed": 1, "retries": 0, "files_per_sec": 8}).lower()
    assert "failing" in dx.verdict(
        {"failed": 0, "retries": 2, "files_per_sec": 8}).lower()
    # Very slow, no errors -> counterfeit/failing/slow-port caution.
    slow = dx.verdict({"failed": 0, "retries": 0, "files_per_sec": 1.0})
    assert "counterfeit" in slow.lower() or "failing" in slow.lower()
    # Slow-but-not-alarming on exFAT (between the floor and the healthy band) ->
    # normal small-file overhead, not a fault.
    slow_fat = dx.verdict({"failed": 0, "retries": 0, "files_per_sec": 3.0,
                           "filesystem": "exFAT"})
    assert "not a fault" in slow_fat.lower()
    # Healthy ~8 files/s on exFAT must NOT be called "slow" — it's at the normal
    # FAT/exFAT rate, so the verdict should read as plain-normal throughput.
    fast_fat = dx.verdict({"failed": 0, "retries": 0, "files_per_sec": 8.0,
                           "filesystem": "exFAT"})
    assert "slow" not in fast_fat.lower()
    assert "normal" in fast_fat.lower()
    # Cancelled -> not a fault.
    assert "cancel" in dx.verdict({"cancelled": True}).lower()


def test_build_report_with_summary_renders_throughput_media_verdict():
    summary = {
        "op": "copy to USB",
        "result": "verified",
        "files_copied": 6400, "files_skipped": 0, "failed": 0, "retries": 0,
        "elapsed": 800.0, "files_per_sec": 8.0, "mb_per_sec": 2.0,
        "filesystem": "exFAT", "free": "12.0 GB", "total": "32.0 GB",
        "slow_media": False,
        "slowest_files": [("disc_01/DOE^JANE/IM0001", 1.23)],
    }
    report = dx.build_report("the copy felt off", [], summary=summary)
    assert "## Last operation" in report
    assert "8.0 files/s" in report and "2.0 MB/s" in report
    assert "## Media" in report and "exFAT" in report
    assert "## Verdict" in report
    # Healthy ~8 files/s on exFAT reads as plain-normal throughput, not the
    # "slow but…" overhead message (which is reserved for the slow-but-OK band).
    assert dx.verdict(summary) in report
    assert "slow but" not in report.lower()
    assert "throughput looks normal" in report.lower()
    # Slowest-file rel paths are scrubbed — no PHI survives.
    assert "DOE" not in report and "JANE" not in report
    assert "## Slowest files" in report


def test_build_report_without_summary_omits_sections():
    report = dx.build_report("x", ["10:00:00  walked 5 files in 0.1s"])
    assert "## Last operation" not in report
    assert "## Media" not in report
    assert "## Verdict" not in report
