"""Home screen: title + fixed-width, centered action cards."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

from .i18n import LANGUAGES, _, current_language

# Buttons share one fixed width (in characters) so the cards are uniform and
# centered, rather than stretching to the full window width.
BUTTON_WIDTH = 30
WRAP = 250


class Launcher(ttk.Frame):
    def __init__(self, master: tk.Misc, app: Any) -> None:
        super().__init__(master, padding=28)
        self.app = app
        # Weighted side columns center the fixed-width cards in column 1.
        self.columnconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        self._row = 0

        self._language_bar()
        self._heading(_("MIA Toolkit"), ("", 22, "bold"), (0, 4))
        self._heading(_("Organize your imaging CDs into one archive for your "
                        "doctor."), ("", 12), (0, 18), color="#555")

        # The path most people should take.
        self._card("✨", _("Guided Setup"),
                   _("Walk me through it, step by step (recommended)."),
                   app.show_wizard)

        self._heading(_("Or use a single tool:"), ("", 11), (16, 4),
                      color="#888")
        self._card("💿", _("Rip a CD"),
                   _("Copy a disc onto your computer."), app.show_rip)
        self._card("📋", _("Build Inventory"),
                   _("List every study in a spreadsheet."), app.show_inventory)
        self._card("💾", _("Build Archive for Doctor"),
                   _("Combine everything onto a USB drive."), app.show_archive)

        self._footer()

    def _footer(self) -> None:
        ttk.Separator(self, orient="horizontal").grid(
            row=self._row, column=0, columnspan=3, sticky="ew", pady=(26, 12))
        self._row += 1
        # Same disclaimer + ethos lines as the website footer.
        ttk.Label(
            self,
            text=_("This software helps you organize and deliver your own "
                   "medical images. It does not interpret images, is not a "
                   "medical device, and does not replace professional "
                   "radiological review. No warranty."),
            foreground="#888", font=("", 10), wraplength=460, justify="center",
        ).grid(row=self._row, column=1, pady=(0, 8))
        self._row += 1
        ttk.Label(self, foreground="#888", font=("", 10),
                  text=_("Open source · Private by design · No tracking")).grid(
            row=self._row, column=1)
        self._row += 1
        ttk.Label(self, foreground="#888", font=("", 10),
                  text=_("Made with ♥ by Fritanga")).grid(
            row=self._row, column=1, pady=(2, 0))
        self._row += 1

    def _language_bar(self) -> None:
        bar = ttk.Frame(self)
        bar.grid(row=self._row, column=0, columnspan=3, sticky="e",
                 pady=(0, 10))
        self._row += 1
        ttk.Label(bar, text=_("Language:"),
                  foreground="#666").pack(side="left", padx=(0, 6))
        self._names_to_code = {name: code for code, name in LANGUAGES.items()}
        combo = ttk.Combobox(bar, state="readonly", width=12,
                             values=list(LANGUAGES.values()))
        combo.set(LANGUAGES.get(current_language(), "English"))
        combo.bind("<<ComboboxSelected>>",
                   lambda e: self.app.set_language(
                       self._names_to_code[combo.get()]))
        combo.pack(side="left")

    def _heading(self, text: str, font, pady, color: str = "") -> None:
        lbl = ttk.Label(self, text=text, font=font, justify="center")
        if color:
            lbl.configure(foreground=color)
        lbl.grid(row=self._row, column=1, pady=pady)
        self._row += 1

    def _card(self, emoji: str, title: str, subtitle: str,
              command: Callable[[], None]) -> None:
        card = ttk.Frame(self)
        # No sticky -> the card keeps its natural (content) width and is
        # centered within the weighted middle column.
        card.grid(row=self._row, column=1, pady=7)
        self._row += 1
        # Emoji is kept out of the translatable string (it's language-neutral)
        # and prefixed here so every card reads "<emoji>  <label>" uniformly.
        # A classic tk.Button so the vertical padding (padx/pady) sits *inside*
        # the button and the pill actually grows with the larger text — the
        # native ttk (aqua) button on macOS won't do that.
        tk.Button(card, text=f"{emoji}  {title}", command=command, font=("", 15),
                  width=BUTTON_WIDTH, padx=18, pady=16, relief="solid",
                  borderwidth=1, bg="white", activebackground="#eef2f7",
                  highlightthickness=0, cursor="hand2").grid(
            row=0, column=0)
        ttk.Label(card, text=subtitle, foreground="#666", wraplength=WRAP,
                  justify="center").grid(row=1, column=0, pady=(6, 0))
