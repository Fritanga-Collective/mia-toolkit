"""Reusable verbose progress + dual-log panel.

Embedded by both the individual task screens (`TaskView`) and the wizard steps.
It owns everything to do with showing progress and giving the user certainty:
the status line, the progress bar (determinate + indeterminate), the stats row,
the always-visible plain-language log, the collapsible technical log, and the
timestamped session log file. It only updates widgets — threading lives in
`jobs` and the owning view.
"""

from __future__ import annotations

import os
import tempfile
import time
import tkinter as tk
from tkinter import filedialog, ttk
from typing import Optional

from mia.core.common import Progress, format_duration
from .i18n import _
from .messages import Presenter
from .sysutil import reveal

# Braille "working" frames (like Claude Code's). They render on the system
# fonts of macOS/Windows/Linux; the panel falls back to nothing fancy if Tk
# can't schedule (headless).
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class ProgressLogPanel(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.presenter = Presenter()
        self._tech_lines: list[str] = []
        self._tech_visible = False
        self._logfile = None
        self._logfile_path: Optional[str] = None
        # Working-spinner state (animates the status line while a session runs).
        self._base_status = _("Ready.")
        self._spinning = False
        self._spin_i = 0
        self._spin_job: Optional[str] = None
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self.status = ttk.Label(self, text=_("Ready."), font=("", 12))
        self.status.grid(row=0, column=0, sticky="w")

        self.bar = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.bar.grid(row=1, column=0, sticky="ew", pady=(6, 2))

        self.stats = ttk.Label(self, text="", foreground="#555")
        self.stats.grid(row=2, column=0, sticky="w")

        plain_box = ttk.Frame(self)
        plain_box.grid(row=3, column=0, sticky="nsew", pady=(8, 4))
        plain_box.rowconfigure(0, weight=1)
        plain_box.columnconfigure(0, weight=1)
        self.plain_log = tk.Text(plain_box, height=9, wrap="word",
                                 state="disabled", relief="solid", borderwidth=1)
        self.plain_log.grid(row=0, column=0, sticky="nsew")
        psb = ttk.Scrollbar(plain_box, command=self.plain_log.yview)
        psb.grid(row=0, column=1, sticky="ns")
        self.plain_log.configure(yscrollcommand=psb.set)
        self.plain_log.tag_configure("fail", foreground="#b00020")
        self.plain_log.tag_configure("done", foreground="#0a7d28")

        self.tech_toggle = ttk.Button(self, text=_("▸ Show technical details"),
                                      command=self._toggle_tech)
        self.tech_toggle.grid(row=4, column=0, sticky="w")

        self.tech_box = ttk.Frame(self)
        self.tech_box.columnconfigure(0, weight=1)
        self.tech_box.rowconfigure(0, weight=1)
        self.tech_log = tk.Text(self.tech_box, height=7, wrap="none",
                                state="disabled", font=("Menlo", 10),
                                background="#1e1e1e", foreground="#d4d4d4")
        self.tech_log.grid(row=0, column=0, sticky="nsew")
        tsb = ttk.Scrollbar(self.tech_box, command=self.tech_log.yview)
        tsb.grid(row=0, column=1, sticky="ns")
        self.tech_log.configure(yscrollcommand=tsb.set)

        logbtns = ttk.Frame(self)
        logbtns.grid(row=6, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(logbtns, text=_("Save log…"),
                   command=self._save_log).pack(side="right")
        ttk.Button(logbtns, text=_("Open log folder"),
                   command=self._open_log).pack(side="right", padx=(0, 8))
        # Report a problem: an anonymized, user-reviewed diagnostic report
        # built from this session's technical log (no auto-collection).
        ttk.Button(logbtns, text=_("Report a problem…"),
                   command=self._report_problem).pack(side="left")

    # ----- Event handling -------------------------------------------------

    def on_event(self, p: Progress) -> None:
        # Verbose timing/per-file notes go straight to the technical pane,
        # never the plain log. Workers emit these when common.is_verbose()
        # (on by default — captured here but only shown when the user expands
        # "technical details").
        if p.kind == "debug":
            self.log_technical(p.note or "")
            return

        # The DICOMDIR write is one long blocking call with no per-file
        # progress; switch to an indeterminate "working" bar until it finishes.
        if p.kind == "info" and p.phase == "write":
            self.set_indeterminate(
                True, _("Writing the archive… this can take several minutes."))
            self.log_plain(_("Writing the archive now. This can take several "
                             "minutes — please wait…"))
            self.log_technical(p.note or "")
            return

        # An opaque "working" phase (e.g. the native USB bulk copy): no honest
        # done/total ratio, so show an animated bar + elapsed, never a fake ETA.
        if p.indeterminate:
            if str(self.bar["mode"]) != "indeterminate":
                self.set_indeterminate(True)
            self.set_status(self._copy_status(p))
            return

        if p.total:
            # Leaving an indeterminate phase (e.g. native copy → verify pass):
            # stop the animation before driving the real determinate bar.
            if str(self.bar["mode"]) == "indeterminate":
                self.set_indeterminate(False)
            self.set_progress(p.done, p.total)
        if p.kind == "progress" or p.elapsed:
            self.set_stats(p)
        plain, technical = self.presenter.feed(p)
        if technical is not None:
            self.log_technical(technical)
        if plain is not None:
            self.log_plain(plain, tag="fail" if p.kind == "fail" else None)

    def _copy_status(self, p: Progress) -> str:
        """Localized status for the indeterminate native-copy phase."""
        mins = p.elapsed / 60.0
        if mins >= 1:
            return _("Copying {n} files… ({m:.0f}m elapsed)").format(
                n=p.total, m=mins)
        return _("Copying {n} files…").format(n=p.total)

    # ----- Widget helpers -------------------------------------------------

    def set_status(self, text: str) -> None:
        # Keep the base text separate so the spinner can prefix a frame without
        # the frames accumulating across updates.
        self._base_status = text
        self._render_status()

    # ----- Working spinner ------------------------------------------------

    def _render_status(self) -> None:
        if self._spinning and self._base_status:
            frame = _SPINNER[self._spin_i % len(_SPINNER)]
            self.status.configure(text=f"{frame}  {self._base_status}")
        else:
            self.status.configure(text=self._base_status)

    def _spin_tick(self) -> None:
        if not self._spinning:
            return
        self._spin_i += 1
        self._render_status()
        try:
            self._spin_job = self.after(120, self._spin_tick)
        except tk.TclError:
            self._spin_job = None

    def _start_spinner(self) -> None:
        if self._spinning:
            return
        self._spinning = True
        self._spin_i = 0
        self._render_status()
        try:
            self._spin_job = self.after(120, self._spin_tick)
        except tk.TclError:
            self._spin_job = None  # headless / no event loop — status still set

    def _stop_spinner(self) -> None:
        self._spinning = False
        if self._spin_job is not None:
            try:
                self.after_cancel(self._spin_job)
            except tk.TclError:
                pass
            self._spin_job = None
        self._render_status()

    def set_progress(self, done: int, total: int) -> None:
        if str(self.bar["mode"]) != "determinate":
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
        parts = []
        if p.total:
            parts.append(_("files {done}/{total}").format(done=p.done,
                                                           total=p.total))
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

    # ----- Session log file ----------------------------------------------

    def start_session_log(self, log_dir: str,
                          busy_label: Optional[str] = None) -> None:
        # Animate the "working" spinner for the whole session so the user knows
        # to wait (covers rip, import, inventory, build, delivery — they all
        # bracket their work with start/close_session_log). The busy label sits
        # beside the spinner so it reads e.g. "⠹  Copy in progress…" rather than
        # the idle "Ready.".
        self._start_spinner()
        if busy_label:
            self.set_status(busy_label)
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

    def close_session_log(self, done_label: Optional[str] = None) -> None:
        self._stop_spinner()
        if done_label:
            self.set_status(done_label)   # e.g. "Copy complete." (spinner gone)
        if self._logfile is not None:
            try:
                self._logfile.close()
            except OSError:
                pass
            self._logfile = None

    # ----- Internal -------------------------------------------------------

    def _report_problem(self) -> None:
        from .report import open_report_dialog
        open_report_dialog(self, list(self._tech_lines))

    def _toggle_tech(self) -> None:
        self._tech_visible = not self._tech_visible
        if self._tech_visible:
            self.rowconfigure(3, weight=1)
            self.rowconfigure(5, weight=1)
            self.tech_box.grid(row=5, column=0, sticky="nsew", pady=(0, 4))
            self.tech_toggle.configure(text=_("▾ Hide technical details"))
            self.tech_log.configure(state="normal")
            self.tech_log.delete("1.0", "end")
            self.tech_log.insert("end", "\n".join(self._tech_lines) + "\n")
            self.tech_log.see("end")
            self.tech_log.configure(state="disabled")
        else:
            self.tech_box.grid_remove()
            self.rowconfigure(5, weight=0)
            self.tech_toggle.configure(text=_("▸ Show technical details"))

    def _save_log(self) -> None:
        path = filedialog.asksaveasfilename(
            title=_("Save technical log"), defaultextension=".log",
            initialfile="mia_log.txt")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(self._tech_lines) + "\n")
            except OSError:
                pass

    def _open_log(self) -> None:
        if self._logfile_path and os.path.exists(self._logfile_path):
            reveal(self._logfile_path)
