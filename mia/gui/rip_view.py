"""Standalone Add Your Studies screen — disc ripping plus local imports."""

from __future__ import annotations

from tkinter import ttk

from . import import_flow
from .i18n import N_, _
from .rip_session import RipSessionController
from .task_view import TaskView
from .widgets import FolderPicker, default_dir


class RipView(TaskView):
    title = N_("Add Your Studies")

    def build_controls(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, wraplength=580, justify="left", text=_(
            "Insert a CD — it copies and ejects automatically. You can also "
            "add studies from a USB drive, a folder, or a downloaded ZIP.")
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.dest = FolderPicker(parent, _("Save copies to:"),
                                 default_dir("raw_discs"))
        self.dest.grid(row=1, column=0, sticky="ew")

        # Emoji kept outside the translatable strings (language-neutral).
        btns = ttk.Frame(parent)
        btns.grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.start_btn = ttk.Button(btns, text=f"💿  {_('Start ripping')}",
                                    command=self._start)
        self.start_btn.pack(side="left")
        self.folder_btn = ttk.Button(
            btns, text=f"📁  {_('From a folder or USB')}",
            command=self._import_folder)
        self.folder_btn.pack(side="left", padx=(8, 0))
        self.zip_btn = ttk.Button(btns, text=f"🗄  {_('From a ZIP file')}",
                                  command=self._import_zip)
        self.zip_btn.pack(side="left", padx=(8, 0))

        self.controller = RipSessionController(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state_changed=self._state, parent_widget=self)
        self._import_cancel = None

    def _start(self) -> None:
        self.controller.start()

    def _import_folder(self) -> None:
        self._import_cancel = import_flow.start_folder_import(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state=self._state, parent=self)

    def _import_zip(self) -> None:
        self._import_cancel = import_flow.start_zip_import(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state=self._state, parent=self)

    def _state(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        for btn in (self.start_btn, self.folder_btn, self.zip_btn):
            btn.configure(state=state)
        self.dest.set_enabled(not running)
        self.stop_btn.configure(state="normal" if running else "disabled")
        self.back_btn.configure(state="disabled" if running else "normal")

    def stop(self) -> None:
        self.controller.stop()
        if self._import_cancel is not None:
            self._import_cancel.set()
            self._import_cancel = None
