"""Native menu bar for the packaged app (macOS app/Window/Help conventions,
Windows/Linux File-menu conventions).

All web links open in the user's browser on explicit click only — the menu
adds no background behavior. Rebuilt by App.set_language so labels follow the
UI language.
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox

from .. import __version__
from .i18n import LANGUAGES, N_, _, current_language

SITE = "https://mia-toolkit.fritanga.co/"
LINKS = [
    (N_("Website"), SITE),
    (N_("Privacy policy"), SITE + "privacy.html"),
    (N_("Support the project"), SITE + "support.html"),
    (N_("Transparency"), SITE + "stats.html"),
    (N_("Read our blog"), "https://fritangacollective.substack.com/"),
]


def _edit_event(root: tk.Tk, name: str):
    def handler() -> None:
        widget = root.focus_get()
        if widget is not None:
            widget.event_generate(f"<<{name}>>")
    return handler


def _about(root: tk.Tk, aqua: bool) -> None:
    if aqua:
        # Standard panel; name/version come from the bundle's Info.plist in
        # the frozen app (set by packaging/macos/mia.spec).
        root.tk.call("tk::mac::standardAboutPanel")
    else:
        messagebox.showinfo(
            _("About MIA Toolkit"),
            f"MIA Toolkit {__version__}\n\n"
            f"{_('Made with ♥ by Fritanga')}\n{SITE}")


def _check_updates(app) -> None:
    """Explicit user action — the only network call the app ever makes."""
    from . import jobs, updates

    def work(_emit, _cancel):
        return updates.check()

    def done(status, result) -> None:
        if status != "done":
            # Append the technical reason untranslated — it makes failures
            # diagnosable (e.g. SSL, DNS, offline) without new msgids.
            detail = (f"\n\n({type(result).__name__}: {result})"
                      if isinstance(result, Exception) else "")
            messagebox.showinfo(
                _("Check for Updates…"),
                _("Couldn't check for updates. Try again later.") + detail)
            return
        if result.newer:
            if messagebox.askyesno(
                    _("Check for Updates…"),
                    _("Version {new} is available — you have {cur}.\n\n"
                      "Open the download page?")
                    .format(new=result.latest, cur=result.current)):
                webbrowser.open(updates.DOWNLOAD_PAGE)
        else:
            messagebox.showinfo(
                _("Check for Updates…"),
                _("You're on the latest version ({v}).")
                .format(v=result.current))

    jobs.run_job(app.root, work, lambda _p: None, done)


def _open_project_folder() -> None:
    from .project import Project
    from .sysutil import open_path
    project = Project()
    project.ensure_dirs()
    open_path(project.root)




def build_menubar(app) -> tk.Menu:
    """Build (or rebuild) the menu bar for the current UI language."""
    root = app.root
    aqua = root.tk.call("tk", "windowingsystem") == "aqua"
    mod = "Command" if aqua else "Control"
    menubar = tk.Menu(root)

    # ----- macOS application menu (About + auto Quit) ----------------------
    if aqua:
        appmenu = tk.Menu(menubar, name="apple", tearoff=False)
        appmenu.add_command(label=_("About MIA Toolkit"),
                            command=lambda: _about(root, aqua))
        appmenu.add_command(label=_("Check for Updates…"),
                            command=lambda: _check_updates(app))
        appmenu.add_separator()
        menubar.add_cascade(menu=appmenu)

    # ----- File -------------------------------------------------------------
    filemenu = tk.Menu(menubar, tearoff=False)
    filemenu.add_command(label=_("Open Project Folder"),
                         command=_open_project_folder)
    if not aqua:
        filemenu.add_separator()
        filemenu.add_command(label=_("Exit"), command=app.request_quit)
    menubar.add_cascade(label=_("File"), menu=filemenu)

    # ----- Edit (native clipboard behavior in text fields) ------------------
    editmenu = tk.Menu(menubar, tearoff=False)
    for label, event, key in [(_("Cut"), "Cut", "X"), (_("Copy"), "Copy", "C"),
                              (_("Paste"), "Paste", "V")]:
        editmenu.add_command(label=label, accelerator=f"{mod}-{key}",
                             command=_edit_event(root, event))
    editmenu.add_separator()
    editmenu.add_command(label=_("Select All"), accelerator=f"{mod}-A",
                         command=_edit_event(root, "SelectAll"))
    menubar.add_cascade(label=_("Edit"), menu=editmenu)

    # ----- Go (mirrors the home cards) + Language ---------------------------
    gomenu = tk.Menu(menubar, tearoff=False)
    nav = [
        (_("Home"), app.show_launcher),
        (_("Guided Setup"), app.show_wizard),
        (_("Add Your Studies"), app.show_rip),
        (_("Build Inventory"), app.show_inventory),
        (_("Build Archive for Doctor"), app.show_archive),
    ]
    for i, (label, command) in enumerate(nav, 1):
        gomenu.add_command(label=label, accelerator=f"{mod}-{i}",
                           command=command)
        root.bind_all(f"<{mod}-Key-{i}>",
                      lambda _e, c=command: c())
    gomenu.add_separator()
    langmenu = tk.Menu(gomenu, tearoff=False)
    lang_var = tk.StringVar(value=current_language())
    menubar._lang_var = lang_var  # keep a reference alive
    for code, name in LANGUAGES.items():
        langmenu.add_radiobutton(label=name, value=code, variable=lang_var,
                                 command=lambda c=code: app.set_language(c))
    gomenu.add_cascade(label=_("Language"), menu=langmenu)
    menubar.add_cascade(label=_("Go"), menu=gomenu)

    # ----- Window (macOS: system-managed window list) -----------------------
    if aqua:
        windowmenu = tk.Menu(menubar, name="window", tearoff=False)
        menubar.add_cascade(label=_("Window"), menu=windowmenu)

    # ----- Help --------------------------------------------------------------
    helpmenu = tk.Menu(menubar, name="help" if aqua else None,
                       tearoff=False)
    for label, url in LINKS:
        helpmenu.add_command(label=_(label),
                             command=lambda u=url: webbrowser.open(u))
    helpmenu.add_separator()
    helpmenu.add_command(label=_("Report a problem…"),
                         command=app.send_feedback)
    if not aqua:
        helpmenu.add_separator()
        helpmenu.add_command(label=_("Check for Updates…"),
                             command=lambda: _check_updates(app))
        helpmenu.add_command(label=_("About MIA Toolkit"),
                             command=lambda: _about(root, aqua))
    menubar.add_cascade(label=_("Help"), menu=helpmenu)

    root.config(menu=menubar)
    return menubar
