"""Wizard container: breadcrumb header, a body that shows one step, and a
Back / Next / Exit footer. Navigation locks while a step is running a job.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from ..i18n import N_, _
from ..project import Project

STEP_TITLES = [N_("Welcome"), N_("Rip discs"), N_("Review"),
               N_("Build & deliver"), N_("Done")]
LAST = len(STEP_TITLES) - 1


class WizardView(ttk.Frame):
    def __init__(self, master: tk.Misc, app: Any) -> None:
        super().__init__(master, padding=16)
        self.app = app
        self.project = Project()
        self.project.ensure_dirs()

        # Shared results, filled in by steps and read by the Done step.
        self.archive_result = None
        self.deliver_result = None
        self.delivered_path: Optional[str] = None

        self._busy = False
        self._steps: dict[int, Any] = {}
        self.index = 0

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        head = ttk.Frame(self)
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text=_("Guided Setup"),
                  font=("", 18, "bold")).grid(row=0, column=0, sticky="w")
        self.crumb = ttk.Label(head, text="", foreground="#666")
        self.crumb.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.body = ttk.Frame(self)
        self.body.grid(row=2, column=0, sticky="nsew", pady=12)
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(0, weight=1)

        foot = ttk.Frame(self)
        foot.grid(row=3, column=0, sticky="ew")
        self.exit_btn = ttk.Button(foot, text=_("Exit to Home"),
                                   command=self._exit)
        self.exit_btn.pack(side="left")
        self.next_btn = ttk.Button(foot, text=_("Next ›"), command=self._next)
        self.next_btn.pack(side="right")
        self.back_btn = ttk.Button(foot, text=_("‹ Back"), command=self._back)
        self.back_btn.pack(side="right", padx=(0, 8))

        self._show(0)

    # ----- step access ----------------------------------------------------

    def _classes(self):
        from .steps import (ArchiveStep, DoneStep, InventoryStep, RipStep,
                            WelcomeStep)
        return [WelcomeStep, RipStep, InventoryStep, ArchiveStep, DoneStep]

    def _get(self, i: int):
        if i not in self._steps:
            step = self._classes()[i](self.body, self)
            step.grid(row=0, column=0, sticky="nsew")
            self._steps[i] = step
        return self._steps[i]

    @property
    def current(self):
        return self._steps.get(self.index)

    # ----- navigation -----------------------------------------------------

    def _show(self, i: int) -> None:
        for j, s in self._steps.items():
            if j != i:
                s.grid_remove()
        step = self._get(i)
        step.grid()
        self.index = i
        step.enter()
        self.crumb.configure(text=_("Step {n} of {m}:  {t}").format(
            n=i + 1, m=LAST + 1, t=_(STEP_TITLES[i])))
        self.refresh_nav()

    def goto(self, i: int) -> None:
        if self.current:
            self.current.on_leave()
        self._show(i)

    def _next(self) -> None:
        if self._busy:
            return
        if self.index >= LAST:
            self._exit()
            return
        if not self.current.can_advance():
            return
        self.current.on_leave()
        self._show(self.index + 1)

    def _back(self) -> None:
        if self._busy or self.index == 0:
            return
        self.current.on_leave()
        self._show(self.index - 1)

    def _exit(self) -> None:
        if self._busy:
            return
        if self.current:
            self.current.on_leave()
        self.app.show_launcher()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.refresh_nav()

    def refresh_nav(self) -> None:
        last = self.index >= LAST
        next_off = self._busy or (not last and not self.current.can_advance())
        self.next_btn.configure(text=_("Finish") if last else _("Next ›"),
                                state="disabled" if next_off else "normal")
        self.back_btn.configure(
            state="disabled" if (self._busy or self.index == 0) else "normal")
        self.exit_btn.configure(state="disabled" if self._busy else "normal")
