"""Application shell: the root window and in-window navigation."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from .i18n import _, install


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(_("Medical Imaging Archiver"))
        self.root.minsize(660, 580)

        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self._current: tk.Widget | None = None

        self.show_launcher()

    def _swap(self, factory: Callable[[tk.Misc], tk.Widget]) -> None:
        if self._current is not None:
            self._current.destroy()
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
        self.root.title(_("Medical Imaging Archiver"))
        self.show_launcher()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    install()
    App().run()
    return 0
