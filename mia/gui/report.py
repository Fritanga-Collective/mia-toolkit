"""'Report a problem' — let the user generate an anonymized diagnostic report,
review it, and send it themselves. No auto-collection: the report is built from
the in-memory technical log, scrubbed of PHI (see mia.core.diagnostics), shown
in full, and only leaves the machine if the user copies/saves/emails it.
"""

from __future__ import annotations

import glob
import os
import tempfile
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from urllib.parse import quote

from mia.core import diagnostics
from .i18n import _, current_language

CONTACT = "mia-tools@fritanga.co"


def latest_session_log_lines(*extra_dirs: str) -> list:
    """Read the newest mia_session_*.log (project + temp + any extra dir) so a
    report can be filed even from a screen without a live panel."""
    candidates = []
    for d in (*extra_dirs, tempfile.gettempdir()):
        if d and os.path.isdir(d):
            candidates += glob.glob(os.path.join(d, "mia_session_*.log"))
    if not candidates:
        return []
    newest = max(candidates, key=lambda p: os.path.getmtime(p))
    try:
        with open(newest, encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return []


def open_report_dialog(parent: tk.Misc, log_lines: list,
                       extra: dict | None = None) -> None:
    extra = {"language": current_language(), **(extra or {})}

    win = tk.Toplevel(parent)
    win.title(_("Report a problem"))
    win.transient(parent.winfo_toplevel())
    win.columnconfigure(0, weight=1)
    win.rowconfigure(3, weight=1)

    ttk.Label(win, wraplength=620, justify="left", text=_(
        "Send us a report to help diagnose a problem. It's anonymized — no "
        "patient names, no file contents — and it's sent only when you choose. "
        "Review exactly what will be sent below.")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8))

    ttk.Label(win, text=_("What happened? Steps to reproduce? (optional)")).grid(
        row=1, column=0, sticky="w", padx=12)
    notes = tk.Text(win, height=4, wrap="word", relief="solid", borderwidth=1)
    notes.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 8))

    ttk.Label(win, text=_("Report preview — this is exactly what will be sent:")
              ).grid(row=3, column=0, sticky="sw", padx=12)
    box = ttk.Frame(win)
    box.grid(row=4, column=0, sticky="nsew", padx=12)
    box.rowconfigure(0, weight=1)
    box.columnconfigure(0, weight=1)
    win.rowconfigure(4, weight=1)
    preview = tk.Text(box, height=16, wrap="none", font=("Menlo", 10),
                      state="disabled", background="#1e1e1e", foreground="#d4d4d4")
    preview.grid(row=0, column=0, sticky="nsew")
    sb = ttk.Scrollbar(box, command=preview.yview)
    sb.grid(row=0, column=1, sticky="ns")
    preview.configure(yscrollcommand=sb.set)

    state = {"report": "", "job": None}

    def rebuild() -> None:
        state["job"] = None
        report = diagnostics.build_report(
            notes.get("1.0", "end").strip(), log_lines, extra=extra)
        state["report"] = report
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        preview.insert("1.0", report)
        preview.configure(state="disabled")

    def schedule(_e=None) -> None:
        if state["job"] is not None:
            try:
                win.after_cancel(state["job"])
            except tk.TclError:
                pass
        state["job"] = win.after(400, rebuild)

    notes.bind("<KeyRelease>", schedule)

    def do_copy() -> None:
        win.clipboard_clear()
        win.clipboard_append(state["report"])
        messagebox.showinfo(_("Report a problem"),
                            _("Report copied to the clipboard — paste it into "
                              "an email to {c}.").format(c=CONTACT), parent=win)

    def save_to(path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(state["report"])
            return True
        except OSError as e:
            messagebox.showerror(_("Report a problem"),
                                 _("Couldn't save the report: {e}").format(e=e),
                                 parent=win)
            return False

    def do_save() -> None:
        path = filedialog.asksaveasfilename(
            parent=win, title=_("Save report"), defaultextension=".txt",
            initialfile=f"mia-report-{time.strftime('%Y%m%d-%H%M%S')}.txt")
        if path and save_to(path):
            messagebox.showinfo(_("Report a problem"),
                                _("Saved."), parent=win)

    def do_email() -> None:
        # The full report → saved file + clipboard (no client length limit).
        # The email body carries the report itself (mailto can't attach a file),
        # with its log section capped so any mail client accepts it.
        tmp = os.path.join(tempfile.gettempdir(),
                           f"mia-report-{time.strftime('%Y%m%d-%H%M%S')}.txt")
        saved = save_to(tmp)
        win.clipboard_clear()
        win.clipboard_append(state["report"])
        pointer = _("\n\n(Full report saved at {p} and copied to your "
                    "clipboard.)").format(p=tmp if saved else _("(not saved)"))
        body = diagnostics.build_report(
            notes.get("1.0", "end").strip(), log_lines, extra=extra,
            max_log_lines=60) + pointer
        subject = _("MIA Toolkit problem report")
        url = f"mailto:{CONTACT}?subject={quote(subject)}&body={quote(body)}"
        if len(url) > 6000:                      # too long for some mail clients
            body = (notes.get("1.0", "end").strip()
                    or _("(no description)")) + pointer
            url = f"mailto:{CONTACT}?subject={quote(subject)}&body={quote(body)}"
        try:
            webbrowser.open(url)
        except Exception:
            messagebox.showinfo(
                _("Report a problem"),
                _("Couldn't open your email app. The report is on your "
                  "clipboard and saved at:\n{p}\n\nPlease email it to {c}.")
                .format(p=tmp if saved else _("(not saved)"), c=CONTACT),
                parent=win)

    bar = ttk.Frame(win)
    bar.grid(row=5, column=0, sticky="e", padx=12, pady=12)
    ttk.Button(bar, text=_("Close"), command=win.destroy).pack(
        side="right", padx=(8, 0))
    ttk.Button(bar, text=f"✉  {_('Email it to us')}", command=do_email).pack(
        side="right", padx=(8, 0))
    ttk.Button(bar, text=_("Save…"), command=do_save).pack(side="right",
                                                           padx=(8, 0))
    ttk.Button(bar, text=_("Copy"), command=do_copy).pack(side="right")

    rebuild()
    win.minsize(640, 520)
