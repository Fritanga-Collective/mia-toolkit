"""Tests for the canonical in-app link builder (mia.gui.links).

Two things matter here: that site_url() composes UTM-tagged first-party links
correctly (query before fragment, right separator, locale prefix), and — the
load-bearing safety guard — that the update-check URLs never carry a UTM tag.
"""

from __future__ import annotations

from mia.gui import links, updates
from mia.gui.links import site_url


def test_basic_campaign_tag():
    assert (site_url("support.html", campaign="acf")
            == "https://miatools.tech/support.html?utm_campaign=acf")


def test_no_campaign_is_bare():
    assert site_url("support.html") == "https://miatools.tech/support.html"
    assert site_url() == "https://miatools.tech/"


def test_anchor_keeps_query_before_fragment():
    # The campaign must land in the query component, before the '#anchor' — a
    # utm_campaign after the fragment would be invisible to analytics.
    assert (site_url("support.html#institutions", campaign="acf")
            == "https://miatools.tech/support.html?utm_campaign=acf#institutions")


def test_anchor_without_campaign_is_preserved():
    assert (site_url("support.html#institutions")
            == "https://miatools.tech/support.html#institutions")


def test_existing_query_uses_ampersand_separator():
    assert (site_url("x?a=1", campaign="abl")
            == "https://miatools.tech/x?a=1&utm_campaign=abl")


def test_non_default_lang_inserts_prefix():
    assert (site_url("support.html", lang="es", campaign="acf")
            == "https://miatools.tech/es/support.html?utm_campaign=acf")
    # English/default gets no prefix.
    assert site_url("support.html", lang="en") == \
        "https://miatools.tech/support.html"


def test_lang_prefix_with_fragment():
    assert (site_url("blog/", lang="de", campaign="abl")
            == "https://miatools.tech/de/blog/?utm_campaign=abl")


def test_site_constant_has_no_trailing_slash():
    assert links.SITE == "https://miatools.tech"


# --- The critical guard: the app's one automatic network call stays clean. ---

def test_update_check_urls_are_never_tagged():
    assert "utm_campaign" not in updates.VERSION_URL
    assert "utm_campaign" not in updates.DOWNLOAD_PAGE


def test_updates_source_contains_no_utm():
    """Static backstop: even a future refactor of updates.py can't introduce a
    utm_campaign onto the version/download URLs without tripping this."""
    import inspect
    src = inspect.getsource(updates)
    assert "utm_campaign" not in src
