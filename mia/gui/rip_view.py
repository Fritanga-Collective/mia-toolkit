"""Rip screen: an auto-looping ripping *session*.

The user clicks "Start ripping" once. From then on the app polls for an inserted
disc, rips it on the worker thread, ejects it, and waits for the next — no
relaunch, minimal clicking. "Stop" ends the session (and aborts an in-flight
disc; the core's resume-on-rerun makes that safe).
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

from mia.core import ripper
from . import jobs
from .i18n import _
from .messages import exception_detail, humanize_exception
from .task_view import TaskView
from .widgets import FolderPicker, default_dir


class RipView(TaskView):
    title = _("Rip a CD")
    POLL_MS = 1500

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
                                    command=self._start_session)
        self.start_btn.grid(row=2, column=0, sticky="w", pady=(10, 0))

        # Session state
        self._session = False
        self._busy = False
        self._last_ripped = None
        self._current_src = None
        self._dest = None
        self._count = 0

    def on_running_changed(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.dest.set_enabled(not running)

    # ----- Session lifecycle ---------------------------------------------

    def _start_session(self) -> None:
        dest = self.dest.get()
        if not dest:
            self.set_status(_("Please choose a folder to save copies to."))
            return
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError:
            self.set_status(_("Couldn't create that folder. Choose another."))
            return
        self._dest = dest
        self._session = True
        self._count = 0
        self._last_ripped = None
        self._open_session_log(dest)
        self._set_running(True)
        self.set_status(_("Insert a disc…"))
        self.log_plain(_("Ripping session started. Insert your first disc."))
        self.app.root.after(self.POLL_MS, self._poll)

    def stop(self) -> None:
        self._session = False
        if self._cancel is not None:
            self._cancel.set()  # abort the disc currently being ripped
            self.set_status(_("Stopping…"))
            self.stop_btn.configure(state="disabled")
        else:
            self._end_session()

    def _end_session(self) -> None:
        self._session = False
        self._busy = False
        self._cancel = None
        self._set_running(False)
        self._close_session_log()
        self.set_indeterminate(False)
        self.set_status(_("Ripping session ended. {n} disc(s) copied.")
                        .format(n=self._count))

    # ----- The poll/rip loop ---------------------------------------------

    def _poll(self) -> None:
        if not self._session or self._busy:
            return

        candidates = ripper.detect_mounted_cds()
        if self._last_ripped and self._last_ripped not in candidates:
            self._last_ripped = None  # the disc was removed; forget it
        candidates = [c for c in candidates if c != self._last_ripped]

        if not candidates:
            self.set_status(_("Insert a disc… (waiting)"))
            self.app.root.after(self.POLL_MS, self._poll)
            return

        if len(candidates) > 1:
            src = self._choose_candidate(candidates)
            if not src:
                self.app.root.after(self.POLL_MS, self._poll)
                return
        else:
            src = candidates[0]

        self._rip_one(src)

    def _rip_one(self, src: str) -> None:
        self._busy = True
        self._current_src = src
        name = os.path.basename(src.rstrip("/")) or src
        num = ripper.next_disc_number(self._dest)
        self.set_status(_("Ripping disc {n}: {name}…").format(n=num, name=name))
        self.log_plain(_("Found disc “{name}”. Copying…").format(name=name))

        def work(emit, cancel):
            return ripper.rip_disc(src, self._dest, num, progress=emit,
                                   cancel=cancel)

        self._cancel = jobs.run_job(self.app.root, work, self.on_event,
                                    self._disc_done)

    def _disc_done(self, status: str, result) -> None:
        src = self._current_src
        self._cancel = None
        self._busy = False
        self.set_indeterminate(False)

        if status == "cancelled":
            self.log_plain(_("Stopped."))
            self._end_session()
            return

        if status == "error":
            self.log_plain(humanize_exception(result), tag="fail")
            self.log_technical(exception_detail(result))
            self.set_status(_("Couldn't rip this disc. Remove it and insert "
                              "another, or press Stop."))
        else:
            self._count += 1
            ok = result.failed == 0
            self.log_plain(
                _("✓ Disc copied: {c} files OK, {r} recovered, {f} could not "
                  "be read.").format(c=result.copied, r=len(result.retry_notes),
                                     f=result.failed),
                tag="done" if ok else "fail")
            if src:
                ripper.eject_macos(src)
                self._last_ripped = src
            self.set_status(_("✓ Disc {n} done. Insert the next disc…")
                            .format(n=self._count))

        if self._session:
            self.app.root.after(self.POLL_MS, self._poll)

    def _choose_candidate(self, candidates):
        """Modal chooser when more than one volume looks like a disc."""
        top = tk.Toplevel(self)
        top.title(_("Choose a disc"))
        top.transient(self.app.root)
        top.grab_set()
        ttk.Label(top, padding=12, text=_(
            "More than one drive looks like a disc. Which one should I copy?")
        ).pack()
        var = tk.StringVar(value=candidates[0])
        for c in candidates:
            ttk.Radiobutton(top, text=c, value=c,
                            variable=var).pack(anchor="w", padx=16)
        result = {"v": None}

        def ok():
            result["v"] = var.get()
            top.destroy()

        def skip():
            top.destroy()

        row = ttk.Frame(top, padding=12)
        row.pack()
        ttk.Button(row, text=_("Rip this one"), command=ok).pack(side="left",
                                                                 padx=6)
        ttk.Button(row, text=_("Skip for now"), command=skip).pack(side="left",
                                                                   padx=6)
        self.app.root.wait_window(top)
        return result["v"]
