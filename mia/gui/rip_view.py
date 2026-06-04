"""Standalone Rip screen — a thin wrapper around RipSessionController."""

from __future__ import annotations

from tkinter import ttk

from .i18n import _
from .rip_session import RipSessionController
from .task_view import TaskView
from .widgets import FolderPicker, default_dir


class RipView(TaskView):
    title = _("Rip a CD")

    def build_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text=_(
            "Insert a CD. The app copies it to your computer, ejects it, and "
            "waits for the next one. Keep inserting discs — you don't need to "
            "restart between them.")
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.dest = FolderPicker(parent, _("Save copies to:"),
                                 default_dir("raw_discs"))
        self.dest.grid(row=1, column=0, sticky="ew")

        self.start_btn = ttk.Button(parent, text=_("Start ripping"),
                                    command=self._start)
        self.start_btn.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.controller = RipSessionController(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state_changed=self._state, parent_widget=self)

    def _start(self) -> None:
        self.controller.start()

    def _state(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.dest.set_enabled(not running)
        self.stop_btn.configure(state="normal" if running else "disabled")
        self.back_btn.configure(state="disabled" if running else "normal")

    def stop(self) -> None:
        self.controller.stop()
