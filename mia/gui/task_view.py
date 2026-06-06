"""Reusable single-task screen: Back + controls + a ProgressLogPanel + Stop.

The verbose progress/log machinery now lives in
:class:`mia.gui.progress_panel.ProgressLogPanel`; this class wires it to a Back
button, subclass controls, the Stop button, and the background job runner. Its
public methods (``set_status``, ``log_plain``, ``on_event``, …) delegate to the
panel so the existing subclasses are unaffected.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from mia.core.common import Progress
from . import jobs
from .i18n import _
from .messages import exception_detail, humanize_exception
from .progress_panel import ProgressLogPanel
from .sysutil import open_path, reveal  # re-exported for the view modules


class TaskView(ttk.Frame):
    title = "Task"

    def __init__(self, master: tk.Misc, app: Any) -> None:
        super().__init__(master, padding=16)
        self.app = app
        self._cancel: Optional[Any] = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        self.back_btn = ttk.Button(header, text=_("‹ Back"),
                                   command=self._on_back)
        self.back_btn.grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=_(self.title),
                  font=("", 16, "bold")).grid(row=0, column=1, sticky="w",
                                              padx=12)

        self.controls = ttk.Frame(self)
        self.controls.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        self.controls.columnconfigure(0, weight=1)

        self.panel = ProgressLogPanel(self)
        self.panel.grid(row=2, column=0, sticky="nsew")

        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.stop_btn = ttk.Button(btns, text=_("Stop"), command=self.stop,
                                   state="disabled")
        self.stop_btn.pack(side="left")

        self.build_controls(self.controls)

    # ----- Hooks for subclasses ------------------------------------------

    def build_controls(self, parent: ttk.Frame) -> None:
        """Override to add task-specific widgets."""

    def on_running_changed(self, running: bool) -> None:
        """Override to enable/disable subclass-owned controls during a run."""

    # ----- Delegating helpers (used by subclasses) -----------------------

    def set_status(self, text: str) -> None:
        self.panel.set_status(text)

    def set_indeterminate(self, on: bool, text: Optional[str] = None) -> None:
        self.panel.set_indeterminate(on, text)

    def log_plain(self, line: str, tag: Optional[str] = None) -> None:
        self.panel.log_plain(line, tag=tag)

    def log_technical(self, line: str) -> None:
        self.panel.log_technical(line)

    def on_event(self, p: Progress) -> None:
        self.panel.on_event(p)

    # ----- Running a job --------------------------------------------------

    def start_job(self, work: jobs.Work,
                  on_finish: Callable[[str, Any], None], log_dir: str) -> None:
        self.panel.start_session_log(log_dir)
        self._set_running(True)
        self.panel.set_indeterminate(False)

        def done(status: str, payload: Any) -> None:
            if status == "error":
                self.log_plain(humanize_exception(payload), tag="fail")
                self.log_technical(exception_detail(payload))
                self.set_status(_("Stopped on an error."))
            elif status == "cancelled":
                self.set_status(_("Stopped."))
                self.log_plain(_("Stopped by you."))
            self.panel.set_indeterminate(False)
            self._set_running(False)
            self.panel.close_session_log()
            on_finish(status, payload)

        self._cancel = jobs.run_job(self.app.root, work, self.panel.on_event,
                                    done)

    def is_busy(self) -> bool:
        """True while a job/session runs (the Stop button is the single source
        of truth across all subclasses, including controller-driven ones)."""
        return str(self.stop_btn.cget("state")) == "normal"

    def stop(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
            self.set_status(_("Stopping…"))
            self.stop_btn.configure(state="disabled")

    # ----- Internal -------------------------------------------------------

    def _set_running(self, running: bool) -> None:
        self.stop_btn.configure(state="normal" if running else "disabled")
        self.back_btn.configure(state="disabled" if running else "normal")
        self.on_running_changed(running)

    def _on_back(self) -> None:
        self.app.show_launcher()
