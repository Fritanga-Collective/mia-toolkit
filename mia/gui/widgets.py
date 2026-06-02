"""Small shared widgets."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, ttk

from .i18n import _


def default_dir(*parts: str) -> str:
    """A sensible default working location under the user's Documents."""
    base = os.path.expanduser("~/Documents/MedicalArchive")
    return os.path.join(base, *parts)


class FolderPicker(ttk.Frame):
    """A label + path entry + Choose… button. ``mode`` is 'dir' or 'savefile'."""

    def __init__(self, master: tk.Misc, label: str, initial: str = "",
                 mode: str = "dir", save_name: str = "") -> None:
        super().__init__(master)
        self.columnconfigure(1, weight=1)
        self.mode = mode
        self.save_name = save_name
        ttk.Label(self, text=label).grid(row=0, column=0, sticky="w",
                                         padx=(0, 8))
        self.var = tk.StringVar(value=initial)
        self.entry = ttk.Entry(self, textvariable=self.var)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.btn = ttk.Button(self, text=_("Choose…"), command=self._choose)
        self.btn.grid(row=0, column=2, padx=(8, 0))

    def _choose(self) -> None:
        if self.mode == "dir":
            path = filedialog.askdirectory(initialdir=self._initdir())
        else:
            path = filedialog.asksaveasfilename(
                initialdir=self._initdir(), initialfile=self.save_name)
        if path:
            self.var.set(path)

    def _initdir(self) -> str:
        cur = self.var.get()
        if cur and os.path.isdir(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent and os.path.isdir(parent):
            return parent
        return os.path.expanduser("~")

    def get(self) -> str:
        return os.path.expanduser(self.var.get().strip())

    def set(self, value: str) -> None:
        self.var.set(value)

    def set_enabled(self, on: bool) -> None:
        state = "normal" if on else "disabled"
        self.entry.configure(state=state)
        self.btn.configure(state=state)
