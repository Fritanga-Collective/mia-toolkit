"""Tests for the /institutions/ section and the patient-page banner.

Runs the full website build into a temp directory (build.main(site=...)) and
checks the generated HTML: institution pages exist with the hreflang cluster,
the sitemap lists them, the hard-rule copy is present (and the never-say
phrases are absent), and every patient homepage carries the banner.
"""

from __future__ import annotations

import importlib.util
import json
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_PY = os.path.join(REPO, "website", "build.py")


def _load_build():
    spec = importlib.util.spec_from_file_location("website_build_inst", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ModuleNotFoundError as e:  # markdown (build-time dep) missing
        if e.name != "markdown":
            raise
        pytest.skip(f"website build dep missing: {e}", allow_module_level=True)
    return mod


build = _load_build()

INST_PAGES = {
    "institutions/index.html": "en",
    "institutions/us/index.html": "en-US",
    "institutions/sg/index.html": "en-SG",
    "es/institutions/mx/index.html": "es-MX",
}


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    assert build.main(str(out)) == 0
    return out


def _read(site, rel):
    with open(os.path.join(site, rel), encoding="utf-8") as f:
        return f.read()


def test_institution_pages_generated_with_lang_and_hreflang(site):
    for rel, lang in INST_PAGES.items():
        page = _read(site, rel)
        assert f'<html lang="{lang}">' in page, rel
        assert '<body class="inst">' in page
        assert "{{" not in page, f"unrendered placeholder in {rel}"
        for hl in ("en-US", "en-SG", "es-MX", "x-default"):
            assert f'hreflang="{hl}"' in page, f"{rel} missing {hl}"
        url = "https://miatools.tech/" + rel.replace("index.html", "")
        assert f'<link rel="canonical" href="{url}">' in page
        # JSON-LD: Organization + SoftwareApplication with three offers.
        assert '"@type": "Organization"' in page
        assert '"@type": "SoftwareApplication"' in page
        assert page.count('"@type": "Offer"') == 3
        assert "aggregateRating" not in page


def test_sitemap_lists_institution_pages(site):
    sm = _read(site, "sitemap.xml")
    for rel in INST_PAGES:
        url = "https://miatools.tech/" + rel.replace("index.html", "")
        assert f"<loc>{url}</loc>" in sm


def test_market_hard_rules(site):
    us = _read(site, "institutions/us/index.html")
    assert "FD&amp;C §520(o)(1)(D)" in us or "FD&C §520(o)(1)(D)" in us
    assert "No BAA needed: we never receive or access PHI (HHS HIPAA FAQ 256)" in us
    sg = _read(site, "institutions/sg/index.html")
    assert "HSA GL-04-R4 (Dec 2025)" in sg
    assert "medical tourism" not in sg.lower()
    mx = _read(site, "es/institutions/mx/index.html")
    assert "No está destinado a fines de diagnóstico" in mx
    for banned in ("no es un dispositivo médico", "aprobado por COFEPRIS",
                   "exento de registro", "cumple NOM-024"):
        assert banned.lower() not in mx.lower(), banned
    # Windows signing row tells the truth until WINDOWS_SIGNED is flipped.
    if not build.WINDOWS_SIGNED:
        assert "not yet code-signed" in sg and "sin firma de código" in mx


def test_ctas_are_real_links(site):
    for rel in INST_PAGES:
        page = _read(site, rel)
        assert 'href="#"' not in page
    us = _read(site, "institutions/us/index.html")
    assert "mailto:support@miatools.tech?subject=" in us


def test_patient_homepages_have_banner_and_nav(site):
    for code in build.LANG_ORDER:
        rel = "index.html" if code == "en" else f"{code}/index.html"
        page = _read(site, rel)
        assert 'class="inst-banner"' in page, code
        assert page.count('href="/institutions/"') >= 2, code  # banner + nav
        with open(os.path.join(REPO, "website", "i18n", f"{code}.json"),
                  encoding="utf-8") as f:
            s = json.load(f)
        assert s["banner.inst_link"] in page
        # R6: the stale "signed installers arrive…" note is gone.
        assert "SmartScreen" in s["index.note"]


def _patient_pages(site):
    for code in build.LANG_ORDER:
        prefix = "" if code == "en" else f"{code}/"
        for page in build.PAGES:
            yield f"{prefix}{page}.html"


def test_fonts_self_hosted_no_google(site):
    """IBM Plex is served from /fonts/ (OFL licence alongside); no page makes a
    third-party font request, and patient pages load no web fonts at all."""
    fonts = os.path.join(site, "fonts")
    assert os.path.isfile(os.path.join(fonts, "OFL.txt"))
    woff2 = [f for f in os.listdir(fonts) if f.endswith(".woff2")]
    assert len(woff2) == 15
    css = _read(site, "styles.css")
    for f in woff2:
        assert f'url("/fonts/{f}")' in css, f
    assert css.count("font-display: swap") == len(woff2)
    for rel in INST_PAGES:
        page = _read(site, rel)
        assert "fonts.googleapis.com" not in page and "fonts.gstatic" not in page
        assert '<link rel="preload" href="/fonts/' in page
    for rel in _patient_pages(site):
        page = _read(site, rel)
        assert "fonts.googleapis.com" not in page, rel
        assert "/fonts/" not in page, rel
        assert 'class="inst"' not in page, rel


MARKET_PAGES = {  # market -> (page path, page language, brand language)
    "mx": ("es/institutions/mx/index.html", "es-MX", "es"),
    "us": ("institutions/us/index.html", "en-US", "en"),
    "sg": ("institutions/sg/index.html", "en-SG", "en"),
}
MARKET_URLS = {"mx": "/es/institutions/mx/", "us": "/institutions/us/",
               "sg": "/institutions/sg/"}


def test_one_language_per_market():
    markets = build.load_markets()
    assert {m: list(d["pages"]) for m, d in markets.items()} == {
        "mx": ["es"], "us": ["en"], "sg": ["en"]}
    for d in markets.values():
        assert "planned_langs" not in d


def test_no_other_language_variants(site):
    for rel in ("institutions/mx/index.html", "zh/institutions/sg/index.html",
                "ms/institutions/sg/index.html", "ta/institutions/sg/index.html",
                "es/institutions/us/index.html"):
        assert not os.path.exists(os.path.join(site, rel)), rel
    for rel in INST_PAGES:
        page = _read(site, rel)
        for hl in ("zh-SG", "ms-SG", "ta-SG", "zh-Hans"):
            assert f'hreflang="{hl}"' not in page, (rel, hl)
        for word in ("中文", "Melayu", "தமிழ்"):
            assert word not in page, (rel, word)


def test_header_has_one_market_menu(site):
    for m, (rel, _, lang) in MARKET_PAGES.items():
        page = _read(site, rel)
        shell = page[page.index('<header class="i-shell">'):page.index("</header>")]
        assert shell.count('<details class="i-market">') == 1, rel
        label = "Mercado" if lang == "es" else "Market"
        assert f'<span class="i-nav-label">{label}</span>' in shell
        for other, url in MARKET_URLS.items():
            cur = ' aria-current="page"' if other == m else ""
            assert f'href="{url}"' in shell, (rel, other)
            assert (f'href="{url}"{cur}>' in shell
                    or f'href="{url}" hreflang=' in shell), (rel, other)
        assert shell.count('aria-current="page"') == 1
        # No language switcher on institution pages.
        assert "Language" not in shell and "Idioma" not in shell
        assert "i-nav" not in shell.replace("i-nav-label", "")
        patients = "/es/" if lang == "es" else "/"
        assert f'class="i-patients" href="{patients}"' in shell
    hub = _read(site, "institutions/index.html")
    assert hub.count('<details class="i-market">') == 1
    assert 'aria-current="page"' not in hub[:hub.index("</header>")]
    assert '<script src="/inst.js" defer></script>' in hub
    assert os.path.isfile(os.path.join(site, "inst.js"))


def test_brand_constant_used(site):
    assert set(build.INST_BRAND) == {"en", "es"}
    for rel, (_, _, lang) in [(v[0], v) for v in MARKET_PAGES.values()] + [
            ("institutions/index.html", (None, None, "en"))]:
        page = _read(site, rel)
        brand = build.INST_BRAND[lang]
        esc = brand.replace("&", "&amp;")
        title = page[page.index("<title>") + 7:page.index("</title>")]
        assert title.endswith(" | " + esc), rel
        assert f'<meta property="og:site_name" content="{esc}">' in page
        assert f'"name": "{brand}"' in page  # JSON-LD Brand
        head, _, tail = esc.partition(" – ")
        assert f'class="i-brand"' in page and f"{head}<span> – {tail}</span>" in page
