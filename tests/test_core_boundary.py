"""Boundary guard: ``mia.core`` must stay a standalone, offline library.

The core package is slated for extraction into a published ``mia-core`` library
(see the KB extraction plan). For that to stay clean — and to keep the patient
Toolkit's "sends nothing, ever" promise structurally true — ``mia.core`` must
import **no GUI** (tkinter / mia.gui), **no i18n** (mia.i18n), **no network**
(urllib / socket / ssl / http / requests / certifi), and **must not reach back
into the application package** (``from mia import …`` for anything but
``mia.core`` itself).

This is enforced by **static analysis** of core's own source (via ``ast``), not
runtime import inspection — so it can't be fooled by, nor false-positive on, a
third-party dependency's transitive imports. Any PR that crosses the boundary
fails here.
"""

from __future__ import annotations

import ast
import os

import pytest

CORE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mia", "core")

# Top-level module names core must never import.
FORBIDDEN_TOP = {
    "tkinter",            # GUI
    "urllib", "http", "socket", "ssl", "requests", "certifi",  # network/TLS
}
# Forbidden dotted prefixes (submodules of the application).
FORBIDDEN_PREFIXES = ("mia.gui", "mia.i18n")


def _core_files() -> list[str]:
    return [os.path.join(CORE_DIR, f) for f in sorted(os.listdir(CORE_DIR))
            if f.endswith(".py")]


def _imported_names(tree: ast.AST) -> list[tuple[str, int]]:
    """Every (module, lineno) an `import x` / `from x import …` references."""
    out: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            # level>0 is a relative import (from . / from .common) — always in
            # core; node.module is None for `from . import x`.
            if node.level == 0 and node.module:
                out.append((node.module, node.lineno))
    return out


@pytest.mark.parametrize("path", _core_files(),
                         ids=lambda p: os.path.basename(p))
def test_core_module_has_no_forbidden_imports(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for module, lineno in _imported_names(tree):
        top = module.split(".")[0]
        assert top not in FORBIDDEN_TOP, (
            f"{os.path.basename(path)}:{lineno} imports forbidden '{module}' "
            f"— mia.core must stay offline/GUI-free")
        assert not module.startswith(FORBIDDEN_PREFIXES), (
            f"{os.path.basename(path)}:{lineno} imports application module "
            f"'{module}' — mia.core must not depend on the GUI/i18n layers")
        # No reverse import of the application root (e.g. `from mia import
        # __version__`): core owns its own version. `mia.core[.x]` is fine.
        assert not (module == "mia" or
                    (module.startswith("mia.") and
                     not module.startswith("mia.core"))), (
            f"{os.path.basename(path)}:{lineno} reaches into the application "
            f"package via '{module}' — mia.core must be self-contained")


def test_core_exposes_frozen_public_api() -> None:
    """The extraction plan freezes a public surface for semver — assert it's
    importable and stable so an accidental removal is caught."""
    import mia.core as core

    assert core.__version__  # the library owns its own version
    for name in ("Progress", "Cancelled", "CancelToken", "check_cancel",
                 "format_bytes", "format_duration", "is_dicom_file",
                 "importer", "inventory", "dicomdir", "deliver",
                 "delivery_target", "ripper", "sources", "documents",
                 "diagnostics"):
        assert name in core.__all__, f"{name} dropped from mia.core.__all__"
        assert hasattr(core, name), f"mia.core.{name} not importable"
