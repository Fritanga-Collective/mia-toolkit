"""Smart, incremental re-delivery to a USB drive: detect & update, don't duplicate.

A delivery puts a ``CaseReview_<PatientName>`` folder on the USB containing the
DICOM ``Archive/``, the inventory, doctor-facing docs, and a hidden
``.mia-archive.json`` marker that records *whose* archive this is. On the next
delivery to the same drive we read those markers, recognize a folder belonging to
the same patient, and update it in place — so the already-incremental
:func:`mia.core.deliver.copy_tree_verified` (resume/verify) and the append-on-
redelivery :func:`mia.core.dicomdir.write_delivery_log` actually do their job
instead of being defeated by a fresh dated folder every time.

This module is pure stdlib + an optional ``pydicom`` import (only for reading a
legacy folder's patient identity), so it's unit-testable without a GUI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .diagnostics import redacting
from .ripper import sanitize_label

# Hidden machine-readable marker at the CaseReview root. Bump schema_version on
# any incompatible change to the on-disk shape.
MARKER_NAME = ".mia-archive.json"
SCHEMA_VERSION = 1

# Generic, PHI-free folder name used when the patient is unknown/ambiguous or
# when redaction (screencast) mode is on.
GENERIC_FOLDER = "CaseReview"
FOLDER_PREFIX = "CaseReview_"


@dataclass
class DeliveryInfo:
    """What we know about one CaseReview folder already on a USB drive."""

    folder: str                       # absolute path to the CaseReview root
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    studies: Optional[int] = None
    instances: Optional[int] = None
    created: Optional[str] = None      # ISO 8601
    updated: Optional[str] = None      # ISO 8601
    legacy: bool = False               # recognized by structure, no marker


# ---- Decision returned by choose_target -----------------------------------

NEW = "new"        # no matching folder on the drive — make a fresh one
UPDATE = "update"  # same-patient folder found — update it in place
ASK = "ask"        # only different-patient folder(s) — let the user choose


@dataclass
class Decision:
    """Outcome of :func:`choose_target`."""

    action: str                       # NEW / UPDATE / ASK
    folder: Optional[str] = None      # resolved target (UPDATE) or proposed (NEW)
    existing: List[DeliveryInfo] = field(default_factory=list)  # for ASK


# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_folder_name(patient_name: Optional[str]) -> str:
    """``CaseReview_<PatientName>`` (filesystem-safe), or a generic ``CaseReview``.

    Falls back to the generic, PHI-free name when the patient is unknown *or*
    when redaction (screencast) mode is on, so a recording never shows a name.
    """
    if redacting() or not patient_name:
        return GENERIC_FOLDER
    safe = sanitize_label(patient_name)
    return f"{FOLDER_PREFIX}{safe}" if safe else GENERIC_FOLDER


def write_marker(folder: str, *, patient_name: Optional[str],
                 patient_id: Optional[str], result=None,
                 when: Optional[datetime] = None) -> str:
    """Write/refresh the hidden ``.mia-archive.json`` marker at ``folder``.

    Preserves the original ``created`` timestamp across re-deliveries (only
    ``updated`` advances). ``result`` may be a ``DicomdirResult`` (or anything
    with ``.studies`` / ``.added``); pass ``None`` to leave counts unknown.
    Returns the marker path.
    """
    path = os.path.join(folder, MARKER_NAME)
    stamp = (when or datetime.now(timezone.utc)).astimezone(
        timezone.utc).replace(microsecond=0).isoformat()
    created = stamp
    prev = read_marker(folder)
    if prev is not None and prev.created:
        created = prev.created

    studies = getattr(result, "studies", None)
    instances = getattr(result, "added", None)

    data = {
        "schema_version": SCHEMA_VERSION,
        "patient_name": patient_name,
        "patient_id": patient_id,
        "studies": studies,
        "instances": instances,
        "created": created,
        "updated": stamp,
    }
    os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)
    return path


def _read_legacy(folder: str) -> Optional[DeliveryInfo]:
    """Recognize a pre-marker MIA delivery by its structure (Archive/DICOMDIR +
    DELIVERY-LOG.txt). Derive the patient from the DICOMDIR via pydicom when
    possible; otherwise leave it None (still recognized as a MIA folder)."""
    dicomdir_path = os.path.join(folder, "Archive", "DICOMDIR")
    log_path = os.path.join(folder, "DELIVERY-LOG.txt")
    if not (os.path.exists(dicomdir_path) and os.path.exists(log_path)):
        return None
    name = pid = None
    try:
        import pydicom
        from pydicom.fileset import FileSet

        fs = FileSet(pydicom.dcmread(dicomdir_path))
        for inst in fs:
            n = getattr(inst, "PatientName", None)
            i = getattr(inst, "PatientID", None)
            name = str(n) if n else None
            pid = str(i) if i else None
            break
    except Exception:
        pass
    return DeliveryInfo(folder=folder, patient_name=name, patient_id=pid,
                        legacy=True)


def read_marker(folder: str) -> Optional[DeliveryInfo]:
    """Read ``folder``'s ``.mia-archive.json`` into a :class:`DeliveryInfo`.

    Back-compat: if the marker is absent but the folder *looks* like a legacy
    MIA delivery (``Archive/DICOMDIR`` + ``DELIVERY-LOG.txt``), recognize it and
    derive the patient from the DICOMDIR when feasible. Returns ``None`` for a
    folder we don't recognize as a MIA archive.
    """
    path = os.path.join(folder, MARKER_NAME)
    if not os.path.exists(path):
        return _read_legacy(folder)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return _read_legacy(folder)
    if not isinstance(data, dict):
        return _read_legacy(folder)
    return DeliveryInfo(
        folder=folder,
        patient_name=data.get("patient_name"),
        patient_id=data.get("patient_id"),
        studies=data.get("studies"),
        instances=data.get("instances"),
        created=data.get("created"),
        updated=data.get("updated"),
    )


def find_deliveries(usb_root: str) -> List[DeliveryInfo]:
    """Scan ``usb_root``'s top-level folders for MIA deliveries (marker or
    recognized legacy structure). Returns them in sorted-folder order."""
    out: List[DeliveryInfo] = []
    try:
        entries = sorted(os.listdir(usb_root))
    except OSError:
        return out
    for name in entries:
        folder = os.path.join(usb_root, name)
        if not os.path.isdir(folder):
            continue
        info = read_marker(folder)
        if info is not None:
            out.append(info)
    return out


def _norm(value: Optional[str]) -> str:
    """Normalize a patient field for matching: stripped, upper-cased, with the
    UNKNOWN placeholder (build_dicomdir's default) treated as empty."""
    s = (value or "").strip().upper()
    return "" if s in ("", "UNKNOWN") else s


def archive_identity(studies: Dict[str, dict]) -> Tuple[Optional[str], Optional[str]]:
    """Derive ``(patient_name, patient_id)`` for a just-built archive.

    ``studies`` is the per-study mapping produced by
    :func:`mia.core.inventory.scan_directory` (each value has ``patient_name`` /
    ``patient_id``). The dominant patient wins; a genuine multi-patient mix, or
    no usable identity at all, yields ``(None, None)`` so the caller falls back
    to a generic folder name.
    """
    name_counts: Dict[str, int] = {}
    raw_name: Dict[str, str] = {}
    id_counts: Dict[str, int] = {}
    raw_id: Dict[str, str] = {}
    for study in (studies or {}).values():
        n = _norm(study.get("patient_name"))
        if n:
            name_counts[n] = name_counts.get(n, 0) + 1
            raw_name.setdefault(n, (study.get("patient_name") or "").strip())
        i = _norm(study.get("patient_id"))
        if i:
            id_counts[i] = id_counts.get(i, 0) + 1
            raw_id.setdefault(i, (study.get("patient_id") or "").strip())

    name = None
    if len(name_counts) == 1:
        name = raw_name[next(iter(name_counts))]
    elif len(name_counts) > 1:
        return (None, None)            # genuine mismatch → generic

    pid = None
    if len(id_counts) == 1:
        pid = raw_id[next(iter(id_counts))]
    elif len(id_counts) > 1:
        pid = None                     # ambiguous id, but name may still hold

    return (name, pid)


def _same_patient(info: DeliveryInfo, patient: Tuple[Optional[str], Optional[str]]
                  ) -> bool:
    """Does an on-disk delivery belong to the same patient as ``patient``?

    Matches on ID when both sides have one (the strong key); otherwise on name.
    An on-disk folder with no identity at all (legacy DICOMDIR we couldn't read)
    never auto-matches — better to ask than to silently overwrite.
    """
    name, pid = patient
    n_name, n_pid = _norm(name), _norm(pid)
    i_name, i_pid = _norm(info.patient_name), _norm(info.patient_id)
    if n_pid and i_pid:
        return n_pid == i_pid
    if n_name and i_name:
        return n_name == i_name
    return False


def choose_target(usb_root: str,
                  patient: Tuple[Optional[str], Optional[str]]) -> Decision:
    """Decide where this delivery goes on ``usb_root``.

    Smart rule:
      * a same-patient folder already exists  → ``UPDATE`` that folder;
      * only different-patient folder(s) exist → ``ASK`` (caller prompts);
      * nothing recognizable                  → ``NEW`` (proposed folder name).
    """
    existing = find_deliveries(usb_root)
    for info in existing:
        if _same_patient(info, patient):
            return Decision(UPDATE, folder=info.folder, existing=existing)
    if existing:
        proposed = os.path.join(usb_root, safe_folder_name(patient[0]))
        return Decision(ASK, folder=proposed, existing=existing)
    return Decision(NEW, folder=os.path.join(usb_root,
                                             safe_folder_name(patient[0])),
                    existing=existing)


def find_orphans(src_archive: str, dest_folder: str) -> List[str]:
    """Files under ``dest_folder`` (in ``Archive/`` and ``Reports/``) that are
    *not* in the freshly built source set — i.e. left over from a previous,
    larger delivery to the same patient folder.

    ``src_archive`` is the just-built source ``Archive/`` directory. We compare
    the destination ``Archive/`` against it by relative path; destination
    ``Reports/`` files are all considered candidates (the source set is the
    current document plan, which the caller has already re-copied, so any extra
    Reports file is an orphan from a previous delivery). The hidden marker, the
    DELIVERY-LOG, README, and the inventory are never reported as orphans.

    Returns destination-relative paths (POSIX-ish, using ``os.sep``).
    """
    orphans: List[str] = []
    src_archive = os.path.abspath(src_archive)

    # Build the set of expected Archive-relative paths from the source.
    expected = set()
    for dirpath, _dirs, files in os.walk(src_archive):
        for fn in files:
            rel = os.path.relpath(os.path.join(dirpath, fn), src_archive)
            expected.add(rel)

    dest_archive = os.path.join(dest_folder, "Archive")
    if os.path.isdir(dest_archive):
        for dirpath, _dirs, files in os.walk(dest_archive):
            for fn in files:
                rel = os.path.relpath(os.path.join(dirpath, fn), dest_archive)
                if rel not in expected:
                    orphans.append(os.path.join("Archive", rel))

    return orphans


def remove_orphans(dest_folder: str, relpaths: List[str]) -> int:
    """Delete the given destination-relative files and prune any directories
    they leave empty (down to, but not including, ``dest_folder``). Returns the
    number of files actually removed. Best-effort: unreadable/locked files are
    skipped."""
    removed = 0
    pruned_roots = set()
    for rel in relpaths:
        full = os.path.join(dest_folder, rel)
        try:
            os.remove(full)
            removed += 1
            pruned_roots.add(os.path.dirname(full))
        except OSError:
            pass
    # Prune now-empty dirs, deepest first, never above dest_folder.
    dest_folder = os.path.abspath(dest_folder)
    for root in sorted(pruned_roots, key=len, reverse=True):
        d = os.path.abspath(root)
        while d.startswith(dest_folder) and d != dest_folder:
            try:
                os.rmdir(d)                # only succeeds if empty
            except OSError:
                break
            d = os.path.dirname(d)
    return removed
