"""Home screen: title + three large action cards."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .i18n import _


class Launcher(ttk.Frame):
    def __init__(self, master: tk.Misc, app: Any) -> None:
        super().__init__(master, padding=28)
        self.app = app
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text=_("Medical Imaging Archiver"),
                  font=("", 22, "bold")).grid(row=0, column=0, pady=(0, 4))
        ttk.Label(self, foreground="#555",
                  text=_("Organize your imaging CDs into one archive for your "
                         "doctor.")).grid(row=1, column=0, pady=(0, 22))

        self._card(2, _("1.   Rip a CD"),
                   _("Copy a disc onto your computer."), app.show_rip)
        self._card(3, _("2.   Build Inventory"),
                   _("List every study in a spreadsheet."), app.show_inventory)
        self._card(4, _("3.   Build Archive for Doctor"),
                   _("Combine everything onto a USB drive."), app.show_archive)

    def _card(self, row: int, title: str, subtitle: str,
              command: Callable[[], None]) -> None:
        card = ttk.Frame(self, relief="solid", borderwidth=1, padding=16)
        card.grid(row=row, column=0, sticky="ew", pady=7)
        card.columnconfigure(0, weight=1)
        btn = ttk.Button(card, text=title, command=command,
                         style="Big.TButton")
        btn.grid(row=0, column=0, sticky="ew")
        ttk.Label(card, text=subtitle, foreground="#666").grid(
            row=1, column=0, sticky="w", pady=(6, 0))
