"""Source identity: sample a tree's DICOM Study UIDs and tell whether a source
has already been imported into the project.

Used to stop the wizard from silently re-importing studies that are already in
the project (e.g. re-inserting the same disc, or a USB whose studies were
already copied). Study-level UIDs are the right granularity: every instance of
a study shares its StudyInstanceUID, so sampling a handful of files reliably
identifies the studies present. Local I/O only.
"""

from __future__ import annotations

import os
import time
from typing import Optional, Set

import pydicom

from .common import CancelToken, check_cancel, is_dicom_file

_MANIFEST_PREFIX = "Study UIDs   :"


def sample_study_uids(root: str, *, max_files: int = 300,
                      max_seconds: float = 5.0,
                      cancel: Optional[CancelToken] = None) -> Set[str]:
    """StudyInstanceUIDs found under ``root`` — bounded so it's cheap even on
    optical media (reads only the StudyInstanceUID tag, stops at the caps)."""
    uids: Set[str] = set()
    seen = 0
    start = time.time()
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            check_cancel(cancel)
            path = os.path.join(dirpath, fn)
            if not is_dicom_file(path):
                continue
            try:
                ds = pydicom.dcmread(path, specific_tags=["StudyInstanceUID"],
                                     stop_before_pixels=True, force=True)
                uid = str(getattr(ds, "StudyInstanceUID", "") or "")
            except Exception:
                uid = ""
            if uid:
                uids.add(uid)
            seen += 1
            if seen >= max_files or time.time() - start > max_seconds:
                return uids
    return uids


def _manifest_path(disc_dir: str, manifest_path: str = "") -> str:
    return manifest_path or os.path.join(disc_dir, "_manifest.txt")


def record_study_uids(disc_dir: str, manifest_path: str = "") -> Set[str]:
    """Sample ``disc_dir`` and append a ``Study UIDs:`` line to its manifest so
    later dedup checks are a cheap manifest read. Returns the sampled UIDs."""
    uids = sample_study_uids(disc_dir)
    if not uids:
        return uids
    try:
        with open(_manifest_path(disc_dir, manifest_path), "a",
                  encoding="utf-8") as f:
            f.write(f"\n{_MANIFEST_PREFIX} {', '.join(sorted(uids))}\n")
    except OSError:
        pass
    return uids


def _manifest_study_uids(disc_dir: str) -> Optional[Set[str]]:
    """UIDs recorded in a disc's manifest, or None if the line is absent (the
    disc predates this feature) so the caller can fall back to live sampling."""
    path = _manifest_path(disc_dir)
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith(_MANIFEST_PREFIX):
                    rest = line[len(_MANIFEST_PREFIX):].strip()
                    return {u.strip() for u in rest.split(",") if u.strip()}
    except OSError:
        return None
    return None


def project_study_uids(raw_discs_dir: str) -> Set[str]:
    """Union of every imported disc's Study UIDs — from manifests where present,
    falling back to a live sample for discs imported before this feature."""
    uids: Set[str] = set()
    if not os.path.isdir(raw_discs_dir):
        return uids
    for entry in sorted(os.listdir(raw_discs_dir)):
        disc = os.path.join(raw_discs_dir, entry)
        if not os.path.isdir(disc) or not entry.startswith("disc_"):
            continue
        recorded = _manifest_study_uids(disc)
        uids |= recorded if recorded is not None else sample_study_uids(disc)
    return uids


def looks_already_imported(src: str, raw_discs_dir: str) -> bool:
    """True when every study on ``src`` is already in the project — i.e. this
    source has effectively been imported before."""
    src_uids = sample_study_uids(src)
    if not src_uids:
        return False
    return src_uids <= project_study_uids(raw_discs_dir)
