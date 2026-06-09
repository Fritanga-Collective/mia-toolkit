"""Auto-looping ripping session, decoupled from any one screen.

Drives a :class:`ProgressLogPanel`: poll for an inserted disc, rip it on the
worker thread, eject, wait for the next — no relaunch. Used by both the
standalone Rip screen and the wizard's Rip step. Stop aborts an in-flight disc
(the core's resume-on-rerun makes that safe).
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional

from tkinter import messagebox

from mia.core import ripper, sources
from . import jobs
from .i18n import _
from .messages import exception_detail, humanize_exception


class RipSessionController:
    POLL_MS = 1500

    def __init__(self, root: Any, panel: Any, *,
                 get_dest: Callable[[], str],
                 on_state_changed: Optional[Callable[[bool], None]] = None,
                 on_session_changed: Optional[Callable[[bool], None]] = None,
                 on_disc: Optional[Callable[[Any], None]] = None,
                 parent_widget: Optional[tk.Misc] = None) -> None:
        self.root = root
        self.panel = panel
        self._get_dest = get_dest
        # on_state_changed → "a disc is actively copying" (drives wizard busy /
        # Next gating). on_session_changed → "the auto-loop is open" (drives the
        # tool's Stop button and the source buttons). They are NOT the same: the
        # session idles between discs, when it is open but not busy.
        self._on_state = on_state_changed or (lambda running: None)
        self._on_session = on_session_changed or (lambda active: None)
        self._on_disc = on_disc or (lambda result: None)
        self._parent = parent_widget or root
        self._session = False
        self._busy = False
        self._cancel = None
        self._last_ripped: Optional[str] = None
        self._prompted: set = set()   # USBs we've already asked about (session)
        self._current_src: Optional[str] = None
        self._dest: Optional[str] = None
        self.count = 0

    @property
    def active(self) -> bool:
        return self._session

    # ----- lifecycle ------------------------------------------------------

    def start(self) -> bool:
        dest = self._get_dest()
        if not dest:
            self.panel.set_status(_("Please choose a folder to save copies to."))
            return False
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError:
            self.panel.set_status(_("Couldn't create that folder. Choose another."))
            return False
        self._dest = dest
        self._session = True
        self.count = 0
        self._last_ripped = None
        self._prompted = set()
        self.panel.start_session_log(dest)
        self._on_session(True)   # session open (not "busy" — it idle-polls)
        self.panel.set_status(_("Insert a disc…"))
        self.panel.log_plain(_("Ripping session started. Insert your first disc."))
        self.root.after(self.POLL_MS, self._poll)
        return True

    def stop(self) -> None:
        self._session = False
        if self._cancel is not None:
            self._cancel.set()
            self.panel.set_status(_("Stopping…"))
        else:
            self._end()

    def _end(self) -> None:
        self._session = False
        self._busy = False
        self._cancel = None
        self._on_state(False)
        self._on_session(False)
        self.panel.close_session_log()
        self.panel.set_indeterminate(False)
        self.panel.set_status(_("Ripping session ended. {n} disc(s) copied.")
                              .format(n=self.count))

    # ----- the poll/rip loop ---------------------------------------------

    def _poll(self) -> None:
        if not self._session or self._busy:
            return
        candidates = ripper.detect_mounted_cds()
        if self._last_ripped and self._last_ripped not in candidates:
            self._last_ripped = None
        candidates = [c for c in candidates if c != self._last_ripped]

        # The hands-free loop auto-rips only real optical discs. A plugged USB
        # is NOT silently ripped — it gets a one-time prompt (the user normally
        # imports a USB via the explicit "From a folder or USB" button).
        optical = [c for c in candidates if ripper.is_optical(c)]
        usb = [c for c in candidates
               if c not in optical and c not in self._prompted]

        src = None
        if len(optical) > 1:
            src = self._choose(optical)
        elif optical:
            src = optical[0]
        elif usb:
            src = self._prompt_usb(usb[0])  # ask before touching a USB

        if not src:
            self.panel.set_status(_("Insert a disc… (waiting)"))
            self.root.after(self.POLL_MS, self._poll)
            return
        # Already-imported guard (both optical and accepted USB): always ask.
        if sources.looks_already_imported(src, self._dest):
            name = os.path.basename(src.rstrip("/")) or src
            if not messagebox.askyesno(
                    _("Already added"),
                    _("“{name}” looks already added. Copy again?")
                    .format(name=name), default="no", parent=self._parent):
                self._last_ripped = src           # don't re-grab this poll
                self.panel.log_plain(
                    _("Already added — skipping “{name}”.").format(name=name))
                self.root.after(self.POLL_MS, self._poll)
                return
        self._rip_one(src)

    def _prompt_usb(self, mount: str) -> Optional[str]:
        """Ask once whether to copy a detected USB drive. Returns it if yes."""
        self._prompted.add(mount)
        name = os.path.basename(mount.rstrip("/")) or mount
        if messagebox.askyesno(
                _("Copy this drive?"),
                _("Copy this drive “{name}”?").format(name=name),
                default="no", parent=self._parent):  # Enter = the safe "No"
            return mount
        return None

    def _rip_one(self, src: str) -> None:
        self._busy = True
        self._on_state(True)   # actively copying → wizard busy / Next blocked
        self._current_src = src
        name = os.path.basename(src.rstrip("/")) or src
        num = ripper.next_disc_number(self._dest)
        self.panel.set_status(_("Ripping disc {n}: {name}…").format(n=num, name=name))
        self.panel.log_plain(_("Found disc “{name}”. Copying…").format(name=name))

        def work(emit, cancel):
            return ripper.rip_disc(src, self._dest, num, progress=emit,
                                   cancel=cancel)

        self._cancel = jobs.run_job(self.root, work, self.panel.on_event,
                                    self._done)

    def _done(self, status: str, result) -> None:
        src = self._current_src
        self._cancel = None
        self._busy = False
        self._on_state(False)   # done copying → idle; wizard Next re-enabled
        self.panel.set_indeterminate(False)

        if status == "cancelled":
            self.panel.log_plain(_("Stopped."))
            self._end()
            return
        if status == "error":
            self.panel.log_plain(humanize_exception(result), tag="fail")
            self.panel.log_technical(exception_detail(result))
            self.panel.set_status(_("Couldn't rip this disc. Remove it and "
                                    "insert another, or press Stop."))
        else:
            self.count += 1
            ok = result.failed == 0
            self.panel.log_plain(
                _("✓ Disc copied: {c} files OK, {r} recovered, {f} could not "
                  "be read.").format(c=result.copied, r=len(result.retry_notes),
                                     f=result.failed),
                tag="done" if ok else "fail")
            sources.record_study_uids(result.disc_dir, result.manifest_path)
            if src:
                ripper.eject_macos(src)
                self._last_ripped = src
            self.panel.set_status(_("✓ Disc {n} done. Insert the next disc…")
                                  .format(n=self.count))
            self._on_disc(result)

        if self._session:
            self.root.after(self.POLL_MS, self._poll)

    def _choose(self, candidates):
        top = tk.Toplevel(self._parent)
        top.title(_("Choose a disc"))
        top.transient(self._parent)
        top.grab_set()
        ttk.Label(top, padding=12, text=_(
            "More than one drive looks like a disc. Which one should I copy?")
        ).pack()
        var = tk.StringVar(value=candidates[0])
        for c in candidates:
            ttk.Radiobutton(top, text=c, value=c, variable=var).pack(
                anchor="w", padx=16)
        result = {"v": None}

        def ok():
            result["v"] = var.get()
            top.destroy()

        row = ttk.Frame(top, padding=12)
        row.pack()
        ttk.Button(row, text=_("Rip this one"), command=ok).pack(side="left",
                                                                 padx=6)
        ttk.Button(row, text=_("Skip for now"),
                   command=top.destroy).pack(side="left", padx=6)
        self.root.wait_window(top)
        return result["v"]
