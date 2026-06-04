"""Internationalization scaffold.

Every user-facing string in the GUI is wrapped in ``_()`` so translations are a
drop-in later. For now the catalog directory is empty, so ``gettext`` falls back
to :class:`gettext.NullTranslations` and ``_()`` returns the original English.

Adding Spanish later is purely additive (no code change):

    xgettext -L Python -o mia/i18n/locale/mia.pot $(find mia -name '*.py')
    msginit -l es_MX -o mia/i18n/locale/es_MX/LC_MESSAGES/mia.po \
            -i mia/i18n/locale/mia.pot
    # translate mia.po, then:
    msgfmt mia/i18n/locale/es_MX/LC_MESSAGES/mia.po \
           -o mia/i18n/locale/es_MX/LC_MESSAGES/mia.mo
"""

from __future__ import annotations

import gettext as _gettext
from pathlib import Path
from typing import Optional, Sequence

DOMAIN = "mia"
LOCALE_DIR = Path(__file__).resolve().parent.parent / "i18n" / "locale"

_translation: _gettext.NullTranslations = _gettext.NullTranslations()


def install(languages: Optional[Sequence[str]] = None) -> None:
    """Load the best available catalog for ``languages`` (or the OS default).

    Safe to call with no catalogs present: it silently falls back to English.
    """
    global _translation
    _translation = _gettext.translation(
        DOMAIN,
        localedir=str(LOCALE_DIR),
        languages=list(languages) if languages else None,
        fallback=True,
    )


def gettext(message: str) -> str:
    return _translation.gettext(message)


# Conventional alias used throughout the GUI.
_ = gettext
