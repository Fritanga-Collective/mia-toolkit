"""The five wizard steps. Panel-bearing steps reuse ProgressLogPanel + jobs."""

from __future__ import annotations

import os
import shutil
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

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

from mia.core import deliver, dicomdir, documents, inventory
from mia.core.common import Progress, format_bytes
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
            "3.  Add any report or lab PDFs (optional)\n"
            "4.  Build one archive and copy it to a USB drive for your doctor")
        ).grid(row=1, column=0, sticky="w", pady=(6, 16))
        self.resume_lbl = ttk.Label(self, foreground="#0a7d28", text="")
        self.resume_lbl.grid(row=2, column=0, sticky="w")
        from .view import BUILD_STEP
        self.skip_btn = ttk.Button(self, text=_("Skip to building the archive"),
                                   command=lambda: self.wizard.goto(BUILD_STEP))

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
            on_disc=lambda r: self._added(r),
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
            on_state=self._busy_state, on_done=lambda r: self._added(r),
            parent=self)

    def _import_zip(self) -> None:
        self._import_cancel = import_flow.start_zip_import(
            self.wizard.app.root, self.panel, get_dest=self._get_dest,
            on_state=self._busy_state, on_done=lambda r: self._added(r),
            parent=self)

    def _added(self, result=None) -> None:
        self._note_pdfs(result)
        self._refresh_count()
        self.wizard.refresh_nav()

    def _note_pdfs(self, result) -> None:
        """If the just-imported source carried report PDFs, point the user at
        the upcoming documents step. The scan runs off the UI thread so a large
        disc doesn't pause the UI right after an import finishes."""
        disc_dir = getattr(result, "disc_dir", None)
        if not disc_dir:
            return

        def work(_emit, _cancel):
            return len(documents.find_pdfs(disc_dir))

        def done(status, n):
            if status == "done" and n:
                self.panel.log_plain("📄 " + _(
                    "Found {n} report PDF(s) — review them in "
                    "‘Add documents’.").format(n=n), tag="info")

        run_job(self.wizard.app.root, work, lambda _p: None, done)

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
        self.wizard.inventory_result = result  # studies feed the documents step
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


def _copy_reports(plan, dest: str, result=None) -> int:
    """Copy each included document into ``dest/Reports/`` (unique names),
    folding any failure — including a source that has since disappeared (e.g.
    removable media unplugged) — into ``result`` so the UI can't report a clean
    delivery while a requested document is missing. Returns the count copied."""
    paths = [d["path"] for d in plan] if plan else []
    if not paths:
        return 0
    reports = os.path.join(dest, "Reports")
    os.makedirs(reports, exist_ok=True)
    used: set = set()
    copied = 0
    for src in paths:
        base = os.path.basename(src)
        # Resolve symlinks: copy_with_retry uses follow_symlinks=False (a disc-
        # rip security guard), so a symlinked pick would otherwise land a broken
        # link on the recipient's USB. The user chose this document — they want
        # its real contents. realpath of a broken link → a missing path → fails
        # below and is folded into the result.
        real = os.path.realpath(src)
        if not os.path.exists(real):
            if result is not None:
                result.failed += 1
                result.failures.append((base, "source file no longer exists"))
            continue
        target = os.path.join(reports, base)
        n = 1
        while target in used or os.path.exists(target):
            stem, ext = os.path.splitext(base)
            target = os.path.join(reports, f"{stem} ({n}){ext}")
            n += 1
        used.add(target)
        ok, note = copy_with_retry(real, target)
        if ok and os.path.exists(target):
            copied += 1
        elif result is not None:
            result.failed += 1
            result.failures.append((base, note or "could not copy report"))
    return copied


class AddDocumentsStep(WizardStep):
    """Optional: add report/lab PDFs (and other files) to the archive. PDFs can
    be embedded into a study (rides into PACS); everything checked is also
    copied to a Reports/ folder on the USB. Auto-discovered PDFs are pre-listed.
    The actual encapsulation/copy happens in the build & deliver steps."""

    NO_EMBED = None  # sentinel label resolved at runtime via _no_embed_label()

    def build(self) -> None:
        ttk.Label(self, wraplength=580, justify="left", text=_(
            "Add the radiologist's report or lab/blood-work results (PDFs). "
            "They travel with the scans as files your doctor can open, and PDFs "
            "can also be embedded into the imaging archive for a PACS. Optional "
            "— click Next to skip.")
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(self, text=f"📎  {_('Add files…')}", command=self._add_files
                   ).grid(row=1, column=0, sticky="w", pady=(8, 6))
        self.rows_frame = ttk.Frame(self)
        self.rows_frame.grid(row=2, column=0, sticky="nsew")
        self.rows_frame.columnconfigure(1, weight=1)
        self.empty_lbl = ttk.Label(self, foreground="#666",
                                   text=_("No documents added yet."))
        self.empty_lbl.grid(row=3, column=0, sticky="w", pady=(4, 0))
        self._rows: list[dict] = []
        self._seen: set = set()
        self._refs = None       # latest study choices (refreshed each scan)
        self._scanning = False  # in-flight guard (avoid overlapping scans)

    def _no_embed_label(self) -> str:
        return _("Just include the file")

    def _skip_label(self) -> str:
        return _("Skip this file")

    def _study_refs(self):
        if self._refs is None:
            inv = self.wizard.inventory_result
            self._refs = documents.study_choices(inv) if inv is not None else []
        return self._refs

    def enter(self) -> None:
        # Re-list PDFs found on the imported media on every entry, off the UI
        # thread (a full os.walk over a large ripped dataset would otherwise
        # freeze the wizard). Re-scanning — not a one-shot — means PDFs from a
        # later import (or after an Inventory re-scan) show up here too; rows
        # already shown are skipped via _seen. An in-flight guard avoids
        # overlapping scans on rapid back/forth.
        if self._scanning:
            return
        self._scanning = True
        raw = self.project.raw_discs_dir
        staged = self.project.staged_docs_dir
        inv = self.wizard.inventory_result

        def work(_emit, _cancel):
            refs = documents.study_choices(inv) if inv is not None else []
            pdfs = documents.find_pdfs(raw, exclude_dir=staged)
            return refs, [(p, documents.study_for_path(p, raw)) for p in pdfs]

        def done(status, payload):
            self._scanning = False
            if status == "done" and payload:
                self._refs, found = payload  # refresh study choices for new rows
                for pdf, ref in found:
                    if pdf not in self._seen:
                        self._add_row(pdf, default_study=ref, found=True)
            self._refresh_empty()

        run_job(self.wizard.app.root, work, lambda _p: None, done)

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title=_("Choose reports or documents"),
            filetypes=[(_("Documents"), ("*.pdf", "*.PDF", "*.jpg", "*.jpeg",
                                         "*.png")), (_("All files"), "*.*")])
        for p in paths:
            if p and p not in self._seen:
                self._add_row(p, default_study=None, found=False)
        self._refresh_empty()

    def _add_row(self, path: str, *, default_study, found: bool) -> None:
        self._seen.add(path)
        r = len(self._rows)
        refs = self._study_refs()
        include = tk.BooleanVar(value=True)  # checked by default; uncheck to skip
        cb = ttk.Checkbutton(self.rows_frame, variable=include)
        cb.grid(row=r, column=0, sticky="w")
        # Filename is a clickable link — open it to preview the contents before
        # deciding whether to include/embed it. Focusable + Enter/Space for
        # keyboard access. The 📄 marker stays a plain (non-link) prefix so only
        # the filename itself is underlined/clickable — clearer than linking the
        # emoji too.
        namebox = ttk.Frame(self.rows_frame)
        namebox.grid(row=r, column=1, sticky="w")
        if found:
            ttk.Label(namebox, text="📄").pack(side="left", padx=(0, 4))
        link = ttk.Label(namebox, text=os.path.basename(path),
                         foreground="#0a58ca", cursor="hand2",
                         font=("", 11, "underline"), takefocus=True)
        for seq in ("<Button-1>", "<Return>", "<space>"):
            link.bind(seq, lambda _e, p=path: self._open_doc(p))
        link.pack(side="left")
        # Embed-target dropdown: index 0 = "just include"; index i = refs[i-1].
        # Selection is read back by index (not label) so two studies with the
        # same date+description label can't collide onto the wrong study.
        is_pdf = path.lower().endswith(".pdf")
        values = [self._no_embed_label()] + [ref.label for ref in refs]
        normal_state = "readonly" if (is_pdf and refs) else "disabled"
        combo = ttk.Combobox(self.rows_frame, values=values, state=normal_state,
                             width=28)
        default_idx = 0
        if is_pdf and refs and default_study is not None:
            for i, ref in enumerate(refs):
                if ref.study_uid == default_study.study_uid:
                    default_idx = i + 1
                    break
        combo.current(default_idx)
        combo.grid(row=r, column=2, sticky="e", padx=(8, 0))
        row = {"path": path, "include": include, "combo": combo, "refs": refs,
               "values": values, "state": normal_state, "saved_idx": default_idx}
        self._rows.append(row)

        # Unchecking "skips" the file: grey the dropdown out to a "Skip this
        # file" label so it's obvious nothing will be added; re-checking
        # restores the prior target choice.
        def _toggle(row=row):
            combo = row["combo"]
            if row["include"].get():
                combo.configure(values=row["values"], state=row["state"])
                combo.current(row["saved_idx"])
            else:
                row["saved_idx"] = combo.current()
                combo.configure(values=[self._skip_label()], state="disabled")
                combo.current(0)
        row["toggle"] = _toggle
        cb.configure(command=_toggle)

    def _open_doc(self, path: str) -> None:
        """Open a listed document to preview it; warn if it's gone."""
        if not os.path.exists(path):
            messagebox.showerror(
                _("Can't open file"),
                _("This file can no longer be found:\n{p}").format(p=path),
                parent=self)
            return
        open_path(path)

    def _refresh_empty(self) -> None:
        self.empty_lbl.grid() if not self._rows else self.empty_lbl.grid_remove()

    def on_leave(self) -> None:
        plan = []
        for row in self._rows:
            if not row["include"].get():
                continue
            idx = row["combo"].current()  # 0 = just include; i = refs[i-1]
            embed = row["refs"][idx - 1] if 0 < idx <= len(row["refs"]) else None
            plan.append({"path": row["path"], "embed_study": embed})
        self.wizard.documents_plan = plan


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
        embed = [d for d in self.wizard.documents_plan if d.get("embed_study")]
        # Rebuild if there's a leftover partial build, or if documents need to
        # be embedded into the fileset (they ride in via raw_discs/_documents).
        if os.path.exists(out) and (embed or not self.project.has_archive()):
            shutil.rmtree(out, ignore_errors=True)
        if self.project.has_archive() and not embed:
            self._build_done("done", None)
            return

        def work(emit, cancel):
            self._stage_documents(emit)  # encapsulate embed-PDFs before walk
            return dicomdir.build_fileset(self.project.raw_discs_dir, out,
                                          progress=emit, cancel=cancel)

        self.run_job(work, self._build_done, self.project.root)

    def _stage_documents(self, emit) -> None:
        """Encapsulate embed-marked PDFs into raw_discs/_documents so the
        DICOMDIR build picks them up. A bad PDF is skipped (not fatal — the
        companion Reports/ copy still carries the original), but the failure is
        surfaced in the progress log so the user knows it wasn't embedded."""
        staged = self.project.staged_docs_dir
        shutil.rmtree(staged, ignore_errors=True)
        embed = [d for d in self.wizard.documents_plan if d.get("embed_study")]
        if not embed:
            return
        os.makedirs(staged, exist_ok=True)
        for d in embed:
            name = os.path.basename(d["path"])
            try:
                documents.encapsulate_pdf(d["path"], d["embed_study"], staged)
            except Exception:
                emit(Progress(0, 0, kind="fail", phase="build", note=_(
                    "Couldn't embed {name} into the archive — it's still "
                    "included as a file.").format(name=name)))

    def _build_done(self, status, result) -> None:
        if status != "done":
            return
        if result is not None:
            self.wizard.archive_result = result
            self.info.configure(text=_(
                "Archive built: {s} studies, {n} images. Now copy it to a USB "
                "drive.").format(s=result.studies, n=result.added))
        self.usb_btn.configure(state="normal")

    @staticmethod
    def _fmt_study_date(d: str) -> str:
        d = (d or "").strip()
        return f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 and d.isdigit() else d

    def _copy_groups(self, src: str):
        """Localized (label, paths) groups so the copy announces progress per
        study. Returns None (flat copy) if the archive index can't be read."""
        try:
            studies = dicomdir.study_groups(src)
        except Exception:
            studies = []
        if not studies:
            return None
        n = len(studies)
        groups = []
        for i, s in enumerate(studies, 1):
            name = " ".join(p for p in (s.get("modality"),
                                        s.get("description")) if p)
            date = self._fmt_study_date(s.get("date", ""))
            if date:
                name = f"{name} · {date}".strip(" ·") if name else date
            name = name or _("Study")
            label = _("{name} ({count} images)").format(
                name=name, count=s.get("count", 0))
            milestone = _("Copying study {i} of {n}: {label}…").format(
                i=i, n=n, label=label)
            groups.append((milestone, s["paths"]))
        return groups

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
            # Copy study-by-study (prefer_native=False so the in-process pass
            # does the real copying and the per-study milestones track it live,
            # not flash by after an opaque ditto run — the two copiers are
            # device-bound-equivalent). Sample a handful of files for SHA-256
            # content verification (cheap insurance against a drive that writes
            # the wrong bytes at the right size — counterfeit/failing sticks).
            result = deliver.copy_tree_verified(
                src, os.path.join(dest, "Archive"),
                prefer_native=False, groups=self._copy_groups(src),
                verify_sample=deliver.DEFAULT_VERIFY_SAMPLE,
                progress=emit, cancel=cancel)
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
            # Companion reports/labs → Reports/ (every included document, as a
            # plain file the doctor can open; embed copies already rode in the
            # Archive via _stage_documents).
            _copy_reports(self.wizard.documents_plan, dest, result)
            # Doctor-facing docs at the CaseReview root (beside Archive/, never
            # inside it — they must not perturb the DICOMDIR). README describes
            # the archive; DELIVERY-LOG records what was copied and when.
            ar = self.wizard.archive_result
            try:
                if ar is not None:
                    dicomdir.write_readme(dest, ar, self.project.raw_discs_dir)
                dicomdir.write_delivery_log(dest, ar)
            except OSError as e:
                # Don't report a clean delivery if the doctor-facing docs
                # couldn't be written (drive full / permissions).
                result.failed += 1
                result.failures.append(("README.txt / DELIVERY-LOG.txt", str(e)))
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
        self.addfiles_btn = ttk.Button(
            bar, text=f"📎  {_('Add more files to the USB')}",
            command=self._add_files, state="disabled")
        self.addfiles_btn.pack(side="left", padx=(8, 0))
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
            self.addfiles_btn.configure(state="normal")
        else:
            self.lbl.configure(text=_("All done."))
            self.addfiles_btn.configure(state="disabled")

    def _add_files(self) -> None:
        """Companion-only append to the delivered USB. (Embedding into the
        DICOM archive must happen before building, so it's not offered here.)"""
        dp = self.wizard.delivered_path
        if not dp:
            return
        paths = filedialog.askopenfilenames(
            title=_("Choose reports or documents"),
            filetypes=[(_("Documents"), ("*.pdf", "*.PDF", "*.jpg", "*.jpeg",
                                         "*.png")), (_("All files"), "*.*")])
        if not paths:
            return
        plan = [{"path": p, "embed_study": None} for p in paths]
        acc = SimpleNamespace(failed=0, failures=[])  # capture copy failures
        n = _copy_reports(plan, dp, acc)
        msg = _("Copied {n} file(s) to the USB.").format(n=n)
        if acc.failed:
            msg += "\n\n" + _("{f} file(s) could not be copied.").format(
                f=acc.failed)
        msg += "\n\n" + _("To embed reports into the DICOM archive for a PACS, "
                          "add them before building.")
        show = messagebox.showwarning if acc.failed else messagebox.showinfo
        show(_("Add more files to the USB"), msg)

    def _reveal(self) -> None:
        if self.wizard.delivered_path:
            reveal(self.wizard.delivered_path)

    def _inv(self) -> None:
        if os.path.exists(self.project.inventory_path):
            open_path(self.project.inventory_path)
