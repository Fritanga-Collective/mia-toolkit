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
        self.root.title(_("MIA Toolkit"))
        self.root.minsize(660, 580)
        try:
            self._icon = tk.PhotoImage(file=str(ICON_PNG))
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass  # icon is cosmetic — never block startup over it

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self._current: tk.Widget | None = None

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

    def set_language(self, lang: str) -> None:
        """Switch UI language and re-render (the selector lives on the launcher)."""
        from .i18n import set_language
        set_language(lang)
        self.root.title(_("MIA Toolkit"))
        self._menubar = build_menubar(self)  # relabel menus in the new language
        self.show_launcher()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    install()
    App().run()
    return 0
