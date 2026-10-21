"""Tests for the /institutions/ section and its links from patient pages.

Runs the full website build into a temp directory (build.main(site=...)) and
checks the generated HTML: institution pages exist with the hreflang cluster,
the sitemap lists them, the hard-rule copy is present (and the never-say
phrases are absent), and patient pages link "For clinics & hospitals".
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


def _rel(code, page):
    """Output file of a patient-register page (build.page_url → file)."""
    url = build.page_url(code, page).lstrip("/")
    return url + "index.html" if url.endswith("/") or not url else url


def test_patient_pages_have_institutions_nav_link_and_no_banner(site):
    for code in build.LANG_ORDER:
        with open(os.path.join(REPO, "website", "i18n", f"{code}.json"),
                  encoding="utf-8") as f:
            s = json.load(f)
        assert "banner.inst_link" not in s and "banner.inst_text" not in s
        target = "/es/institutions/mx/" if code == "es" else "/institutions/"
        for page in ("patients", "help", "support", "privacy", "stats"):
            html = _read(site, _rel(code, page))
            assert 'class="inst-banner"' not in html, (code, page)
            assert f'<a href="{target}">{s["nav.institutions"]}</a>' in html, (
                code, page)
        # R6: the stale "signed installers arrive…" note is gone.
        assert "SmartScreen" in s["index.note"]
    assert "inst-banner" not in _read(site, "styles.css")


def _patient_pages(site):
    for code in build.LANG_ORDER:
        for page in build.PAGES:
            yield _rel(code, page)


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
        label = "Región" if lang == "es" else "Region"
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
        patients = "/es/patients/" if lang == "es" else "/patients/"
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
        assert 'class="i-brand"' in page and f"{head}<span> – {tail}</span>" in page


def _spanish_pages(site):
    for root, _, files in os.walk(os.path.join(site, "es")):
        for f in files:
            if f.endswith(".html"):
                yield os.path.join(root, f)


def test_no_spanish_device_status_claim(site):
    """No Spanish page claims a device status ("no es un dispositivo médico");
    the approved non-medical-purpose wording is used instead (R5)."""
    pages = list(_spanish_pages(site))
    assert len(pages) > 10
    for path in pages:
        with open(path, encoding="utf-8") as f:
            text = f.read().lower()
        assert "no es un dispositivo médico" not in text, path
        assert "dispositivo médico" not in text, path
    with open(os.path.join(REPO, "website", "i18n", "es.json"),
              encoding="utf-8") as f:
        es = json.load(f)
    approved = ("no interpreta imágenes ni está destinada a fines de "
                "diagnóstico, prevención, monitoreo ni tratamiento")
    assert approved in es["footer.disclaimer"]
    assert approved in es["instp.foot_disclaimer"]
    mx = _read(site, "es/institutions/mx/index.html")
    assert "MIA Toolkit es una herramienta de gestión de archivos" in mx
    home = _read(site, "es/index.html")
    assert approved in home


def test_mx_procurement_documents_copy(site):
    mx = _read(site, "es/institutions/mx/index.html")
    assert '<h2 id="kit-h">Kit de Cumplimiento para IT</h2>' in mx
    assert ("Todo lo que piden para darnos de alta como proveedor: seguridad, "
            "instalación, términos de licencia y certificado.") in mx
    assert 'href="#kit">Ver el Kit de Cumplimiento para IT</a>' in mx
    for item in ("Ficha de seguridad", "Guía de instalación para TI",
                 "Términos de la licencia institucional",
                 "Certificado de licencia (muestra)"):
        assert f"<strong>{item}</strong></a>" in mx, item
    assert ">Solicitar el paquete completo por correo</a>" in mx
    assert "Disponibles a solicitud" not in mx
    for old in ("kit de compras", "documentos para compras y ti"):
        assert old not in mx.lower(), old
    with open(os.path.join(REPO, "website", "kit", "manifest.json"),
              encoding="utf-8") as f:
        assert json.load(f)["kit_name"]["es"] == "Kit de Cumplimiento para IT"
    us = _read(site, "institutions/us/index.html")
    assert '<h2 id="kit-h">Procurement kit</h2>' in us
    assert "available on request" not in us.lower()
    assert ">Request the full package by email</a>" in us


def _pilot_form(page):
    a = page.index('<form class="i-form" id="pilot-form"')
    return page[a:page.index("</form>", a)]


def test_pilot_form_present_with_hidden_fields_and_honeypot(site):
    for m, (rel, _, lang) in MARKET_PAGES.items():
        page = _read(site, rel)
        form = _pilot_form(page)
        assert 'method="post"' in form
        for hidden in ('name="form" value="pilot"', f'name="market" value="{m}"',
                       f'name="lang" value="{lang}"',
                       'name="utm_campaign" value=""'):
            assert f'<input type="hidden" {hidden}>' in form, (rel, hidden)
        # Honeypot: off-screen, hidden from assistive tech, not tabbable.
        assert '<div class="i-hp" aria-hidden="true">' in form
        assert 'name="website" type="text" tabindex="-1" autocomplete="off"' in form
        for name in ("name", "email", "organisation"):
            assert f'name="{name}"' in form and "required" in form
        assert 'name="email" type="email"' in form
        for name in ("role", "discs_per_month", "pacs", "message"):
            assert f'name="{name}"' in form, name
        for v, _ in build.INST_DISC_RANGES:
            assert f'<option value="{v}">' in form
        # Every visible control has a label.
        for fid in ("pf-name", "pf-email", "pf-organisation", "pf-role",
                    "pf-discs", "pf-pacs", "pf-message"):
            assert f'<label for="{fid}">' in form and f'id="{fid}"' in form
        privacy = "/es/privacy.html" if lang == "es" else "/privacy.html"
        assert f'href="{privacy}"' in form
        assert 'role="status"' in form
        # The pilot CTA is no longer just an email link.
        pilot = page[page.index('id="pilot"'):]
        assert 'class="i-btn i-btn-primary" href="mailto:' not in pilot
    mx = _pilot_form(_read(site, "es/institutions/mx/index.html"))
    assert "Correo de trabajo" in mx and "Aviso de privacidad" in mx


def test_pilot_form_disabled_until_endpoint_set(site):
    assert build.FORM_ENDPOINT == ""  # default until the Worker + R4 ship
    for rel, _, _ in MARKET_PAGES.values():
        form = _pilot_form(_read(site, rel))
        assert " action=" not in form, rel
        assert 'type="submit" disabled aria-describedby="pf-pending"' in form
        assert 'id="pf-pending"' in form
        assert 'href="mailto:support@miatools.tech?subject=' in form


def test_pilot_form_live_when_endpoint_set(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "FORM_ENDPOINT",
                        "https://forms.miatools.tech/submit")
    assert build.main(str(tmp_path)) == 0
    form = _pilot_form(_read(tmp_path, "institutions/us/index.html"))
    assert 'action="https://forms.miatools.tech/submit"' in form
    assert "disabled" not in form and 'id="pf-pending"' not in form


def test_thank_you_pages(site):
    for rel, lang, back in (
            ("institutions/thanks/index.html", "en", "/institutions/"),
            ("es/institutions/mx/gracias/index.html", "es-MX",
             "/es/institutions/mx/")):
        page = _read(site, rel)
        assert f'<html lang="{lang}">' in page
        assert '<meta name="robots" content="noindex">' in page
        assert "{{" not in page
        assert f'href="{back}"' in page
        assert '<details class="i-market">' in page
        assert 'aria-current="page"' not in page
    assert "Gracias. Recibimos su solicitud." in _read(
        site, "es/institutions/mx/gracias/index.html")
    sm = _read(site, "sitemap.xml")
    assert "thanks" not in sm and "gracias" not in sm
    # The Worker redirects to exactly these paths.
    with open(os.path.join(REPO, "workers", "forms", "src", "index.js"),
              encoding="utf-8") as f:
        worker = f.read()
    for path in build.INST_THANKS.values():
        assert f'"{path}"' in worker, path
    for v, _ in build.INST_DISC_RANGES:
        assert f'"{v}"' in worker, v


def test_inst_js_is_first_party_and_storage_free(site):
    js = _read(site, "inst.js")
    for banned in ("localStorage", "sessionStorage", "document.cookie",
                   "http://", "https://"):
        assert banned not in js, banned
    for rel in list(INST_PAGES) + ["institutions/thanks/index.html",
                                   "institutions/us/pilot/index.html",
                                   "es/institutions/mx/piloto/index.html"]:
        page = _read(site, rel)
        assert '<script src="/inst.js" defer></script>' in page
        assert '<script src="/track.js" defer></script>' in page
        # No inline <script> other than JSON-LD and the analytics beacon.
        for chunk in page.split("<script")[1:]:
            head = chunk[:chunk.index(">")]
            assert ("application/ld+json" in head or 'src="/inst.js"' in head
                    or 'src="/track.js"' in head
                    or "goatcounter" in head), head
