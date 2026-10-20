"""Headless self-test for an installed/frozen build (no GUI, no network).

``MIA Toolkit --selftest`` (alias ``--self-test``) proves the shipped bundle
actually works, not just that it starts:

1. imports the heavy dependencies and every ``mia_core`` worker module;
2. writes a tiny **synthetic** DICOM study (two instances, fake patient
   ``SELFTEST^MIA`` — no real data, nothing bundled, nothing downloaded) into a
   temporary folder;
3. builds a DICOMDIR archive from it with ``mia_core.dicomdir.build_fileset``
   (the same code path the app's "Build Archive" step uses);
4. re-reads the written DICOMDIR and checks it indexes both images.

It prints one result line and returns 0 (pass) or 1 (fail). The release
workflow runs it against the built ``.app`` / installed ``.exe`` and fails the
job before anything is published (PRODUCTION-READINESS G15).

Windowed (no-console) builds may have no usable stdout, so the result can also
be written to a file named by ``MIA_SELFTEST_REPORT`` — CI reads that file.
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from typing import Callable, List, Optional

FLAGS = ("--selftest", "--self-test")
REPORT_ENV = "MIA_SELFTEST_REPORT"

# Standard MR Image Storage SOP class; the synthetic files mimic a minimal MR.
_MR_STORAGE = "1.2.840.10008.5.1.4.1.1.4"


def _write_fixture(folder: str, count: int = 2) -> List[str]:
    """Write ``count`` minimal, file-format-compliant DICOM instances (one
    synthetic study/series) under ``folder``. Mirrors ``tests/helpers.make_dicom``
    but lives in the app because ``tests/`` is not shipped in the bundle."""
    from pydicom.dataset import Dataset, FileMetaDataset
    from pydicom.uid import ExplicitVRLittleEndian, generate_uid

    study_uid, series_uid = generate_uid(), generate_uid()
    paths = []
    for n in range(1, count + 1):
        sop_uid = generate_uid()
        ds = Dataset()
        ds.SOPClassUID = _MR_STORAGE
        ds.SOPInstanceUID = sop_uid
        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.PatientID = "SELFTEST"
        ds.PatientName = "SELFTEST^MIA"
        ds.Modality = "MR"
        ds.StudyDate = "20000101"
        ds.StudyTime = "000000"
        ds.StudyID = "1"
        ds.StudyDescription = "MIA SELF-TEST"
        ds.SeriesNumber = 1
        ds.InstanceNumber = n
        fm = FileMetaDataset()
        fm.MediaStorageSOPClassUID = _MR_STORAGE
        fm.MediaStorageSOPInstanceUID = sop_uid
        fm.TransferSyntaxUID = ExplicitVRLittleEndian
        fm.ImplementationClassUID = generate_uid()
        ds.file_meta = fm
        path = os.path.join(folder, "disc_01", f"IM{n:04d}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ds.save_as(path, enforce_file_format=True)
        paths.append(path)
    return paths


def _check(extra_imports: Optional[Callable[[], None]] = None) -> str:
    """Run every check; return a one-line summary or raise on failure."""
    import openpyxl
    import pydicom

    import mia_core
    from mia_core import (  # noqa: F401  (import = bundle completeness check)
        common, deliver, delivery_target, diagnostics, dicomdir, documents,
        importer, inventory, ripper, sources,
    )

    from . import __version__

    if extra_imports is not None:
        extra_imports()

    with tempfile.TemporaryDirectory(prefix="mia-selftest-") as tmp:
        src = os.path.join(tmp, "raw_discs")
        out = os.path.join(tmp, "Archive")
        written = _write_fixture(src)
        result = dicomdir.build_fileset(src, out)
        if result is None:
            raise RuntimeError("build_fileset found no DICOM files")
        if result.added != len(written) or result.errors:
            raise RuntimeError(
                f"build_fileset added {result.added}/{len(written)} "
                f"instances with {result.errors} errors")
        dicomdir_path = os.path.join(out, "DICOMDIR")
        if not os.path.isfile(dicomdir_path):
            raise RuntimeError("no DICOMDIR written")
        ds = pydicom.dcmread(dicomdir_path)
        images = [r for r in ds.DirectoryRecordSequence
                  if r.DirectoryRecordType == "IMAGE"]
        if len(images) != len(written):
            raise RuntimeError(
                f"DICOMDIR indexes {len(images)} images, expected {len(written)}")

    return (f"selftest OK: MIA Toolkit {__version__}, mia_core "
            f"{mia_core.__version__}, pydicom {pydicom.__version__}, openpyxl "
            f"{openpyxl.__version__}; DICOMDIR built with {len(written)} images")


def _report(text: str) -> None:
    # print() is a silent no-op when sys.stdout is None (windowed builds).
    print(text)
    path = os.environ.get(REPORT_ENV)
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
        except OSError:
            pass


def run(extra_imports: Optional[Callable[[], None]] = None) -> int:
    """Run the self-test. Returns a process exit code (0 pass, 1 fail)."""
    try:
        summary = _check(extra_imports)
    except Exception as e:  # any failure must be reported, not crash silently
        _report("selftest FAILED: " + "".join(
            traceback.format_exception_only(type(e), e)).strip()
            + "\n" + traceback.format_exc())
        return 1
    _report(summary)
    return 0


def wants_selftest(argv: Optional[List[str]] = None) -> bool:
    return any(a in FLAGS for a in (sys.argv if argv is None else argv)[1:])


if __name__ == "__main__":
    sys.exit(run())
