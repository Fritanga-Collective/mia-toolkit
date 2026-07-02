"""Canonical builder for the app's first-party miatools.tech links.

Pure string building — no network, no side effects — so the "the app sends
nothing on its own" promise stays structurally obvious and the whole thing is
trivially unit-testable. The only outbound traffic is the browser opening a URL
the user explicitly clicked.

UTM discipline: we tag the *link*, not the person. ``site_url(..., campaign=…)``
appends a static, opaque ``utm_campaign`` suffix that GoatCounter (cookieless)
reads when the user lands on the site. The app itself transmits nothing.

The registered in-app ``utm_campaign`` codes (first char ``a`` = app bucket):

===  ==========================================================================
awb  Help ▸ Website / "Visit website" menu link
ahp  in-app help-page link
abl  "Read our blog" link
acf  "Buy us a coffee" / support link (menu or general)
adc  the wizard Done-step coffee/support button
===  ==========================================================================

CRITICAL: the update-check URLs (``mia.gui.updates``) must NEVER carry a UTM
tag — that is the app's one automatic network call, and tagging it would both
pollute analytics and break the "sends nothing that identifies a visit"
guarantee. Those constants deliberately do not go through this helper.
"""

from __future__ import annotations

# Canonical apex, no trailing slash — site_url() joins the path itself.
SITE = "https://miatools.tech"

# The source/default language renders at the apex with no locale prefix.
_DEFAULT_LANG = "en"


def site_url(path: str = "", *, campaign: str | None = None,
             lang: str | None = None) -> str:
    """Build ``https://miatools.tech/<lang-prefix><path>`` for a first-party link.

    - ``campaign`` appends ``utm_campaign=<code>`` using the correct separator,
      inserted *before* any ``#fragment`` and after any existing query string.
    - ``lang`` (or, when omitted, the app's current UI language) inserts a
      ``<lang>/`` prefix for non-default languages, matching how the site
      localizes its pages; English/default gets no prefix.
    """
    if lang is None:
        from .i18n import current_language
        lang = current_language()
    prefix = "" if (not lang or lang == _DEFAULT_LANG) else f"{lang}/"

    # Peel any fragment and existing query off the path so a campaign lands in
    # the query component, before the fragment — a UTM after '#' is invisible.
    fragment = ""
    if "#" in path:
        path, frag = path.split("#", 1)
        fragment = "#" + frag
    query = ""
    if "?" in path:
        path, q = path.split("?", 1)
        query = "?" + q

    url = f"{SITE}/{prefix}{path.lstrip('/')}"
    if campaign:
        query += ("&" if query else "?") + f"utm_campaign={campaign}"
    return f"{url}{query}{fragment}"
