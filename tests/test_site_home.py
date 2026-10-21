"""Tests for the use-case chooser (/ and /<lang>/), the patient homepage at
/patients/, the institutional request form + modal, the funnel-event script
(track.js) and the procurement-kit PDF links.

Runs the full website build into a temp directory and checks the HTML.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(REPO, "website")
BUILD_PY = os.path.join(WEB, "build.py")


def _load_build():
    spec = importlib.util.spec_from_file_location("website_build_home", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ModuleNotFoundError as e:  # markdown (build-time dep) missing
        if e.name != "markdown":
            raise
        pytest.skip(f"website build dep missing: {e}", allow_module_level=True)
    return mod


build = _load_build()
BASE = "https://miatools.tech"
MARKET_URLS = {"mx": "/es/institutions/mx/", "us": "/institutions/us/",
               "sg": "/institutions/sg/"}
MARKET_PAGES = {"mx": "es/institutions/mx/index.html",
                "us": "institutions/us/index.html",
                "sg": "institutions/sg/index.html"}


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    assert build.main(str(out)) == 0
    return out


def _read(site, rel):
    with open(os.path.join(site, rel), encoding="utf-8") as f:
        return f.read()


def _strings(code):
    with open(os.path.join(WEB, "i18n", f"{code}.json"), encoding="utf-8") as f:
        return json.load(f)


def _root(code):
    return "" if code == "en" else f"{code}/"


# ───────────────────────────── chooser ─────────────────────────────

@pytest.mark.parametrize("code", build.LANG_ORDER)
def test_chooser_page(site, code):
    s = _strings(code)
    page = _read(site, f"{_root(code)}index.html")
    assert "{{" not in page
    assert '<a class="brand" href="%s">MIA Tools</a>' % build.page_url(code, "index") in page
    # Header nav: Help · Blog · Support · language selector.
    nav = page[page.index('<nav class="lang">'):page.index("</nav>")]
    for key in ("nav.help", "nav.blog", "nav.support"):
        assert f">{s[key]}</a>" in nav, key
    assert 'class="langsel"' in nav
    # Headline + subhead + the original hero image with its alt text.
    assert f"<h1>{s['home.h1']}</h1>" in page
    assert s["home.sub"] in page
    assert 'img/hero.jpg"' in page and f'alt="{s["index.hero_alt"]}"' in page
    # Two cards.
    assert page.count('<article class="choose-card') == 2
    assert 'class="choose-card choose-dark"' in page
    assert s["home.pat_h3"] in page and s["home.inst_h3"] in page
    # Patient card: one-click download (download.js) + How it works → /patients/.
    assert 'id="dl-primary"' in page and 'download.js"></script>' in page
    assert f'data-label-mac="{s["home.dl_mac"]}"' in page
    assert f'<a href="{build.page_url(code, "patients")}">{s["home.pat_more"]}' in page
    # Region select: labelled, exactly 3 options pointing at the market pages.
    form = page[page.index('<form class="region-form"'):page.index("</form>")]
    assert 'method="get"' in form and 'action="/institutions/"' in form
    assert f'<label for="region-select">{s["home.region_label"]}</label>' in form
    opts = re.findall(r'<option value="([^"]+)" data-market="(\w+)"', form)
    assert [(u, m) for u, m in opts] == [(MARKET_URLS[m], m) for m in ("mx", "us", "sg")]
    for m in ("mx", "us", "sg"):
        assert f">{s['home.region_' + m]}</option>" in form
    assert form.count(" selected") == 1
    assert 'type="submit"' in form and s["home.region_go"] in form
    # No-JS fallback: direct links in <noscript>.
    ns = page[page.index("<noscript>"):page.index("</noscript>")]
    for url in MARKET_URLS.values():
        assert f'<a href="{url}"' in ns
    assert 'home.js"></script>' in page and 'track.js"></script>' in page
    # Trust strip.
    for key in ("home.trust_offline", "home.trust_private", "home.trust_oss",
                "home.trust_os", "home.trust_langs"):
        assert s[key] in page, key
    # SEO: canonical + full hreflang cluster of chooser pages.
    assert f'<link rel="canonical" href="{BASE}{build.page_url(code, "index")}">' in page
    for c in build.LANG_ORDER:
        assert (f'hreflang="{build.HREFLANG[c]}" href="{BASE}'
                f'{build.page_url(c, "index")}"') in page
    assert f'hreflang="x-default" href="{BASE}/"' in page
    # JSON-LD: Organization + WebSite; the app schema lives on /patients/.
    assert '"@type": "Organization"' in page and '"@type": "WebSite"' in page
    assert '"@type": "SoftwareApplication"' not in page
    assert "/fonts/" not in page  # patient register: no web fonts


def test_chooser_region_defaults_follow_language(site):
    def selected(code):
        page = _read(site, f"{_root(code)}index.html")
        return re.search(r'data-market="(\w+)" selected', page).group(1)
    assert selected("es") == "mx"
    assert selected("en") == "us"
    assert selected("zh") == selected("ms") == selected("ta") == "sg"


def test_home_js_navigates_only_to_own_paths():
    with open(os.path.join(WEB, "home.js"), encoding="utf-8") as f:
        js = f.read()
    assert 'miaTrack("region_select:" + market)' in js
    assert "localStorage" not in js and "document.cookie" not in js
    assert "https://" not in js and "http://" not in js


# ──────────────────────────── /patients/ ────────────────────────────

@pytest.mark.parametrize("code", build.LANG_ORDER)
def test_patients_page_keeps_old_homepage(site, code):
    s = _strings(code)
    rel = f"{_root(code)}patients/index.html"
    page = _read(site, rel)
    assert "{{" not in page
    for key in ("index.h1", "index.lead", "index.why_h2", "index.steps_h2",
                "index.dl_h2"):
        assert s[key] in page, key
    assert 'id="download"' in page and 'id="dl-primary"' in page
    assert f'alt="{s["index.hero_alt"]}"' in page
    # Assets resolve from the nested directory.
    prefix = "../" if code == "en" else "../../"
    assert f'href="{prefix}styles.css"' in page
    assert f'src="{prefix}img/hero.jpg"' in page
    assert os.path.isfile(os.path.join(site, _root(code), "patients",
                                       prefix, "styles.css"))
    # Relative help link from i18n (index.note) is made root-absolute.
    assert 'href="help.html' not in page
    assert f'href="{build.page_url(code, "help")}#troubleshooting"' in page
    # Canonical + hreflang cluster of patient pages.
    url = BASE + build.page_url(code, "patients")
    assert f'<link rel="canonical" href="{url}">' in page
    for c in build.LANG_ORDER:
        assert (f'hreflang="{build.HREFLANG[c]}" href="{BASE}'
                f'{build.page_url(c, "patients")}"') in page
    assert f'hreflang="x-default" href="{BASE}/patients/"' in page
    assert '"@type": "SoftwareApplication"' in page
    assert f'"url": "{url}"' in page
    # Brand → chooser; nav link to clinics & hospitals; no banner.
    assert f'<a class="brand" href="{build.page_url(code, "index")}">' in page
    assert s["nav.institutions"] in page
    assert "inst-banner" not in page


def test_internal_home_links_point_to_patients(site):
    for code in build.LANG_ORDER:
        pat = build.page_url(code, "patients")
        for page in ("support", "privacy", "stats"):
            html = _read(site, f"{_root(code)}{page}.html")
            assert f'<a href="{pat}">' in html, (code, page)  # "← Back" link
            assert 'href="index.html' not in html
        help_ = _read(site, f"{_root(code)}help.html")
        assert f'href="{pat}#download"' in help_
    us = _read(site, "institutions/us/index.html")
    assert 'class="i-patients" href="/patients/"' in us


def test_sitemap_lists_chooser_and_patients(site):
    sm = _read(site, "sitemap.xml")
    for code in build.LANG_ORDER:
        for page in ("index", "patients"):
            assert f"<loc>{BASE}{build.page_url(code, page)}</loc>" in sm
    for banned in ("/pilot/", "/piloto/", "/request/", "/solicitud/", "/kit/",
                   ".pdf"):
        assert banned not in sm, banned


def test_lang_js_maps_patients_directory():
    with open(os.path.join(WEB, "lang.js"), encoding="utf-8") as f:
        js = f.read()
    assert 'var DIR_PAGES = ["patients"];' in js
    assert 'return prefix + page + "/";' in js
    assert 'if (page === "index") return prefix;' in js
    assert build.DIR_PAGES == {"patients"}


# ─────────────────────── request form + modal ───────────────────────

@pytest.mark.parametrize("m", ["mx", "us", "sg"])
def test_pilot_cta_and_dialog(site, m):
    page = _read(site, MARKET_PAGES[m])
    lang = "es" if m == "mx" else "en"
    s = _strings(lang)
    pilot = page[page.index('id="pilot"'):]
    cta = re.search(r'<a class="i-btn i-btn-primary" id="pilot-cta" ([^>]+)>([^<]+)</a>',
                    pilot)
    assert cta, m
    attrs, label = cta.groups()
    assert label == s["instp.pilot_cta"]
    assert f'href="{build.inst_pilot_url(lang, m)}"' in attrs
    assert 'data-request="pilot"' in attrs and f'data-market="{m}"' in attrs
    # The form lives in a labelled, closed <dialog> with a close button.
    assert '<dialog class="i-dialog" id="pilot-dialog" aria-labelledby="pf-h"' in pilot
    assert " open" not in pilot[pilot.index("<dialog"):pilot.index(">", pilot.index("<dialog"))]
    dlg = pilot[pilot.index("<dialog"):pilot.index("</dialog>")]
    assert f'class="i-dialog-close" type="button" data-close aria-label="{s["instp.dialog_close"]}"' in dlg
    assert '<form class="i-form" id="pilot-form"' in dlg
    assert '<input type="hidden" name="request_type" value="pilot">' in dlg
    assert page.count('id="pilot-form"') == 1


@pytest.mark.parametrize("m", ["mx", "us", "sg"])
def test_pricing_and_kit_ctas_open_request_form(site, m):
    page = _read(site, MARKET_PAGES[m])
    lang = "es" if m == "mx" else "en"
    s = _strings(lang)
    pricing = page[page.index('id="pricing"'):page.index('id="kit"')]
    assert 'href="mailto:' not in pricing
    for rtype, label in (("pricing_clinic", "instp.price_buy"),
                         ("pricing_hospital", "instp.price_invoice"),
                         ("pricing_network", "instp.price_quote"),
                         ("pricing_public", "instp.price_public_cta")):
        a = re.search(r'<a class="i-btn [^"]+" (href="[^"]+" data-request="%s"[^>]+)>([^<]+)</a>'
                      % rtype, pricing)
        assert a, (m, rtype)
        assert a.group(2) == s[label]
        assert f'href="{build.inst_request_url(lang, m, rtype)}"' in a.group(1)
        assert f'data-context="{s["instp.req_ctx_" + rtype]}"' in a.group(1).replace("&amp;", "&") \
            or f'data-context="{s["instp.req_ctx_" + rtype]}"' in a.group(1)
    kit = page[page.index('id="kit"'):page.index('id="pilot"')]
    assert 'data-request="kit"' in kit and s["instp.kit_cta"] in kit
    assert 'href="mailto:' not in kit
    # Context line in the modal form.
    assert f'<p class="i-form-context" id="pf-context">{s["instp.req_ctx_pilot"]}</p>' in page


def test_request_context_examples(site):
    en, es = _strings("en"), _strings("es")
    assert en["instp.req_ctx_pricing_hospital"] == "Request: Hospital license — US$499/year"
    assert es["instp.req_ctx_pricing_hospital"] == "Solicitud: Licencia Hospital — US$499/año"
    assert en["instp.req_submit_pricing_hospital"] == "Request an invoice"
    assert en["instp.req_submit_pricing_network"] == "Request a quote"
    assert en["instp.req_submit_pilot"] == "Request a pilot"


def test_request_types_match_worker():
    with open(os.path.join(REPO, "workers", "forms", "src", "index.js"),
              encoding="utf-8") as f:
        worker = f.read()
    for t in build.INST_REQUEST_TYPES:
        assert f'"{t}"' in worker, t
    with open(os.path.join(REPO, "workers", "forms", "schema.sql"),
              encoding="utf-8") as f:
        assert "request_type" in f.read()


@pytest.mark.parametrize("m", ["mx", "us", "sg"])
def test_no_js_request_pages(site, m):
    lang = "es" if m == "mx" else "en"
    s = _strings(lang)
    for rtype in build.INST_REQUEST_TYPES:
        url = build.inst_request_url(lang, m, rtype)
        page = _read(site, url.lstrip("/") + "index.html")
        assert '<meta name="robots" content="noindex">' in page, url
        assert f'<link rel="canonical" href="{BASE}{url}">' in page
        assert "{{" not in page
        assert f'<h1 id="pf-h">{s["instp.req_title_" + rtype]}</h1>' in page
        assert f'<input type="hidden" name="request_type" value="{rtype}">' in page
        assert f'<input type="hidden" name="market" value="{m}">' in page
        assert '<div class="i-hp" aria-hidden="true">' in page
        assert 'name="utm_campaign" value=""' in page
        assert s["instp.req_ctx_" + rtype].replace("&amp;", "&") in page.replace("&amp;", "&")
        if not build.FORM_ENDPOINT:
            assert 'type="submit" disabled' in page and 'id="pf-pending"' in page
        assert "<dialog" not in page
    assert build.inst_pilot_url("es", "mx") == "/es/institutions/mx/piloto/"
    assert build.inst_pilot_url("en", "sg") == "/institutions/sg/pilot/"
    assert build.inst_request_url("es", "mx", "pricing_hospital") == \
        "/es/institutions/mx/solicitud/hospital/"


def test_inst_js_modal_behaviour_static():
    with open(os.path.join(WEB, "inst.js"), encoding="utf-8") as f:
        js = f.read()
    for needle in ("showModal", 'typeof dialog.showModal !== "function"',
                   "e.preventDefault()", "opener.focus()", '"close"',
                   'funnel("cta_click"', 'funnel("form_open"',
                   'ev("form_start")', 'ev("submit_attempt")',
                   'ev("submit_success")', 'funnel("close_without_submit"',
                   "data-track"):
        assert needle in js, needle


# ───────────────────────────── track.js ─────────────────────────────

def test_track_js_is_name_only(site):
    src = open(os.path.join(WEB, "track.js"), encoding="utf-8").read()
    built = _read(site, "track.js")
    assert "__ANALYTICS_PROVIDER__" not in built
    assert f'var PROVIDER = "{build.ANALYTICS_PROVIDER}";' in built
    assert "window.miaTrack = function (name)" in src
    assert "goatcounter.count({ path: name, title: name, event: true })" in src
    assert "umami.track(name)" in src and "plausible(name)" in src
    # Names are sanitised; nothing else can be sent.
    assert "[^A-Za-z0-9_:-]" in src and "slice(0, 64)" in src
    for banned in ("localStorage", "sessionStorage", "document.cookie",
                   "fetch(", "XMLHttpRequest", "sendBeacon", "http://",
                   "https://"):
        assert banned not in src.replace("https://www.goatcounter.com/help/events", ""), banned


def test_tracking_calls_never_carry_personal_data():
    """Static check: every miaTrack/track/funnel call builds its name from
    literals and the market/type/doc codes only — never a form field value."""
    banned = re.compile(r"\.value\b|email|name\.|FormData|textContent")
    for fname in ("inst.js", "home.js"):
        js = open(os.path.join(WEB, fname), encoding="utf-8").read()
        calls = re.findall(r"(?:miaTrack|\btrack|\bfunnel|\bev)\(([^;]*)\);", js)
        assert calls, fname
        for args in calls:
            assert not banned.search(args), (fname, args)
    # fieldValue() is only ever used for the two hidden code fields.
    inst = open(os.path.join(WEB, "inst.js"), encoding="utf-8").read()
    for used in re.findall(r'fieldValue\(form, "(\w+)"\)', inst):
        assert used in ("request_type", "market"), used
    # Kit links carry only the document key.
    assert set(re.findall(r'data-track="([^"]+)"', open(BUILD_PY).read())) <= {
        "kit_download:{key}"}


def test_privacy_text_mentions_button_clicks(site):
    if not build.GOATCOUNTER:
        pytest.skip("analytics disabled")
    en = _read(site, "privacy.html")
    assert "aggregate page and button-click counts" in en
    for code in build.LANG_ORDER:
        assert "GoatCounter" in _read(site, f"{_root(code)}privacy.html")


# ──────────────────────────── kit PDFs ────────────────────────────

def test_kit_pdf_links_resolve(site):
    with open(os.path.join(WEB, "kit", "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    for m, rel in MARKET_PAGES.items():
        page = _read(site, rel)
        lang = "es" if m == "mx" else "en"
        kit = page[page.index('id="kit"'):page.index('id="pilot"')]
        links = re.findall(r'<a href="(/kit/[^"]+\.pdf)" type="application/pdf" '
                           r'hreflang="(\w+)" data-track="kit_download:([\w-]+)">', kit)
        assert len(links) == 4, m
        for href, hl, key in links:
            assert hl == lang and f"/kit/{lang}/" in href
            path = os.path.join(site, href.lstrip("/"))
            assert os.path.isfile(path), href
            doc = next(d for d in manifest["documents"]
                       if d["lang"] == lang and d["key"] == key)
            assert os.path.getsize(path) == doc["bytes"]
            assert doc["title"] in kit
        unit = "página" if lang == "es" else "page"
        assert re.search(r"PDF · [^·]+ · 1 %s · \d+ KB" % unit, kit)
        assert "available on request" not in kit.lower()


def test_bridge_status_label(site):
    us = _read(site, "institutions/us/index.html")
    mx = _read(site, "es/institutions/mx/index.html")
    assert ">Apply to our Pilot Program</span>" in us and "In design" not in us
    assert ">Aplica para el programa piloto</span>" in mx and "En diseño" not in mx
    assert 'href="https://bridge.miatools.tech/en/">' in us
    assert 'href="https://bridge.miatools.tech/">' in mx
    assert ("Imports outside studies straight into your PACS and pulls PACS "
            "studies onto clean patient media — on-premise, inside your network.") in us
    assert ("Importa estudios externos directo a su PACS y lleva estudios del "
            "PACS a medios limpios para el paciente — en sus instalaciones, "
            "dentro de su red.") in mx


BRIDGE_BANNED = ("in design", "en diseño", "not available yet",
                 "aún no está disponible", "separate, paid", "no price yet",
                 "todavía no tiene precio", "design partner", "socio de diseño",
                 "planned companion", "en planeación", "will live", "vivirá")


def test_no_hypothetical_bridge_copy_anywhere(site):
    for root, _, files in os.walk(site):
        for f in files:
            if not f.endswith(".html"):
                continue
            with open(os.path.join(root, f), encoding="utf-8") as fh:
                text = fh.read()
            if "bridge" not in text.lower():
                continue
            low = text.lower()
            for phrase in BRIDGE_BANNED:
                assert phrase not in low, (os.path.join(root, f), phrase)
