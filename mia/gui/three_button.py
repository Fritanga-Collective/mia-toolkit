"""A tiny three-button modal dialog.

``messagebox`` can't show three buttons with custom labels cleanly, so this is a
minimal ``tk.Toplevel`` in the same spirit as :mod:`mia.gui.report`. Used for the
incremental-redelivery prompts (Update / New / Cancel and Keep / Remove /
Cancel). It returns a caller-supplied value for whichever button was pressed, or
the ``cancel`` value if the window is closed.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, List, Tuple


def ask_three(parent: tk.Misc, title: str, message: str,
              buttons: List[Tuple[str, Any]], *, cancel: Any = None) -> Any:
    """Show a modal dialog with up to three buttons.

    ``buttons`` is an ordered list of ``(label, value)`` pairs, shown left→right;
    the last one gets default focus. Returns the chosen value, or ``cancel`` if
    the dialog is closed via the window manager. Blocks until dismissed.
    """
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent.winfo_toplevel())
    win.resizable(False, False)
    win.columnconfigure(0, weight=1)

    result = {"value": cancel}

    ttk.Label(win, text=message, wraplength=460, justify="left").grid(
        row=0, column=0, sticky="w", padx=16, pady=(16, 12))

    bar = ttk.Frame(win)
    bar.grid(row=1, column=0, sticky="e", padx=16, pady=(0, 16))

    def choose(value: Any) -> None:
        result["value"] = value
        win.destroy()

    last_btn = None
    for label, value in buttons:
        b = ttk.Button(bar, text=label, command=lambda v=value: choose(v))
        b.pack(side="left", padx=(8, 0))
        last_btn = b

    win.protocol("WM_DELETE_WINDOW", lambda: choose(cancel))
    win.bind("<Escape>", lambda _e: choose(cancel))
    if last_btn is not None:
        last_btn.focus_set()

    win.update_idletasks()
    try:
        win.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(win)
    return result["value"]
