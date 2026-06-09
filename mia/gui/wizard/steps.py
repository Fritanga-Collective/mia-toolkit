"""The five wizard steps. Panel-bearing steps reuse ProgressLogPanel + jobs."""

from __future__ import annotations

import os
import shutil
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

# The tool and its installers are free. These open in the user's browser —
# the only outbound links in the app (no telemetry, no background calls).
SUPPORT_URL = "https://mia-toolkit.fritanga.co/support.html"
BLOG_URL = "https://fritangacollective.substack.com/"


def institutions_url() -> str:
    """The institutional section in the app's current language — linking the
    language page directly avoids the website's auto-redirect entirely."""
    from ..i18n import current_language
    lang = current_language()
    prefix = "" if lang == "en" else f"{lang}/"
    return f"https://mia-toolkit.fritanga.co/{prefix}support.html#institutions"

from mia.core import deliver, dicomdir, inventory
from mia.core.common import format_bytes
from mia.core.ripper import copy_with_retry

from .. import import_flow
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
            "1.  Add your studies — CDs, USB folders, or ZIP downloads\n"
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


class AddStudiesStep(PanelStep):
    """Acquire studies from any local source: disc, folder/USB, or ZIP."""

    def build(self) -> None:
        ttk.Label(self, wraplength=580, justify="left", text=_(
            "Insert each CD — it copies and ejects automatically. You can "
            "also add studies from a USB drive, a folder, or a ZIP downloaded "
            "from a hospital portal. When everything's added, click Next.")
        ).grid(row=0, column=0, sticky="w")
        # Emoji kept outside the translatable strings (language-neutral).
        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, sticky="w", pady=(8, 4))
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
        self.count_lbl = ttk.Label(self, foreground="#0a7d28", text="")
        self.count_lbl.grid(row=2, column=0, sticky="w", pady=(0, 6))
        self.build_panel(3)
        self._session_open = False   # rip auto-loop is open (idle-polls)
        self._working = False        # a disc/import is actively running
        self.controller = RipSessionController(
            self.wizard.app.root, self.panel,
            get_dest=lambda: self.project.raw_discs_dir,
            on_state_changed=self._busy_state,
            on_session_changed=self._session_state,
            on_disc=lambda r: self._added(),
            parent_widget=self)
        self._import_cancel = None

    def enter(self) -> None:
        self.panel.set_status(
            _("Ready. Insert a disc, then click Start ripping."))
        self._refresh_count()

    def _start(self) -> None:
        self.guard_space(1_000_000_000, self._begin)  # ~1 GB headroom

    def _begin(self) -> None:
        self.project.ensure_dirs()
        self.controller.start()

    def _get_dest(self) -> str:
        self.project.ensure_dirs()
        return self.project.raw_discs_dir

    def _import_folder(self) -> None:
        self._import_cancel = import_flow.start_folder_import(
            self.wizard.app.root, self.panel, get_dest=self._get_dest,
            on_state=self._busy_state, on_done=lambda r: self._added(),
            parent=self)

    def _import_zip(self) -> None:
        self._import_cancel = import_flow.start_zip_import(
            self.wizard.app.root, self.panel, get_dest=self._get_dest,
            on_state=self._busy_state, on_done=lambda r: self._added(),
            parent=self)

    def _added(self) -> None:
        self._refresh_count()
        self.wizard.refresh_nav()

    def _refresh_count(self) -> None:
        n = self.project.disc_count()
        self.count_lbl.configure(
            text=_("Sources added so far: {n}").format(n=n) if n else "")

    # Two states drive the UI. _working = a disc/import is actively copying →
    # gates Next (wizard busy). _session_open = the rip auto-loop is open (it
    # idle-polls between discs) → must NOT gate Next, or the user can never
    # advance after a rip. Both disable the source buttons while in effect.
    def _busy_state(self, running: bool) -> None:
        self._working = running
        self._sync()

    def _session_state(self, active: bool) -> None:
        self._session_open = active
        self._sync()

    def _sync(self) -> None:
        disabled = self._session_open or self._working
        state = "disabled" if disabled else "normal"
        for btn in (self.start_btn, self.folder_btn, self.zip_btn):
            btn.configure(state=state)
        self.wizard.set_busy(self._working)   # Next gated by active work only
        if not self._working:
            self._refresh_count()

    def on_leave(self) -> None:
        if self.controller.active:
            self.controller.stop()
        if self._import_cancel is not None:
            self._import_cancel.set()
            self._import_cancel = None


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
        btns = ttk.Frame(support)
        btns.grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Button(btns, text=_("☕  Buy us a coffee"),
                   command=self._donate).pack(side="left")
        # Emoji outside the translatable string (language-neutral).
        ttk.Button(btns, text=f"📰  {_('Read our blog')}",
                   command=self._blog).pack(side="left", padx=(8, 0))
        # Quiet institutional pointer — per the licensing plan: one line, no
        # nag, opens the support page's institutional section in the browser.
        inst = ttk.Label(
            support, foreground="#666", cursor="hand2",
            font=("", 11, "underline"),
            text=_("Deploying at a clinic or hospital? Institutional licenses "
                   "fund free access for patients →"))
        inst.bind("<Button-1>", lambda e: webbrowser.open(institutions_url()))
        inst.grid(row=2, column=0, sticky="w", pady=(10, 0))

    def _donate(self) -> None:
        webbrowser.open(SUPPORT_URL)

    def _blog(self) -> None:
        webbrowser.open(BLOG_URL)

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
