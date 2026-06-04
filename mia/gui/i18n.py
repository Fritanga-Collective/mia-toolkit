"""Internationalization: gettext catalogs + a runtime-switchable language.

Every user-facing string is wrapped in ``_()``. Strings that are bound at import
time (class attributes, module constants) use ``N_()`` to mark them for
extraction without translating immediately; they're translated at *use* time so
a language switch re-renders them.

Catalogs live in ``mia/i18n/locale/<lang>/LC_MESSAGES/mia.mo``. English is the
source language (no catalog needed — gettext falls back to the original text).
The chosen language is remembered in a small JSON config so it persists across
launches. No network, no telemetry.
"""

from __future__ import annotations

import gettext as _gettext
import json
import os
from pathlib import Path
from typing import Optional, Sequence

DOMAIN = "mia"
LOCALE_DIR = Path(__file__).resolve().parent.parent / "i18n" / "locale"

# code -> display name (shown, in its own language, in the language selector)
LANGUAGES = {"en": "English", "es": "Español", "zh": "中文"}

_translation: _gettext.NullTranslations = _gettext.NullTranslations()
_current: str = "en"


def _config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "mia-toolkit" / "config.json"


def _load_pref() -> Optional[str]:
    try:
        with open(_config_path(), encoding="utf-8") as f:
            lang = json.load(f).get("language")
        return lang if lang in LANGUAGES else None
    except (OSError, ValueError):
        return None


def _save_pref(lang: str) -> None:
    try:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"language": lang}, f)
    except OSError:
        pass


def install(languages: Optional[Sequence[str]] = None) -> None:
    """Load a catalog. With no argument, use the saved preference or OS default."""
    global _translation, _current
    if languages is None:
        pref = _load_pref()
        languages = [pref] if pref else None
    _translation = _gettext.translation(
        DOMAIN, localedir=str(LOCALE_DIR),
        languages=list(languages) if languages else None, fallback=True)
    if languages:
        _current = languages[0]
    else:
        # OS-default path: report whichever catalog gettext actually loaded, so
        # the selector stays in sync with what's rendered.
        loaded = (_translation.info().get("language") or "").split("_")[0].lower()
        _current = loaded if loaded in LANGUAGES else "en"


def set_language(lang: str) -> None:
    """Switch language at runtime and remember the choice."""
    global _current
    _current = lang
    install([lang])
    _save_pref(lang)


def current_language() -> str:
    return _current


def gettext(message: str) -> str:
    return _translation.gettext(message)


def N_(message: str) -> str:
    """Mark a string for extraction but translate it later (deferred)."""
    return message


# Conventional alias used throughout the GUI.
_ = gettext
