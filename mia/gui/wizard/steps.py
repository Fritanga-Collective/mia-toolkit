"""The five wizard steps. Panel-bearing steps reuse ProgressLogPanel + jobs."""

from __future__ import annotations

import os
import shutil
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

# The tool and its installers are free. This opens the support page in the
# user's browser (the only outbound link in the app — no telemetry, no calls).
SUPPORT_URL = "https://mia-toolkit.fritanga.co/support.html"

from mia.core import deliver, dicomdir, inventory
from mia.core.common import format_bytes
from mia.core.ripper import copy_with_retry

from ..i18n import _
from ..jobs import run_job
from ..messages import exception_detail, humanize_exception
from ..progress_panel import ProgressLogPanel
from ..rip_session import RipSessionController
from ..sysutil import open_path, reveal


class WizardStep(ttk.Frame):
    def __init__(self, master: tk.Misc, wizard) -> None:
        super().__init__(master, padding=4)
        self.wizard = wizard
        self.project = wizard.project
        self.columnconfigure(0, weight=1)
        self.build()

    def build(self) -> None: ...
    def enter(self) -> None: ...
    def on_leave(self) -> None: ...
    def can_advance(self) -> bool:
        return True


class PanelStep(WizardStep):
    """A step that runs core workers and shows their progress."""

    def build_panel(self, row: int) -> None:
        self.panel = ProgressLogPanel(self)
        self.panel.grid(row=row, column=0, sticky="nsew")
        self.rowconfigure(row, weight=1)
        self._cancel = None

    def run_job(self, work, on_finish, log_dir: str) -> None:
        self.wizard.set_busy(True)
        self.panel.start_session_log(log_dir)

        def done(status, payload):
            if status == "error":
                self.panel.log_plain(humanize_exception(payload), tag="fail")
                self.panel.log_technical(exception_detail(payload))
            self.panel.set_indeterminate(False)
            self.panel.close_session_log()
            self.wizard.set_busy(False)
            on_finish(status, payload)

        self._cancel = run_job(self.wizard.app.root, work, self.panel.on_event,
                               done)

    def guard_space(self, need_bytes: int, on_ready) -> None:
        """Run on_ready if the project drive has room; else offer to relocate."""
        if self.project.free_space() >= int(need_bytes * 1.1):
            on_ready()
            return
        if not messagebox.askyesno(
                _("Not enough space"),
                _("This drive may not have enough room (need about {n}). Move "
                  "your project to another drive with more space?")
                .format(n=format_bytes(need_bytes))):
            self.panel.set_status(_("Cancelled — not enough space."))
            return
        new_root = filedialog.askdirectory(
            title=_("Choose a drive or folder with more space"))
        if not new_root:
            self.panel.set_status(_("Cancelled."))
            return

        def work(emit, cancel):
            return self.project.relocate(new_root, progress=emit, cancel=cancel)

        def fin(status, payload):
            if status == "done":
                on_ready()
            else:
                self.panel.log_plain(
                    _("Could not move the project. Try another drive."),
                    tag="fail")

        self.run_job(work, fin, self.project.root)


class WelcomeStep(WizardStep):
    def build(self) -> None:
        ttk.Label(self, text=_("This will help you, step by step:"),
                  font=("", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(self, justify="left", text=_(
            "1.  Copy your CDs onto this computer\n"
            "2.  Review everything we found\n"
            "3.  Build one archive and copy it to a USB drive for your doctor")
        ).grid(row=1, column=0, sticky="w", pady=(6, 16))
        self.resume_lbl = ttk.Label(self, foreground="#0a7d28", text="")
        self.resume_lbl.grid(row=2, column=0, sticky="w")
        self.skip_btn = ttk.Button(self, text=_("Skip to building the archive"),
                                   command=lambda: self.wizard.goto(3))

    def enter(self) -> None:
        n = self.project.disc_count()
        if n > 0:
            self.resume_lbl.configure(
                text=_("Welcome back — you already have {n} disc(s) copied. "
                       "Continue with Next, or:").format(n=n))
            self.skip_btn.grid(row=3, column=0, sticky="w", pady=(6, 0))
        else:
            self.resume_lbl.configure(text="")
            self.skip_btn.grid_remove()


class RipStep(PanelStep):
    def build(self) -> None:
        ttk.Label(self, wraplength=580, justify="left", text=_(
            "Insert each CD. It copies onto your computer, ejects, and waits "
            "for the next one. When you've done all your discs, click Next.")
        ).grid(row=0, column=0, sticky="w")
        self.start_btn = ttk.Button(self, text=_("Start ripping"),
                                    command=self._start)
        self.start_btn.grid(row=1, column=0, sticky="w", pady=(8, 8))
        self.build_panel(2)
        self.controller = RipSessionController(
            self.wizard.app.root, self.panel,
            get_dest=lambda: self.project.raw_discs_dir,
            on_state_changed=self._state,
            on_disc=lambda r: self.wizard.refresh_nav(),
            parent_widget=self)

    def enter(self) -> None:
        self.panel.set_status(
            _("Ready. Insert a disc, then click Start ripping."))

    def _start(self) -> None:
        self.guard_space(1_000_000_000, self._begin)  # ~1 GB headroom

    def _begin(self) -> None:
        self.project.ensure_dirs()
        self.controller.start()

    def _state(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.wizard.set_busy(running)

    def on_leave(self) -> None:
        if self.controller.active:
            self.controller.stop()


class InventoryStep(PanelStep):
    def build(self) -> None:
        self.info = ttk.Label(self, text="", wraplength=580, justify="left")
        self.info.grid(row=0, column=0, sticky="w")
        self.warn = ttk.Label(self, text="", foreground="#b00020",
                              wraplength=580, justify="left")
        self.warn.grid(row=1, column=0, sticky="w")
        bar = ttk.Frame(self)
        bar.grid(row=2, column=0, sticky="w", pady=(8, 8))
        self.rescan_btn = ttk.Button(bar, text=_("Re-scan"), command=self._scan)
        self.rescan_btn.pack(side="left")
        self.open_btn = ttk.Button(bar, text=_("Open spreadsheet"),
                                   command=self._open, state="disabled")
        self.open_btn.pack(side="left", padx=(8, 0))
        self.build_panel(3)
        self._scanned = False

    def enter(self) -> None:
        if not self.project.has_discs():
            self.info.configure(
                text=_("No discs copied yet — you can skip this step."))
            self.rescan_btn.configure(state="disabled")
            return
        self.rescan_btn.configure(state="normal")
        if not self._scanned:
            self._scan()

    def _scan(self) -> None:
        self.info.configure(text=_("Looking through your discs…"))
        self.warn.configure(text="")
        self.open_btn.configure(state="disabled")

        def work(emit, cancel):
            return inventory.build_inventory(
                self.project.raw_discs_dir, self.project.inventory_path,
                progress=emit, cancel=cancel)

        self.run_job(work, self._done, self.project.root)

    def _done(self, status, result) -> None:
        if status != "done" or result is None:
            return
        self._scanned = True
        self.info.configure(
            text=_("We found {n} studies across your discs.")
            .format(n=result.study_count))
        self.open_btn.configure(
            state="normal" if result.output_path else "disabled")
        ids = {s["patient_id"] for s in result.studies.values()
               if s.get("patient_id")}
        names = {s["patient_name"] for s in result.studies.values()
                 if s.get("patient_name")}
        if len(ids) > 1 or len(names) > 1:
            self.warn.configure(text=_(
                "⚠ More than one patient appears across these discs. Open the "
                "spreadsheet's ‘Consistency Check’ to be sure a stranger's disc "
                "wasn't mixed in (often it's just the same person registered "
                "differently)."))

    def _open(self) -> None:
        if os.path.exists(self.project.inventory_path):
            open_path(self.project.inventory_path)


class ArchiveStep(PanelStep):
    def build(self) -> None:
        self.info = ttk.Label(self, text="", wraplength=580, justify="left")
        self.info.grid(row=0, column=0, sticky="w")
        bar = ttk.Frame(self)
        bar.grid(row=1, column=0, sticky="w", pady=(8, 8))
        self.build_btn = ttk.Button(bar, text=_("Build the archive"),
                                    command=self._build)
        self.build_btn.pack(side="left")
        self.usb_btn = ttk.Button(bar, text=_("Choose USB & copy"),
                                  command=self._deliver, state="disabled")
        self.usb_btn.pack(side="left", padx=(8, 0))
        self.build_panel(2)

    def enter(self) -> None:
        if not self.project.has_discs():
            self.info.configure(text=_(
                "No discs to build from. Go back and rip some discs first."))
            self.build_btn.configure(state="disabled")
            return
        self.build_btn.configure(state="normal")
        if self.project.has_archive():
            self.info.configure(text=_(
                "Archive already built. Choose a USB drive to copy it to."))
            self.usb_btn.configure(state="normal")
        else:
            self.info.configure(
                text=_("Ready to combine your discs into one archive."))

    def _build(self) -> None:
        self.guard_space(max(self.project.raw_size(), 1), self._do_build)

    def _do_build(self) -> None:
        out = self.project.archive_dir
        if os.path.exists(out) and not self.project.has_archive():
            # A leftover partial build inside our managed folder — safe to clear.
            shutil.rmtree(out, ignore_errors=True)
        if self.project.has_archive():
            self._build_done("done", None)
            return

        def work(emit, cancel):
            return dicomdir.build_fileset(self.project.raw_discs_dir, out,
                                          progress=emit, cancel=cancel)

        self.run_job(work, self._build_done, self.project.root)

    def _build_done(self, status, result) -> None:
        if status != "done":
            return
        if result is not None:
            self.wizard.archive_result = result
            self.info.configure(text=_(
                "Archive built: {s} studies, {n} images. Now copy it to a USB "
                "drive.").format(s=result.studies, n=result.added))
        self.usb_btn.configure(state="normal")

    def _deliver(self) -> None:
        usb = filedialog.askdirectory(title=_("Choose your USB drive"))
        if not usb:
            return
        src = self.project.archive_dir
        need = deliver.dir_size(src)
        if deliver.free_space(usb) < need:
            messagebox.showwarning(_("Not enough space"), _(
                "That drive doesn't have room for the archive (need about {n}).")
                .format(n=format_bytes(need)))
            return
        dest = os.path.join(usb, "CaseReview_" + time.strftime("%Y%m%d"))
        inv = self.project.inventory_path

        def work(emit, cancel):
            result = deliver.copy_tree_verified(
                src, os.path.join(dest, "Archive"), progress=emit, cancel=cancel)
            if os.path.exists(inv):
                os.makedirs(dest, exist_ok=True)
                dst_inv = os.path.join(dest, os.path.basename(inv))
                ok, note = copy_with_retry(inv, dst_inv)
                if not (ok and os.path.exists(dst_inv)):
                    # Fold a failed inventory copy into the result so the UI
                    # doesn't report a clean delivery while the file is missing.
                    result.failed += 1
                    result.failures.append(
                        (os.path.basename(inv), note or "could not copy inventory"))
            return result, dest

        self.run_job(work, self._deliver_done, self.project.root)

    def _deliver_done(self, status, payload) -> None:
        if status != "done":
            return
        result, dest = payload
        self.wizard.deliver_result = result
        self.wizard.delivered_path = dest
        if result.failed == 0:
            self.info.configure(text=_(
                "✓ Copied to the USB and verified. Click Next to finish."))
        else:
            self.info.configure(text=_(
                "Copied with {f} problem file(s) — see technical details.")
                .format(f=result.failed))
        self.wizard.refresh_nav()


class DoneStep(WizardStep):
    def build(self) -> None:
        self.lbl = ttk.Label(self, text="", wraplength=580, justify="left",
                             font=("", 13))
        self.lbl.grid(row=0, column=0, sticky="w")
        bar = ttk.Frame(self)
        bar.grid(row=1, column=0, sticky="w", pady=(10, 8))
        self.reveal_btn = ttk.Button(bar, text=_("Show the files on the USB"),
                                     command=self._reveal, state="disabled")
        self.reveal_btn.pack(side="left")
        self.inv_btn = ttk.Button(bar, text=_("Open the inventory"),
                                  command=self._inv)
        self.inv_btn.pack(side="left", padx=(8, 0))
        ttk.Label(self, wraplength=580, justify="left", foreground="#444",
                  text=_("Tip: include a one-page cover note with the patient's "
                         "name, date of birth, a short history, and the specific "
                         "questions you want the radiologist to answer.")
                  ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        # Gentle, value-first support ask — shown only after everything worked.
        support = ttk.Frame(self, relief="solid", borderwidth=1, padding=14)
        support.grid(row=3, column=0, sticky="ew", pady=(18, 0))
        support.columnconfigure(0, weight=1)
        ttk.Label(support, wraplength=560, justify="left", font=("", 12), text=_(
            "Was this useful? This tool is free and always will be. If it helped "
            "you, you can buy the dev team a coffee — it keeps the project alive "
            "and free for families who can't pay.")
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(support, text=_("☕  Buy us a coffee"),
                   command=self._donate).grid(row=1, column=0, sticky="w",
                                              pady=(8, 0))

    def _donate(self) -> None:
        webbrowser.open(SUPPORT_URL)

    def enter(self) -> None:
        dp = self.wizard.delivered_path
        if dp:
            self.lbl.configure(text=_(
                "All done! Your archive is on the USB drive at:\n{p}\n\n"
                "You can now hand it to your doctor.").format(p=dp))
            self.reveal_btn.configure(state="normal")
        else:
            self.lbl.configure(text=_("All done."))

    def _reveal(self) -> None:
        if self.wizard.delivered_path:
            reveal(self.wizard.delivered_path)

    def _inv(self) -> None:
        if os.path.exists(self.project.inventory_path):
            open_path(self.project.inventory_path)
