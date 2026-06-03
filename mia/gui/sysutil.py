"""Tiny platform helpers for revealing/opening files (macOS for now)."""

from __future__ import annotations

import os
import subprocess
import sys


def reveal(path: str) -> None:
    """Reveal a file/folder in the platform file manager."""
    try:
        if sys.platform == "darwin":
            args = ["open", "-R", path] if os.path.isfile(path) else ["open", path]
            subprocess.run(args, check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(["explorer", os.path.normpath(path)], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError:
        pass


def open_path(path: str) -> None:
    """Open a file with its default application."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError:
        pass
