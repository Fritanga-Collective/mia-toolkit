#!/usr/bin/env python3
"""Static site generator for the MIA Toolkit website (stdlib only).

Renders templates/*.html × i18n/*.json into _site/: English at the root
(x-default), every other language under /<code>/. Generates the language
selector, canonical + hreflang cluster, Open Graph block, JSON-LD, the
sitemap, and redirect stubs for the pre-2026 flat URLs — so adding a language
is exactly one JSON file in i18n/.

Usage:  python3 website/build.py        (from the repo root or website/)
Output: website/_site/  (deployed by .github/workflows/pages.yml)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://mia-toolkit.fritanga.co"

# Language order = dropdown order. English lives at the site root (x-default).
LANG_ORDER = ["en", "es", "zh", "ms", "ta"]
HREFLANG = {"en": "en", "es": "es", "zh": "zh-Hans", "ms": "ms-SG",
            "ta": "ta-SG"}

PAGES = ["index", "support", "privacy"]
OG_PAGES = {"index", "support"}          # privacy has no social card (as before)

ASSETS = ["styles.css", "lang.js", "download.js", "support.js", "robots.txt",
          "CNAME", "img"]

# Legacy flat URLs -> new locations (meta-refresh + canonical stubs).
LEGACY = {
    "es.html": "/es/", "soporte.html": "/es/support.html",
    "privacidad.html": "/es/privacy.html",
    "zh.html": "/zh/", "support-zh.html": "/zh/support.html",
    "privacy-zh.html": "/zh/privacy.html",
}


def page_url(lang: str, page: str) -> str:
    """Root-absolute URL of a page in a language."""
    prefix = "/" if lang == "en" else f"/{lang}/"
    return prefix if page == "index" else f"{prefix}{page}.html"


def load_langs() -> dict[str, dict]:
    langs = {}
    for code in LANG_ORDER:
        path = os.path.join(HERE, "i18n", f"{code}.json")
        if not os.path.exists(path):
            print(f"  ! i18n/{code}.json missing — skipping {code}")
            continue
        with open(path, encoding="utf-8") as f:
            langs[code] = json.load(f)
    return langs


def langsel(langs: dict, lang: str, page: str) -> str:
    label = langs[lang].get("_selector_label", "Language")
    opts = []
    for code in langs:
        sel = " selected" if code == lang else ""
        opts.append(f'          <option value="{page_url(code, page)}"{sel}>'
                    f'{langs[code]["_lang_name"]}</option>')
    return (f'        <select class="langsel" aria-label="{label}"\n'
            '                onchange="if(this.value)location.href=this.value">\n'
            + "\n".join(opts) + "\n        </select>")


def head_seo(langs: dict, lang: str, page: str, s: dict) -> str:
    url = BASE + page_url(lang, page)
    lines = [f'  <link rel="canonical" href="{url}">']
    for code in langs:
        lines.append(f'  <link rel="alternate" hreflang="{HREFLANG[code]}" '
                     f'href="{BASE}{page_url(code, page)}">')
    lines.append(f'  <link rel="alternate" hreflang="x-default" '
                 f'href="{BASE}{page_url("en", page)}">')
    if page in OG_PAGES:
        title = s.get(f"{page}.og_title", s.get(f"{page}.title", ""))
        desc = s.get(f"{page}.meta_desc", "")
        lines += [
            '  <meta property="og:type" content="website">',
            '  <meta property="og:site_name" content="MIA Toolkit">',
            f'  <meta property="og:title" content="{title}">',
            f'  <meta property="og:description" content="{desc}">',
            f'  <meta property="og:url" content="{url}">',
            f'  <meta property="og:locale" content="{s["_og_locale"]}">',
        ]
        for code in langs:
            if code != lang:
                lines.append(f'  <meta property="og:locale:alternate" '
                             f'content="{langs[code]["_og_locale"]}">')
        lines += [
            f'  <meta property="og:image" content="{BASE}/img/social.jpg">',
            '  <meta property="og:image:width" content="1200">',
            '  <meta property="og:image:height" content="633">',
            f'  <meta property="og:image:alt" content="{title}">',
            '  <meta name="twitter:card" content="summary_large_image">',
            f'  <meta name="twitter:title" content="{title}">',
            f'  <meta name="twitter:description" content="{desc}">',
            f'  <meta name="twitter:image" content="{BASE}/img/social.jpg">',
        ]
    return "\n".join(lines)


def json_ld(lang: str, s: dict, page: str) -> str:
    if page != "index":
        return ""
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "MIA Toolkit",
        "operatingSystem": "macOS, Windows",
        "applicationCategory": "HealthApplication",
        "url": BASE + page_url(lang, "index"),
        "downloadUrl": "https://github.com/Fritanga-Collective/mia-toolkit/releases/latest",
        "description": s["index.meta_desc"],
        "image": f"{BASE}/img/social.jpg",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "publisher": {"@type": "Organization", "name": "Fritanga",
                      "url": "https://fritanga.co"},
    }
    return ('  <script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n  </script>")


def render(template: str, s: dict, computed: dict) -> str:
    out = template
    for key, value in computed.items():
        out = out.replace("{{" + key + "}}", value)

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in s:
            raise KeyError(f"missing i18n key: {key}")
        return s[key]

    out = re.sub(r"\{\{([\w.]+)\}\}", sub, out)
    return out


def redirect_stub(target: str) -> str:
    url = BASE + target
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={target}">
  <link rel="canonical" href="{url}">
  <title>Redirecting…</title>
</head>
<body>
  <p>This page has moved: <a href="{target}">{url}</a></p>
</body>
</html>
"""


def sitemap(langs: dict) -> str:
    entries = []
    for page in PAGES:
        for lang in langs:
            loc = BASE + page_url(lang, page)
            alts = [f'    <xhtml:link rel="alternate" hreflang="{HREFLANG[c]}"'
                    f' href="{BASE}{page_url(c, page)}"/>' for c in langs]
            alts.append(f'    <xhtml:link rel="alternate" hreflang="x-default"'
                        f' href="{BASE}{page_url("en", page)}"/>')
            entries.append("  <url>\n    <loc>" + loc + "</loc>\n"
                           + "\n".join(alts) + "\n  </url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(entries) + "\n</urlset>\n")


def main() -> int:
    langs = load_langs()
    if "en" not in langs:
        print("FATAL: i18n/en.json is required")
        return 1
    site = os.path.join(HERE, "_site")
    shutil.rmtree(site, ignore_errors=True)
    os.makedirs(site)

    templates = {p: open(os.path.join(HERE, "templates", f"{p}.html"),
                         encoding="utf-8").read() for p in PAGES}

    pages = 0
    for lang, s in langs.items():
        outdir = site if lang == "en" else os.path.join(site, lang)
        os.makedirs(outdir, exist_ok=True)
        prefix = "" if lang == "en" else "../"
        for page in PAGES:
            computed = {
                "P": prefix,
                "HEAD_SEO": head_seo(langs, lang, page, s),
                "JSON_LD": json_ld(lang, s, page),
                "LANGSEL": langsel(langs, lang, page),
            }
            html = render(templates[page], s, computed)
            with open(os.path.join(outdir, f"{page}.html"), "w",
                      encoding="utf-8") as f:
                f.write(html)
            pages += 1

    for legacy, target in LEGACY.items():
        with open(os.path.join(site, legacy), "w", encoding="utf-8") as f:
            f.write(redirect_stub(target))

    with open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap(langs))

    for asset in ASSETS:
        src = os.path.join(HERE, asset)
        if not os.path.exists(src):
            print(f"  ! asset missing: {asset}")
            continue
        dst = os.path.join(site, asset)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    print(f"✓ built {pages} pages × {len(langs)} languages "
          f"({', '.join(langs)}), {len(LEGACY)} redirects, sitemap, assets "
          f"→ {os.path.relpath(site)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
