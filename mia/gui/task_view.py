"""Reusable task screen: progress + verbose dual-log + run/stop machinery.

Subclasses add their own controls (folder pickers, primary buttons) into
``self.controls`` and call :meth:`start_job` with a worker thunk. The base owns
everything common: the status line, progress bar, stats row, the plain log, the
collapsible technical log, the session log file, and the Stop/Back buttons.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Any, Callable, Optional

from mia.core.common import Progress
from . import jobs
from .i18n import _
from .messages import Presenter, exception_detail, humanize_exception


def reveal(path: str) -> None:
    """Reveal a file/folder in the platform file manager (macOS for now)."""
    try:
        if sys.platform == "darwin":
            flag = "-R" if os.path.isfile(path) else None
            subprocess.run(["open"] + ([flag] if flag else []) + [path], check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", os.path.normpath(path)], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError:
        pass


def open_path(path: str) -> None:
    """Open a file with its default application (macOS for now)."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError:
        pass


class TaskView(ttk.Frame):
    title = "Task"

    def __init__(self, master: tk.Misc, app: Any) -> None:
        super().__init__(master, padding=16)
        self.app = app
        self.presenter = Presenter()
        self._cancel: Optional[Any] = None
        self._tech_lines: list[str] = []
        self._tech_visible = False
        self._logfile = None
        self._logfile_path: Optional[str] = None
        self._build_base_ui()
        self.build_controls(self.controls)

    # ----- UI construction ------------------------------------------------

    def _build_base_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)  # plain log grows

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        self.back_btn = ttk.Button(header, text=_("‹ Back"),
                                   command=self._on_back)
        self.back_btn.grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=self.title,
                  font=("", 16, "bold")).grid(row=0, column=1, sticky="w",
                                               padx=12)

        # Subclass controls (folder pickers, primary action button, etc.)
        self.controls = ttk.Frame(self)
        self.controls.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        self.controls.columnconfigure(0, weight=1)

        self.status = ttk.Label(self, text=_("Ready."), font=("", 12))
        self.status.grid(row=2, column=0, sticky="w")

        self.bar = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.bar.grid(row=3, column=0, sticky="ew", pady=(6, 2))

        self.stats = ttk.Label(self, text="", foreground="#555")
        self.stats.grid(row=4, column=0, sticky="w")

        # Plain log (always visible)
        plain_box = ttk.Frame(self)
        plain_box.grid(row=5, column=0, sticky="nsew", pady=(8, 4))
        plain_box.rowconfigure(0, weight=1)
        plain_box.columnconfigure(0, weight=1)
        self.plain_log = tk.Text(plain_box, height=10, wrap="word",
                                 state="disabled", relief="solid", borderwidth=1)
        self.plain_log.grid(row=0, column=0, sticky="nsew")
        psb = ttk.Scrollbar(plain_box, command=self.plain_log.yview)
        psb.grid(row=0, column=1, sticky="ns")
        self.plain_log.configure(yscrollcommand=psb.set)
        self.plain_log.tag_configure("fail", foreground="#b00020")
        self.plain_log.tag_configure("done", foreground="#0a7d28")

        # Technical disclosure
        self.tech_toggle = ttk.Button(self, text=_("▸ Show technical details"),
                                      command=self._toggle_tech)
        self.tech_toggle.grid(row=6, column=0, sticky="w")

        self.tech_box = ttk.Frame(self)
        self.tech_box.columnconfigure(0, weight=1)
        self.tech_box.rowconfigure(0, weight=1)
        self.tech_log = tk.Text(self.tech_box, height=8, wrap="none",
                                state="disabled", font=("Menlo", 10),
                                background="#1e1e1e", foreground="#d4d4d4")
        self.tech_log.grid(row=0, column=0, sticky="nsew")
        tsb = ttk.Scrollbar(self.tech_box, command=self.tech_log.yview)
        tsb.grid(row=0, column=1, sticky="ns")
        self.tech_log.configure(yscrollcommand=tsb.set)
        # tech_box gridded only when shown

        # Button row
        btns = ttk.Frame(self)
        btns.grid(row=8, column=0, sticky="ew", pady=(8, 0))
        self.stop_btn = ttk.Button(btns, text=_("Stop"), command=self.stop,
                                   state="disabled")
        self.stop_btn.pack(side="left")
        ttk.Button(btns, text=_("Save log…"),
                   command=self._save_log).pack(side="right")
        ttk.Button(btns, text=_("Open log folder"),
                   command=self._open_log).pack(side="right", padx=(0, 8))

    # ----- Hooks for subclasses ------------------------------------------

    def build_controls(self, parent: ttk.Frame) -> None:
        """Override to add task-specific widgets."""

    def on_running_changed(self, running: bool) -> None:
        """Override to enable/disable subclass-owned controls during a run."""

    # ----- Running a job --------------------------------------------------

    def start_job(
        self,
        work: jobs.Work,
        on_finish: Callable[[str, Any], None],
        log_dir: str,
    ) -> None:
        """Run ``work`` on a background thread, wiring events into this screen."""
        self._open_session_log(log_dir)
        self._set_running(True)
        self.set_indeterminate(False)

        def done(status: str, payload: Any) -> None:
            if status == "error":
                self.log_plain(humanize_exception(payload), tag="fail")
                self.log_technical(exception_detail(payload))
                self.set_status(_("Stopped on an error."))
            elif status == "cancelled":
                self.set_status(_("Stopped."))
                self.log_plain(_("Stopped by you."))
            self.set_indeterminate(False)
            self._set_running(False)
            self._close_session_log()
            on_finish(status, payload)

        self._cancel = jobs.run_job(self.app.root, work, self.on_event, done)

    def stop(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
            self.set_status(_("Stopping…"))
            self.stop_btn.configure(state="disabled")

    def on_event(self, p: Progress) -> None:
        # The DICOMDIR write is a single long blocking call with no per-file
        # progress; switch to an indeterminate "working" bar until it finishes.
        if p.kind == "info" and p.phase == "write":
            self.set_indeterminate(
                True, _("Writing the archive… this can take several minutes."))
            self.log_plain(_("Writing the archive now. This can take several "
                             "minutes — please wait…"))
            self.log_technical(p.note or "")
            return

        # Bar + stats update on every event (never throttled).
        if p.total:
            self.set_progress(p.done, p.total)
        if p.kind == "progress" or p.elapsed:
            self.set_stats(p)
        plain, technical = self.presenter.feed(p)
        if technical is not None:
            self.log_technical(technical)
        if plain is not None:
            tag = "fail" if p.kind == "fail" else None
            self.log_plain(plain, tag=tag)

    # ----- Widget helpers (UI thread only) -------------------------------

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def set_progress(self, done: int, total: int) -> None:
        if self.bar["mode"] != "determinate":
            self.bar.configure(mode="determinate")
        self.bar["maximum"] = 100
        self.bar["value"] = (100.0 * done / total) if total else 0

    def set_indeterminate(self, on: bool, text: Optional[str] = None) -> None:
        if on:
            self.bar.configure(mode="indeterminate")
            self.bar.start(12)
            if text:
                self.set_status(text)
        else:
            try:
                self.bar.stop()
            except tk.TclError:
                pass
            self.bar.configure(mode="determinate")

    def set_stats(self, p: Progress) -> None:
        from mia.core.common import format_duration
        parts = []
        if p.total:
            parts.append(_("files {done}/{total}").format(done=p.done, total=p.total))
        if p.elapsed:
            parts.append(_("elapsed {t}").format(t=format_duration(p.elapsed)))
        if p.eta and p.done != p.total:
            parts.append(_("ETA {t}").format(t=format_duration(p.eta)))
        if p.rate:
            parts.append(_("{r:.0f}/s").format(r=p.rate))
        self.stats.configure(text="   ".join(parts))

    def log_plain(self, line: str, tag: Optional[str] = None) -> None:
        self.plain_log.configure(state="normal")
        self.plain_log.insert("end", line + "\n", (tag,) if tag else ())
        self.plain_log.see("end")
        self.plain_log.configure(state="disabled")

    def log_technical(self, line: str) -> None:
        stamped = f"{time.strftime('%H:%M:%S')}  {line}"
        self._tech_lines.append(stamped)
        if self._logfile is not None:
            try:
                self._logfile.write(stamped + "\n")
                self._logfile.flush()
            except OSError:
                pass
        if self._tech_visible:
            self.tech_log.configure(state="normal")
            self.tech_log.insert("end", stamped + "\n")
            self.tech_log.see("end")
            self.tech_log.configure(state="disabled")

    # ----- Internal -------------------------------------------------------

    def _set_running(self, running: bool) -> None:
        self.stop_btn.configure(state="normal" if running else "disabled")
        self.back_btn.configure(state="disabled" if running else "normal")
        self.on_running_changed(running)

    def _toggle_tech(self) -> None:
        self._tech_visible = not self._tech_visible
        if self._tech_visible:
            self.rowconfigure(5, weight=1)
            self.rowconfigure(7, weight=1)
            self.tech_box.grid(row=7, column=0, sticky="nsew", pady=(0, 4))
            self.tech_toggle.configure(text=_("▾ Hide technical details"))
            # Populate from the in-memory buffer (kept even while hidden).
            self.tech_log.configure(state="normal")
            self.tech_log.delete("1.0", "end")
            self.tech_log.insert("end", "\n".join(self._tech_lines) + "\n")
            self.tech_log.see("end")
            self.tech_log.configure(state="disabled")
        else:
            self.tech_box.grid_remove()
            self.rowconfigure(7, weight=0)
            self.tech_toggle.configure(text=_("▸ Show technical details"))

    def _on_back(self) -> None:
        self.app.show_launcher()

    def _open_session_log(self, log_dir: str) -> None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        name = f"mia_session_{stamp}.log"
        for candidate in (log_dir, tempfile.gettempdir()):
            try:
                os.makedirs(candidate, exist_ok=True)
                path = os.path.join(candidate, name)
                self._logfile = open(path, "a", encoding="utf-8")
                self._logfile_path = path
                return
            except OSError:
                continue

    def _close_session_log(self) -> None:
        if self._logfile is not None:
            try:
                self._logfile.close()
            except OSError:
                pass
            self._logfile = None

    def _save_log(self) -> None:
        path = filedialog.asksaveasfilename(
            title=_("Save technical log"),
            defaultextension=".log",
            initialfile="mia_log.txt",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._tech_lines) + "\n")
            except OSError:
                pass

    def _open_log(self) -> None:
        if self._logfile_path and os.path.exists(self._logfile_path):
            reveal(self._logfile_path)
