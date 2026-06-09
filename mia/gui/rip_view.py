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

        self._session_open = False   # rip auto-loop open (idle-polls)
        self._working = False        # a disc/import actively running
        self.controller = RipSessionController(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state_changed=self._busy_state,
            on_session_changed=self._session_state, parent_widget=self)
        self._import_cancel = None

    def _start(self) -> None:
        self.controller.start()

    def _import_folder(self) -> None:
        self._import_cancel = import_flow.start_folder_import(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state=self._busy_state, parent=self)

    def _import_zip(self) -> None:
        self._import_cancel = import_flow.start_zip_import(
            self.app.root, self.panel, get_dest=self.dest.get,
            on_state=self._busy_state, parent=self)

    def _busy_state(self, running: bool) -> None:
        self._working = running
        self._sync()

    def _session_state(self, active: bool) -> None:
        self._session_open = active
        self._sync()

    def _sync(self) -> None:
        # Active = the auto-loop is open OR a job is running. Stop stays
        # available the whole time the session is open (even while idle-polling
        # between discs), so the user can always end it.
        active = self._session_open or self._working
        state = "disabled" if active else "normal"
        for btn in (self.start_btn, self.folder_btn, self.zip_btn):
            btn.configure(state=state)
        self.dest.set_enabled(not active)
        self.stop_btn.configure(state="normal" if active else "disabled")
        self.back_btn.configure(state="disabled" if active else "normal")

    def stop(self) -> None:
        self.controller.stop()
        if self._import_cancel is not None:
            self._import_cancel.set()
            self._import_cancel = None
