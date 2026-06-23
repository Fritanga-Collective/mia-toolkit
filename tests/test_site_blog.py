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
        pytest.skip(f"website build dep missing: {e}")
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
    # The drawer post is a 3-language cluster (en/es/zh) sharing one slug.
    assert {p["lang"] for p in clusters["drawer-of-hospital-cds"]} == {
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
