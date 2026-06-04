"""Build inventory screen: pick a ripped folder, scan it, open the spreadsheet."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Any

from mia.core import inventory
from .i18n import N_, _
from .task_view import TaskView, open_path
from .widgets import FolderPicker, default_dir


class InventoryView(TaskView):
    title = N_("Build Inventory")

    def build_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text=_(
            "Pick the folder of ripped discs. A spreadsheet of every study "
            "will be created inside it and opened for you.")
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.folder = FolderPicker(parent, _("Ripped discs folder:"),
                                   default_dir("raw_discs"))
        self.folder.grid(row=1, column=0, sticky="ew")

        self.run_btn = ttk.Button(parent, text=_("Build inventory"),
                                  command=self._run)
        self.run_btn.grid(row=2, column=0, sticky="w", pady=(10, 0))

    def on_running_changed(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.run_btn.configure(state=state)
        self.folder.set_enabled(not running)

    def _run(self) -> None:
        folder = self.folder.get()
        if not os.path.isdir(folder):
            self.set_status(_("Please choose a valid folder first."))
            return
        out = os.path.join(folder, "dicom_inventory.xlsx")
        self.set_status(_("Scanning…"))
        self.log_plain(_("Looking through {f} for studies…").format(f=folder))

        def work(emit, cancel):
            return inventory.build_inventory(folder, out, progress=emit,
                                             cancel=cancel)

        self.start_job(work, self._finish, log_dir=folder)

    def _finish(self, status: str, result: Any) -> None:
        if status != "done":
            return
        if not result.studies:
            self.set_status(_("No DICOM studies found in that folder."))
            self.log_plain(_("No studies found. Is this the folder with your "
                             "ripped discs?"))
            return
        self.set_status(_("Done — {n} studies.").format(n=result.study_count))
        self.log_plain(_("✓ Found {n} studies. Opening the spreadsheet…")
                       .format(n=result.study_count), tag="done")
        if result.output_path:
            open_path(result.output_path)
