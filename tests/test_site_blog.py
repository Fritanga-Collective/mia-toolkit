"""Tests for the website blog pipeline in website/build.py.

The generator is a standalone stdlib script (not a package), so we load it by
path via importlib. These exercise the pure functions — front-matter parsing,
slug clustering, and that the sitemap + RSS feed include the sample post — so
the blog machinery is regression-covered without a full HTTP/render harness.

`markdown` is a build-time-only dep (website/requirements.txt); if it isn't
installed in the test environment we skip rather than fail the app suite.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_PY = os.path.join(REPO, "website", "build.py")


def _load_build():
    spec = importlib.util.spec_from_file_location("website_build", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ModuleNotFoundError as e:  # markdown not installed in this env
        # Only skip for the known build-time dep; re-raise anything else so a
        # real regression (e.g. a typoed stdlib import) fails loudly instead of
        # silently skipping the whole module. Called at module load, so the skip
        # must allow a module-level skip (else pytest errors at collection).
        if e.name != "markdown":
            raise
        pytest.skip(f"website build dep missing: {e}", allow_module_level=True)
    return mod


build = _load_build()


def test_parse_front_matter_scalars_and_lists():
    text = (
        "---\n"
        "title: Hello World\n"
        'slug: "hello-world"\n'
        "date: 2026-06-15\n"
        "languages: [en, es]\n"
        'tags: ["a", "b"]\n'
        "status: published\n"
        "---\n"
        "\n# Body\n\nSome *markdown* here.\n"
    )
    meta, body = build._parse_front_matter(text)
    assert meta["title"] == "Hello World"
    assert meta["slug"] == "hello-world"        # quotes stripped
    assert meta["languages"] == ["en", "es"]    # bare list
    assert meta["tags"] == ["a", "b"]           # quoted list
    assert meta["status"] == "published"
    assert body.startswith("# Body")            # leading blank lines trimmed


def test_parse_front_matter_no_block():
    meta, body = build._parse_front_matter("# Just markdown\n")
    assert meta == {}
    assert body == "# Just markdown\n"


def test_url_helpers():
    assert build.blog_index_url("en") == "/blog/"
    assert build.blog_index_url("es") == "/es/blog/"
    assert build.blog_post_url("en", "x") == "/blog/x/"
    assert build.blog_post_url("es", "x") == "/es/blog/x/"


def test_load_posts_and_clusters():
    posts, clusters = build.load_posts()
    slugs = {p["slug"] for p in posts}
    assert "drawer-of-hospital-cds" in slugs
    # Every returned post is published, and clusters group by slug.
    assert all(p["status"] == "published" for p in posts)
    for slug, cluster in clusters.items():
        assert all(p["slug"] == slug for p in cluster)
    # The drawer post is a multi-language cluster sharing one slug (at least
    # the original en/es/zh; more locales may have been added since).
    assert {p["lang"] for p in clusters["drawer-of-hospital-cds"]} >= {
        "en", "es", "zh"}
    sample = next(p for p in posts
                  if p["slug"] == "drawer-of-hospital-cds" and p["lang"] == "en")
    assert sample["date"] == "2026-06-05"


def test_sitemap_includes_blog():
    posts, clusters = build.load_posts()
    langs = build.load_langs()
    out = build.sitemap(langs, posts, clusters)
    assert "https://miatools.tech/blog/" in out
    assert "https://miatools.tech/blog/drawer-of-hospital-cds/" in out


def test_rss_feed_well_formed_and_has_sample():
    import xml.dom.minidom

    posts, _ = build.load_posts()
    en = [p for p in posts if p["lang"] == "en"]
    out = build.rss_feed(en)
    xml.dom.minidom.parseString(out)            # raises if malformed
    assert '<rss version="2.0">' in out
    assert "What to Do With a Drawer Full of Hospital Imaging CDs" in out
    assert "Fri, 05 Jun 2026" in out            # RFC-822 pubDate


def test_date_gate_holds_future_and_shows_past(monkeypatch):
    import datetime

    # BLOG_PREVIEW is read from the env at import; force it off so this test is
    # deterministic even if a dev/CI exports BLOG_PREVIEW.
    monkeypatch.setattr(build, "BLOG_PREVIEW", False)
    today = datetime.date(2026, 6, 23)
    # Past / today → live; future → held; missing or malformed → live (now).
    assert build._is_live({"date": "2020-01-01"}, today) is True
    assert build._is_live({"date": "2026-06-23"}, today) is True
    assert build._is_live({"date": "2099-12-31"}, today) is False
    assert build._is_live({"date": ""}, today) is True
    assert build._is_live({}, today) is True
    assert build._is_live({"date": "not-a-date"}, today) is True


def test_prune_dead_blog_links():
    live = {"/blog/alive/", "/de/blog/alive/"}
    body = ('<p><a href="/blog/alive/">A</a>, '
            '<a href="/blog/future/">F</a>, '
            '<a href="/de/blog/alive/">DA</a>, '
            '<a href="/de/blog/missing/">DM</a></p>')
    out = build._prune_dead_blog_links(body, live)
    assert '<a href="/blog/alive/">A</a>' in out      # live → kept
    assert '<a href="/de/blog/alive/">DA</a>' in out   # live → kept
    assert '<a href="/blog/future/"' not in out        # dead → unlinked…
    assert ">F</a>" not in out and ">F<" not in out and "F</p>" not in out
    assert "F," in out                                  # …but the text stays
    assert '<a href="/de/blog/missing/"' not in out and "DM" in out


def test_blog_preview_includes_future(monkeypatch):
    import datetime

    today = datetime.date(2026, 6, 23)
    monkeypatch.setattr(build, "BLOG_PREVIEW", True)
    # With preview on, even a far-future post is treated as live.
    assert build._is_live({"date": "2099-12-31"}, today) is True


def test_help_img_lang_falls_back_to_english():
    # A locale WITH its own screenshot set resolves to itself; en always does.
    assert build.help_img_lang("en") == "en"
    # A locale WITHOUT a screenshot dir must fall back to English, never emit a
    # broken img/help/<lang>/ path (the fr-help regression this guards against).
    assert build.help_img_lang("definitely-not-a-locale") == "en"


def test_every_language_help_screenshots_resolve():
    # For every site language, the screenshots the /help page references must
    # exist on disk — either the locale's own set or the English fallback. This
    # is the end-to-end guard: add a language to LANG_ORDER without a screenshot
    # set (as happened for fr) and this fails unless the fallback covers it.
    help_dir = os.path.join(REPO, "website", "img", "help")
    for lang in build.LANG_ORDER:
        ilang = build.help_img_lang(lang)
        for slug in build.HELP_STEPS + ["home"]:
            path = os.path.join(help_dir, ilang, f"{slug}.png")
            assert os.path.isfile(path), f"{lang} → missing {ilang}/{slug}.png"
