"""Application shell: the root window and in-window navigation."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable

from .i18n import _, install
from .menubar import build_menubar

# Window/taskbar icon (macOS Dock uses the bundle's .icns instead). Bundled
# by the PyInstaller specs alongside the locale data.
ICON_PNG = Path(__file__).resolve().parent / "assets" / "icon.png"


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(self._title())
        self.root.minsize(660, 580)
        try:
            self._icon = tk.PhotoImage(file=str(ICON_PNG))
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass  # icon is cosmetic — never block startup over it

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self._current: tk.Widget | None = None

        # Route every close path through one confirming handler: the window
        # close button, macOS Cmd-Q / the Apple-menu Quit, and File ▸ Exit
        # (wired in menubar.py). Tk would otherwise destroy the window
        # immediately, killing a running copy/rip mid-stream.
        self.root.protocol("WM_DELETE_WINDOW", self.request_quit)
        try:
            self.root.createcommand("tk::mac::Quit", self.request_quit)
        except tk.TclError:
            pass  # non-aqua: no such command

        self._menubar = build_menubar(self)
        self.show_launcher()

    def _swap(self, factory: Callable[[tk.Misc], tk.Widget]) -> None:
        current = self._current
        if current is not None:
            # Menus/shortcuts bypass the views' own busy-locking — refuse to
            # tear down a view while it is running a job.
            is_busy = getattr(current, "is_busy", None)
            if callable(is_busy) and is_busy():
                messagebox.showinfo(
                    _("MIA Toolkit"),
                    _("A task is still running — stop it or let it finish "
                      "first."))
                return
            current.destroy()
        self._current = factory(self.container)
        self._current.pack(fill="both", expand=True)
        # macOS/Aqua deferred-redraw fix: destroying a view that held native
        # tk.Text widgets (the tool screens' log panels) and immediately
        # building a new one leaves the replacement un-repainted until the
        # window gets a real OS event (mouse move / resize). Flush pending
        # redraws now, and on Aqua force an expose so labels paint immediately.
        # (Do NOT use full update() here — this runs inside a button callback.)
        self._current.update_idletasks()
        if self.root.tk.call("tk", "windowingsystem") == "aqua":
            self._current.event_generate("<Expose>")

    # Imports are local to avoid a circular import at module load.
    def show_launcher(self) -> None:
        from .launcher import Launcher
        self._swap(lambda parent: Launcher(parent, self))

    def show_wizard(self) -> None:
        from .wizard import WizardView
        self._swap(lambda parent: WizardView(parent, self))

    def show_rip(self) -> None:
        from .rip_view import RipView
        self._swap(lambda parent: RipView(parent, self))

    def show_inventory(self) -> None:
        from .inventory_view import InventoryView
        self._swap(lambda parent: InventoryView(parent, self))

    def show_archive(self) -> None:
        from .archive_view import ArchiveView
        self._swap(lambda parent: ArchiveView(parent, self))

    def send_feedback(self) -> None:
        """Open the anonymized report/feedback dialog from anywhere. Uses the
        current view's live log if it has one, else the newest session log."""
        from .project import Project
        from .report import latest_session_log_lines, open_report_dialog
        view = self._current
        panel = getattr(view, "panel", None) or getattr(
            getattr(view, "current", None), "panel", None)
        lines = list(getattr(panel, "_tech_lines", []) or [])
        summary = getattr(panel, "last_summary", None)
        if not lines:
            try:
                lines = latest_session_log_lines(Project().root)
            except Exception:
                lines = []
        open_report_dialog(self.root, lines, summary=summary)

    def set_language(self, lang: str) -> None:
        """Switch UI language and re-render (the selector lives on the launcher)."""
        from .i18n import set_language
        set_language(lang)
        self.root.title(self._title())
        self._menubar = build_menubar(self)  # relabel menus in the new language
        self.show_launcher()

    def _title(self) -> str:
        from mia_core import diagnostics
        base = _("MIA Toolkit")
        return f"{base} — {_('anonymized logs')}" if diagnostics.redacting() \
            else base

    def request_quit(self) -> None:
        """Confirm before quitting, and stop any running work safely first.

        Bound to the window close button, Cmd-Q / Apple-menu Quit, and the
        non-aqua File ▸ Exit. We signal the running work to cancel, then quit.
        Workers run on *daemon* threads, so the process can exit before a worker
        reaches its next between-files cancel check — the in-flight file may be
        cut mid-write. That's intentionally fine: every copy/rip is resume-safe
        and verified (size, plus a SHA-256 sample), so the next run recopies
        anything left partial and nothing is corrupted. We don't block quit
        waiting for the worker (a multi-minute copy must not wedge the close)."""
        current = self._current
        is_busy = getattr(current, "is_busy", None)
        busy = callable(is_busy) and is_busy()
        if busy:
            ok = messagebox.askyesno(
                _("Quit MIA Toolkit?"),
                _("Something is still running. If you quit now it will stop "
                  "safely — you can resume it later.\n\nQuit anyway?"),
                default="no", icon="warning")
        else:
            ok = messagebox.askyesno(
                _("Quit MIA Toolkit?"), _("Quit MIA Toolkit?"), default="no")
        if not ok:
            return
        if busy:
            self._stop_current(current)
        self.root.destroy()

    @staticmethod
    def _stop_current(view: tk.Widget) -> None:
        """Best-effort: signal the active view to cancel its work (sets cancel
        tokens, stops the rip poll loop) before we tear down. Daemon workers may
        not observe it before the process exits — resume-safety covers that."""
        for name in ("stop", "on_leave"):
            fn = getattr(view, name, None)
            if callable(fn):
                try:
                    fn()
                except Exception:  # pragma: no cover - shutdown best-effort
                    pass
        # The wizard delegates per-step cleanup to its active step.
        step = getattr(view, "current", None)
        on_leave = getattr(step, "on_leave", None)
        if callable(on_leave):
            try:
                on_leave()
            except Exception:  # pragma: no cover - shutdown best-effort
                pass

    def run(self) -> None:
        self.root.mainloop()


def _parse(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="mia", description=_("MIA Toolkit"))
    p.add_argument(
        "--anonymize", action="store_true",
        help="redact paths/names/IDs in the on-screen logs and the session "
             "log — for safe testing and screencasts")
    return p.parse_args(argv)


def main(argv=None) -> int:
    from mia_core import diagnostics
    args = _parse(argv)
    diagnostics.set_redact(args.anonymize)
    install()
    App().run()
    return 0
