"""Build archive screen: pick source + destination, build DICOMDIR, reveal it."""

from __future__ import annotations

import os
from tkinter import ttk
from typing import Any

from mia_core import delivery_target, dicomdir
from .i18n import N_, _
from .task_view import TaskView, reveal
from .three_button import ask_three
from .widgets import FolderPicker, default_dir


class ArchiveView(TaskView):
    title = N_("Build Archive for Doctor")

    def build_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text=_(
            "Combine all your ripped discs into one archive the radiologist can "
            "open. Choose where to save it — a USB drive is ideal.")
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.source = FolderPicker(parent, _("Ripped discs folder:"),
                                   default_dir("raw_discs"))
        self.source.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.dest = FolderPicker(parent, _("Save archive to:"),
                                 default_dir("Archive"))
        self.dest.grid(row=2, column=0, sticky="ew")

        self.run_btn = ttk.Button(parent, text=_("Build archive"),
                                  command=self._run)
        self.run_btn.grid(row=3, column=0, sticky="w", pady=(10, 0))

    def on_running_changed(self, running: bool) -> None:
        self.run_btn.configure(state="disabled" if running else "normal")
        self.source.set_enabled(not running)
        self.dest.set_enabled(not running)

    def _run(self) -> None:
        source = self.source.get()
        out = self.dest.get()
        if not os.path.isdir(source):
            self.set_status(_("Please choose a valid ripped-discs folder."))
            return
        if not out:
            self.set_status(_("Please choose where to save the archive."))
            return
        self._update = False
        if os.path.isdir(out) and os.listdir(out):
            # A non-empty destination is only safe to touch if it's a MIA
            # archive we recognize — then we update it incrementally. Anything
            # else (unknown data) we refuse to clobber, as before.
            if delivery_target.read_marker(out) is None:
                self.set_status(_("That destination already has files in it."))
                self.log_plain(_("⚠ The destination folder isn't empty. Choose "
                                 "an empty folder (or a new one) so the archive "
                                 "stays clean."), tag="fail")
                return
            choice = ask_three(
                self.app.root, _("Update existing archive"),
                _("This folder already holds a MIA archive. Update it with the "
                  "latest images, or cancel?"),
                [(_("Update"), True), (_("Cancel"), None)], cancel=None)
            if not choice:
                self.set_status(_("Cancelled."))
                return
            self._update = True

        self._source = source
        self._out = out
        # Snapshot the existing files so we can detect orphans (left over from a
        # previous, larger build) after the rebuild.
        self._before = self._snapshot(out) if self._update else set()
        self.set_status(_("Scanning for images…"))
        self.log_plain(_("Looking for all DICOM images under {f}…")
                       .format(f=source))

        def work(emit, cancel):
            return dicomdir.build_fileset(source, out, progress=emit,
                                          cancel=cancel)

        self.start_job(work, self._finish, log_dir=out)

    @staticmethod
    def _snapshot(folder: str) -> set:
        """Relative paths of all files under ``folder`` (excluding the hidden
        marker), for orphan detection across a rebuild."""
        out = set()
        for dirpath, _dirs, files in os.walk(folder):
            for fn in files:
                if fn == delivery_target.MARKER_NAME:
                    continue
                out.add(os.path.relpath(os.path.join(dirpath, fn), folder))
        return out

    def _finish(self, status: str, result: Any) -> None:
        if status != "done":
            return
        if result is None:
            self.set_status(_("No DICOM images found in that folder."))
            self.log_plain(_("No images found. Is this the folder with your "
                             "ripped discs?"))
            return
        readme = dicomdir.write_readme(self._out, result, self._source)

        # On an incremental update, offer to drop files left over from a
        # previous, larger build that the rebuild no longer produced.
        if self._update:
            after = self._snapshot(self._out)
            orphans = sorted(self._before - after)
            if orphans:
                choice = ask_three(
                    self.app.root, _("Leftover files found"),
                    _("This folder has {n} file(s) from a previous build that "
                      "aren't in the current archive. Keep them, or remove "
                      "them?").format(n=len(orphans)),
                    [(_("Keep them"), False), (_("Remove them"), True)],
                    cancel=False)
                if choice:
                    delivery_target.remove_orphans(self._out, orphans)

        # Stamp the marker so a later run recognizes this folder as a MIA
        # archive and offers to update it.
        try:
            delivery_target.write_marker(
                self._out, patient_name=None, patient_id=None, result=result)
        except OSError:
            pass

        self.set_status(_("Archive ready — {s} studies, {n} images.")
                        .format(s=result.studies, n=result.added))
        self.log_plain(_("✓ Archive complete: {s} studies, {n} images. "
                         "Copy this folder to the USB drive and hand it to the "
                         "doctor.").format(s=result.studies, n=result.added),
                       tag="done")
        self.log_technical(_("README: {p}").format(p=readme))
        reveal(os.path.join(self._out, "DICOMDIR"))
