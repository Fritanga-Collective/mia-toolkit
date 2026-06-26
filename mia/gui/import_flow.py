"""Shared pick → pre-scan → confirm → import flow.

Used by both the wizard's "Add your studies" step and the standalone tool view.
Mirrors RipSessionController's contract: drives a ProgressLogPanel, reports
running-state through a callback, and returns the job's cancel token (or None
if the user backed out) so callers can wire their Stop/on_leave handling.
All sources are local I/O only — no network.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any, Callable, Optional

from mia_core import deliver, importer, ripper, sources
from mia_core.common import format_bytes

from . import jobs
from .i18n import _
from .messages import exception_detail, humanize_exception

StateCb = Callable[[bool], None]
DoneCb = Optional[Callable[[Any], None]]


def start_folder_import(root: Any, panel: Any, *,
                        get_dest: Callable[[], str],
                        on_state: StateCb,
                        on_done: DoneCb = None,
                        parent: Optional[tk.Misc] = None):
    """Pick a folder/USB, pre-scan it, confirm, then import. Returns the job's
    cancel token, or None if nothing was started."""
    src = filedialog.askdirectory(
        title=_("Choose the folder or USB drive to import"), parent=parent)
    if not src:
        return None
    dest = _prepare_dest(get_dest, panel)
    if not dest or not _outside_project(src, dest, parent):
        return None
    if sources.looks_already_imported(src, dest) and not messagebox.askyesno(
            _("Already added"),
            _("These studies look already added. Import again?"),
            default="no", parent=parent):
        return None

    scan = importer.scan_folder(src)  # synchronous but capped (metadata only)
    # A capped scan only saw part of the tree — treat its size as an estimate
    # and demand much larger headroom.
    if not _has_room(scan.bytes, dest, parent,
                     headroom=2.0 if scan.capped else 1.1):
        return None
    if scan.dicom_files == 0:
        if not messagebox.askyesno(
                _("Import"),
                _("No medical images were found here. Copy anyway?"),
                icon="warning", default="no", parent=parent):
            return None
    else:
        files_txt = f"{scan.files:,}" + ("+" if scan.capped else "")
        size_txt = format_bytes(scan.bytes) + ("+" if scan.capped else "")
        if not messagebox.askyesno(
                _("Import"),
                _("{files} files · {size}\n{dicom} medical images detected."
                  "\n\nCopy everything into your project?")
                .format(files=files_txt, size=size_txt,
                        dicom=scan.dicom_files),
                parent=parent):
            return None
    return _start_job(root, panel, parent, on_state, on_done,
                      src=src, dest=dest, kind="folder")


def start_zip_import(root: Any, panel: Any, *,
                     get_dest: Callable[[], str],
                     on_state: StateCb,
                     on_done: DoneCb = None,
                     parent: Optional[tk.Misc] = None):
    """Pick a downloaded ZIP, confirm, then extract + import. Returns the job's
    cancel token, or None if nothing was started."""
    src = filedialog.askopenfilename(
        title=_("Choose the ZIP file to import"), parent=parent,
        filetypes=[("ZIP", ("*.zip", "*.ZIP")),
                   (_("All files"), "*.*")])
    if not src:
        return None
    dest = _prepare_dest(get_dest, panel)
    if not dest:
        return None
    try:
        scan = importer.scan_zip(src)
    except Exception:
        messagebox.showerror(
            _("Import"), _("This doesn't look like a ZIP file."),
            parent=parent)
        return None
    # Extraction (now on the project volume) needs temp space too, and nested
    # zip-of-zips can expand beyond the outer ZIP's declared sizes — so demand
    # double the bytes with double headroom (~4x the declared content).
    if not _has_room(scan.bytes * 2, dest, parent, headroom=2.0):
        return None
    if not messagebox.askyesno(
            _("Import"),
            _("{files} files · {size} inside the ZIP.\nMedical images are "
              "detected during the import.\n\nImport it into your project?")
            .format(files=f"{scan.files:,}", size=format_bytes(scan.bytes)),
            parent=parent):
        return None
    return _start_job(root, panel, parent, on_state, on_done,
                      src=src, dest=dest, kind="zip")


# ----- internals ------------------------------------------------------------

def _prepare_dest(get_dest: Callable[[], str], panel: Any) -> Optional[str]:
    dest = get_dest()
    if not dest:
        panel.set_status(_("Please choose a folder to save copies to."))
        return None
    try:
        os.makedirs(dest, exist_ok=True)
    except OSError:
        panel.set_status(_("Couldn't create that folder. Choose another."))
        return None
    return dest


def _outside_project(src: str, dest: str, parent) -> bool:
    """Block importing the project into itself (or a parent of it)."""
    s = os.path.realpath(src)
    d = os.path.realpath(dest)
    if s == d or s.startswith(d + os.sep) or d.startswith(s + os.sep):
        messagebox.showerror(
            _("Import"),
            _("That folder is inside your project (or contains it). "
              "Choose a different folder."), parent=parent)
        return False
    return True


def _has_room(need_bytes: int, dest: str, parent, *,
              headroom: float = 1.1) -> bool:
    free = deliver.free_space(dest)
    if free >= int(need_bytes * headroom):
        return True
    messagebox.showerror(
        _("Import"),
        _("Not enough space on the project drive (need about {need}, "
          "free {free}).").format(need=format_bytes(need_bytes),
                                  free=format_bytes(free)),
        parent=parent)
    return False


def _start_job(root, panel, parent, on_state: StateCb, on_done: DoneCb, *,
               src: str, dest: str, kind: str):
    num = ripper.next_disc_number(dest)
    name = os.path.basename(src.rstrip(os.sep)) or src
    panel.start_session_log(dest)
    on_state(True)
    panel.set_status(_("Importing “{name}”…").format(name=name))
    panel.log_plain(_("Importing “{name}”…").format(name=name))

    def work(emit, cancel):
        if kind == "zip":
            return importer.import_zip(src, dest, num,
                                       progress=emit, cancel=cancel)
        return importer.import_folder(src, dest, num,
                                      progress=emit, cancel=cancel)

    def done(status, result):
        panel.set_indeterminate(False)
        panel.close_session_log()
        on_state(False)
        if status == "cancelled":
            panel.log_plain(_("Stopped."))
            panel.set_status(_("Stopped."))
            return
        if status == "error":
            panel.log_plain(humanize_exception(result), tag="fail")
            panel.log_technical(exception_detail(result))
            panel.set_status(_("Couldn't import this source."))
            return
        ok = result.failed == 0
        panel.log_plain(
            _("✓ Imported: {c} files OK, {f} could not be read.")
            .format(c=result.copied, f=result.failed),
            tag="done" if ok else "fail")
        if result.dicom_files == 0:
            panel.log_plain(_("⚠ No medical images were found in this "
                              "import."), tag="fail")
            messagebox.showwarning(
                _("Import"),
                _("No medical images were found in this import."),
                parent=parent)
        panel.set_status(_("✓ Import done. Add another source or continue."))
        if on_done:
            on_done(result)

    return jobs.run_job(root, work, panel.on_event, done)
