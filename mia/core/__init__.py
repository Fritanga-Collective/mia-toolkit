"""``mia.core`` — the toolkit's offline worker library (future ``mia-core``).

These modules preserve the algorithms of the original standalone scripts
(``rip_cd.py``, ``dicom_inventory.py``, ``build_dicomdir.py``) verbatim. The
only change is the I/O boundary: instead of printing and calling ``sys.exit``,
each worker accepts an optional progress callback and cancel token and returns
a structured result object. Thin CLI shims reproduce the original
command-line behavior on top of these workers.

This package is **standalone by design** — it imports no GUI (``tkinter`` /
``mia.gui``), no i18n (``mia.i18n``), and no network (``urllib`` / ``socket`` /
``ssl`` / ``http``). That boundary is what keeps the patient Toolkit's "sends
nothing, ever" promise structurally true, and it's enforced by
``tests/test_core_boundary.py``. It is the shared foundation slated for
extraction into a published MIT ``mia-core`` library (see the KB extraction
plan); the names re-exported below are its **public API surface** — treat
changes to them as semver-significant.

``__version__`` is the library's OWN version (independent of the application's
``mia.__version__``); the diagnostic report reports it as ``core_version``.
"""

from __future__ import annotations

# The library's own version line — deliberately separate from the application's
# ``mia.__version__``. Starts at 0.1.0 for the eventual ``mia-core`` package.
__version__ = "0.1.0"

import importlib
from typing import Any

# ── Public API surface (frozen for semver) ──────────────────────────────────
# Lightweight primitives, re-exported for convenience (`from mia.core import
# Progress`). `common` is a dependency-free leaf, so this adds no import cost.
from .common import (  # noqa: E402
    Cancelled,
    CancelToken,
    Progress,
    check_cancel,
    format_bytes,
    format_duration,
    is_dicom_file,
)

# Worker modules are part of the public surface but loaded **lazily** (PEP 562):
# `import mia.core` stays cheap (no eager pydicom/openpyxl), `python -m
# mia.core.<x>` doesn't warn about double-execution, yet `from mia.core import
# inventory` and `mia.core.inventory` both work and `import *` honours __all__.
_SUBMODULES = frozenset({
    "deliver", "delivery_target", "diagnostics", "dicomdir", "documents",
    "importer", "inventory", "ripper", "sources",
})


def __getattr__(name: str) -> Any:
    if name in _SUBMODULES:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)


__all__ = [
    "__version__",
    # primitives
    "Progress",
    "Cancelled",
    "CancelToken",
    "check_cancel",
    "format_bytes",
    "format_duration",
    "is_dicom_file",
    # worker modules
    "importer",
    "inventory",
    "dicomdir",
    "deliver",
    "delivery_target",
    "ripper",
    "sources",
    "documents",
    "diagnostics",
]
