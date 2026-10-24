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

import datetime
import html
import json
import os
import re
import shutil
import sys

import markdown  # build-time only (see website/requirements.txt)

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://miatools.tech"

# Language order = dropdown order. English lives at the site root (x-default).
LANG_ORDER = ["en", "es", "zh", "ms", "ta", "de", "fr"]
HREFLANG = {"en": "en", "es": "es", "zh": "zh-Hans", "ms": "ms-SG",
            "ta": "ta-SG", "de": "de", "fr": "fr"}

# "index" is the use-case chooser at / and /<lang>/ (templates/index.html);
# "patients" is the patient homepage at /patients/ and /<lang>/patients/
# (templates/patients.html, the former homepage). The patient page keeps its
# historical `index.*` i18n keys; the chooser's copy lives under `home.*`.
PAGES = ["index", "patients", "help", "support", "privacy", "stats"]
OG_PAGES = {"index", "patients", "help", "support", "privacy", "stats"}
I18N_PREFIX = {"index": "home", "patients": "index"}  # page -> i18n key prefix
# Social-card image per page: 1200x630 crops in img/og/ (1.91:1, the size
# Facebook, LinkedIn and X recommend). Pages not listed use OG_IMAGE_DEFAULT.
OG_IMAGE = {"index": "/img/og/mia-tools.jpg", "patients": "/img/og/patients.jpg",
            "help": "/img/og/patients.jpg", "blog": "/img/og/patients.jpg",
            "institutions": "/img/og/mia-tools.jpg"}
OG_IMAGE_DEFAULT = "/img/og/mia-tools.jpg"


def og_meta(title: str, desc: str, url: str, image: str, site_name: str,
            locale: str = "") -> list[str]:
    """OG + Twitter card lines for pages without their own head_seo
    (institution form and thank-you pages, redirect stubs). Escapes."""
    t, d = html.escape(title, quote=True), html.escape(desc, quote=True)
    img = image if image.startswith("http") else BASE + image
    lines = ['  <meta property="og:type" content="website">',
             f'  <meta property="og:site_name" content="{html.escape(site_name, quote=True)}">',
             f'  <meta property="og:title" content="{t}">',
             f'  <meta property="og:description" content="{d}">',
             f'  <meta property="og:url" content="{url}">']
    if locale:
        lines.append(f'  <meta property="og:locale" content="{locale}">')
    return lines + [
        f'  <meta property="og:image" content="{img}">',
        '  <meta property="og:image:width" content="1200">',
        '  <meta property="og:image:height" content="630">',
        f'  <meta property="og:image:alt" content="{t}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{t}">',
        f'  <meta name="twitter:description" content="{d}">',
        f'  <meta name="twitter:image" content="{img}">']
DIR_PAGES = {"patients"}  # emitted as <page>/index.html (directory URL)

# The 6 guided-setup screens the /help walkthrough documents, in order (the
# `home` screenshot lives in the Overview, not the HowTo). Slugs drive the
# anchor ids, the image filenames, and the i18n key suffixes (hyphen→underscore).
HELP_STEPS = ["welcome", "add-studies", "review", "documents",
              "build-deliver", "done"]
HELP_FAQ_N = 8                            # number of FAQ Q&A pairs (faq_q1…)


def help_img_lang(lang: str) -> str:
    """Language whose /help screenshots to use: the page's own language if a
    localized screenshot set exists (img/help/<lang>/), else fall back to
    English. Localized UI screenshots don't exist for every locale yet (e.g.
    fr), so without this fallback those pages render broken <img>s. English is
    the safe default — the walkthrough reads fine with English screenshots."""
    d = os.path.join(HERE, "img", "help", lang)
    return lang if os.path.isdir(d) else "en"

ASSETS = ["styles.css", "lang.js", "download.js", "support.js", "inst.js",
          "particles.js", "home.js", "track.js",
          "robots.txt",
          "fonts", "kit",
          "CNAME", "img", "version.json", "favicon.ico"]

# GoatCounter site code (e.g. "miatoolkit"). Empty = no analytics script is
# emitted AND the privacy policy keeps its "no analytics" wording. Setting it
# emits the cookieless beacon on every page and swaps in the privacy text that
# names GoatCounter — the build keeps the policy honest automatically.
GOATCOUNTER = "fritanga-collective"

# Which cookieless analytics receives the name-only funnel events sent by
# track.js (miaTrack("pilot_cta_click:sg")). "goatcounter" (today), "umami",
# "plausible", or "" for none — track.js is then a silent no-op. The build
# substitutes this into track.js and emits the matching script tag; switching
# provider = change this line (+ its site id below) and the privacy wording.
ANALYTICS_PROVIDER = "goatcounter" if GOATCOUNTER else ""
UMAMI_WEBSITE_ID = ""          # only used when ANALYTICS_PROVIDER == "umami"
PLAUSIBLE_DOMAIN = "miatools.tech"  # only used for "plausible"

# Legacy flat URLs -> new locations (meta-refresh + canonical stubs).
LEGACY = {
    "es.html": "/es/", "soporte.html": "/es/support.html",
    "privacidad.html": "/es/privacy.html",
    "zh.html": "/zh/", "support-zh.html": "/zh/support.html",
    "privacy-zh.html": "/zh/privacy.html",
    # Mexico is published in Spanish only; catch the guessable English path.
    "institutions/mx/index.html": "/es/institutions/mx/",
    "es/institutions/index.html": "/es/institutions/mx/",
}


def page_url(lang: str, page: str) -> str:
    """Root-absolute URL of a page in a language."""
    prefix = "/" if lang == "en" else f"/{lang}/"
    if page == "index":
        return prefix
    if page in DIR_PAGES:
        return f"{prefix}{page}/"
    return f"{prefix}{page}.html"


def site_links(lang: str) -> dict:
    """Root-absolute chrome links shared by every patient-register page, so a
    template renders the same at /, /<lang>/ and /<lang>/patients/."""
    return {
        # "/" or "/{lang}/" (the use-case chooser) — never "index.html",
        # which Google crawls as a separate URL ("Alternate page with proper
        # canonical tag").
        "HOME": page_url(lang, "index"),
        "PATIENTS": page_url(lang, "patients"),  # the patient homepage
        "HELP": page_url(lang, "help"),
        "SUPPORT": page_url(lang, "support"),
        "PRIVACY": page_url(lang, "privacy"),
        "STATS": page_url(lang, "stats"),
        # "For clinics & hospitals": the Spanish site goes straight to the
        # (Spanish) MX page; everyone else to the English hub.
        "INSTITUTIONS": "/es/institutions/mx/" if lang == "es"
                        else "/institutions/",
    }


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


def _favicon_lines() -> list[str]:
    # Favicons (generated by scripts/make_icons.py from the master logo).
    # Shared by head_seo (pages) and blog_head_seo (blog), so both stay in sync.
    return [
        '  <link rel="icon" href="/favicon.ico" sizes="48x48">',
        '  <link rel="icon" type="image/png" sizes="32x32" '
        'href="/img/favicon-32.png">',
        '  <link rel="icon" type="image/png" sizes="16x16" '
        'href="/img/favicon-16.png">',
        '  <link rel="icon" type="image/png" sizes="192x192" '
        'href="/img/icon-192.png">',
        '  <link rel="apple-touch-icon" sizes="180x180" '
        'href="/img/apple-touch-icon.png">',
    ]


def head_seo(langs: dict, lang: str, page: str, s: dict) -> str:
    url = BASE + page_url(lang, page)
    lines = [f'  <link rel="canonical" href="{url}">'] + _favicon_lines()
    for code in langs:
        lines.append(f'  <link rel="alternate" hreflang="{HREFLANG[code]}" '
                     f'href="{BASE}{page_url(code, page)}">')
    lines.append(f'  <link rel="alternate" hreflang="x-default" '
                 f'href="{BASE}{page_url("en", page)}">')
    if page in OG_PAGES:
        kp = I18N_PREFIX.get(page, page)
        title = s.get(f"{kp}.og_title", s.get(f"{kp}.title", ""))
        desc = s.get(f"{kp}.og_desc", s.get(f"{kp}.meta_desc", ""))
        og_img, og_w, og_h = OG_IMAGE.get(page, OG_IMAGE_DEFAULT), 1200, 630
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
            f'  <meta property="og:image" content="{BASE}{og_img}">',
            f'  <meta property="og:image:width" content="{og_w}">',
            f'  <meta property="og:image:height" content="{og_h}">',
            f'  <meta property="og:image:alt" content="{title}">',
            '  <meta name="twitter:card" content="summary_large_image">',
            f'  <meta name="twitter:title" content="{title}">',
            f'  <meta name="twitter:description" content="{desc}">',
            f'  <meta name="twitter:image" content="{BASE}{og_img}">',
        ]
    return "\n".join(lines)


def _ld_script(data: dict) -> str:
    return ('  <script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, indent=2)
            + "\n  </script>")


def json_ld(lang: str, s: dict, page: str) -> str:
    if page == "index":
        # The chooser: who we are (Organization) + the site itself (WebSite).
        org_id = BASE + "/#org"
        org = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": org_id,
            "name": "Fritanga",
            "url": "https://fritanga.co",
            "logo": f"{BASE}/img/icon-512.png",
            "email": INST_EMAIL,
            "brand": {"@type": "Brand", "name": "MIA Tools"},
        }
        site = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "MIA Tools",
            "url": BASE + page_url(lang, "index"),
            "inLanguage": HREFLANG[lang],
            "description": s["home.meta_desc"],
            "publisher": {"@id": org_id},
        }
        return _ld_script(org) + "\n" + _ld_script(site)

    if page == "patients":
        data = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "MIA Toolkit",
            "operatingSystem": "macOS, Windows",
            "applicationCategory": "HealthApplication",
            "url": BASE + page_url(lang, "patients"),
            "downloadUrl": "https://github.com/Fritanga-Collective/mia-toolkit/releases/latest",
            "description": s["index.meta_desc"],
            "image": BASE + OG_IMAGE["patients"],
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "publisher": {"@type": "Organization", "name": "Fritanga",
                          "url": "https://fritanga.co"},
        }
        return _ld_script(data)

    if page == "help":
        # Localized HowTo (the walkthrough) + FAQPage (the FAQ), both built from
        # the i18n strings so each locale gets its own structured data.
        url = BASE + page_url(lang, "help")
        ilang = help_img_lang(lang)   # localized screenshots if present, else en
        steps = []
        for slug in HELP_STEPS:
            k = slug.replace("-", "_")
            steps.append({
                "@type": "HowToStep",
                "name": s[f"help.s_{k}_h3"],
                "text": s[f"help.s_{k}_p"],
                "url": f"{url}#step-{slug}",
                "image": f"{BASE}/img/help/{ilang}/{slug}.png",
            })
        howto = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": s["help.howto_name"],
            "description": s["help.meta_desc"],
            "image": f"{BASE}/img/help/{ilang}/home.png",
            "totalTime": "PT15M",
            "step": steps,
        }
        faqpage = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": s[f"help.faq_q{i}"],
                 "acceptedAnswer": {"@type": "Answer", "text": s[f"help.faq_a{i}"]}}
                for i in range(1, HELP_FAQ_N + 1)
            ],
        }
        return _ld_script(howto) + "\n" + _ld_script(faqpage)

    return ""


# ───────────────────────── blog (/blog) ─────────────────────────
# A self-hosted, multilingual blog under /blog. Posts are one markdown file per
# (post, language) at content/blog/<lang>/<slug>.md, with a `---`-fenced
# front-matter block. The same slug across languages forms a translation
# "cluster" (drives hreflang + the post's language switcher). en lives at
# /blog/ and /blog/<slug>/; other langs under /<lang>/blog/…  — mirroring the
# rest of the site. Only `status: published` posts are emitted, and only for
# languages that also carry the blog.* i18n keys (see load_posts/main).

import datetime as _dt
import email.utils as _eut

# Every blog.* i18n key the blog templates/renderers consume. A locale must
# carry ALL of these to be eligible — render() raises KeyError on the first
# missing key, so a partial set (e.g. only blog.index_title) must still skip.
REQUIRED_BLOG_KEYS = frozenset({
    "blog.index_title", "blog.meta_desc", "blog.published",
    "blog.back", "blog.read_more",
})


def blog_index_url(lang: str) -> str:
    return "/blog/" if lang == "en" else f"/{lang}/blog/"


def blog_post_url(lang: str, slug: str) -> str:
    return blog_index_url(lang) + f"{slug}/"


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """Split a `---`-fenced front-matter block from the markdown body.

    A tiny stdlib parser (no YAML dep). Handles `key: value` and list values
    written as `key: [a, b]` or `key: ["a", "b"]`. Returns (meta, body).
    """
    if not text.startswith("---"):
        return {}, text
    # Front-matter is everything between the first two `---` lines.
    parts = text.split("\n", 1)[1].split("\n---", 1)
    if len(parts) != 2:
        return {}, text
    block, body = parts[0], parts[1]
    meta: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key, raw = key.strip(), raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            items = [x.strip().strip('"').strip("'")
                     for x in raw[1:-1].split(",")]
            meta[key] = [x for x in items if x]
        else:
            meta[key] = raw.strip('"').strip("'")
    return meta, body.lstrip("\n")


# Scheduling: a post goes live only when its `date` (ISO YYYY-MM-DD) has
# arrived. A `status: published` post with a FUTURE date is "scheduled" and
# held until then — combined with the daily Pages rebuild (pages.yml cron), it
# publishes itself on its date with no manual push. Set BLOG_PREVIEW=1 to
# include future-dated posts (local preview / staging the upcoming week).
# Parse explicitly so "0"/"false"/"" do NOT enable preview (a bare bool() on the
# env value would treat any non-empty string, incl. "0", as on).
BLOG_PREVIEW = os.environ.get("BLOG_PREVIEW", "").strip().lower() in {
    "1", "true", "yes", "on"}


def _blog_today() -> datetime.date:
    return datetime.datetime.now(datetime.timezone.utc).date()


def _is_live(meta: dict, today: datetime.date) -> bool:
    """A published post is live once its date is today or earlier (UTC).

    Future-dated → held unless BLOG_PREVIEW. A missing/malformed date is treated
    as live now (back-compatible) — main() warns so it doesn't go unnoticed."""
    if BLOG_PREVIEW:
        return True
    raw = (meta.get("date") or "").strip()
    try:
        return datetime.date.fromisoformat(raw) <= today
    except ValueError:
        return True  # no/!ISO date → publish now (warned in main)


def load_posts() -> tuple[list[dict], dict[str, list[dict]]]:
    """Walk content/blog/<lang>/*.md → live post dicts + slug clusters.

    Each post dict carries: lang, slug, title, date, summary, languages, tags,
    status, image, translation, body (raw markdown). Keeps only
    status == "published" posts whose date has arrived (see _is_live;
    BLOG_PREVIEW=1 includes scheduled ones). Returns (posts, clusters) where
    clusters maps slug → [post, …] (every live language for that slug), used for
    hreflang + the language switcher.
    """
    root = os.path.join(HERE, "content", "blog")
    posts: list[dict] = []
    if not os.path.isdir(root):
        return posts, {}
    today = _blog_today()
    for lang in sorted(os.listdir(root)):
        ldir = os.path.join(root, lang)
        if not os.path.isdir(ldir):
            continue
        for name in sorted(os.listdir(ldir)):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(ldir, name), encoding="utf-8") as f:
                meta, body = _parse_front_matter(f.read())
            if meta.get("status") != "published":
                continue
            if not _is_live(meta, today):
                continue  # scheduled for a future date — hold it
            try:
                datetime.date.fromisoformat((meta.get("date") or "").strip())
            except ValueError:
                print(f"  ! blog: {lang}/{name} has no/invalid ISO date "
                      f"({meta.get('date')!r}) — publishing now; set "
                      f"date: YYYY-MM-DD to schedule it")
            posts.append({
                "lang": lang,
                "slug": meta.get("slug") or name[:-3],
                "title": meta.get("title", ""),
                "date": meta.get("date", ""),
                "summary": meta.get("summary", ""),
                "languages": meta.get("languages", [lang]),
                "tags": meta.get("tags", []),
                "status": meta.get("status", ""),
                "image": meta.get("image", ""),
                # Optional social-card texts (≤60 / ≤155 chars); fall back to
                # title / summary, which stay the H1 and the meta description.
                "og_title": meta.get("og_title", ""),
                "og_description": meta.get("og_description", ""),
                "translation": meta.get("translation", ""),
                "body": body,
            })
    clusters: dict[str, list[dict]] = {}
    for p in posts:
        clusters.setdefault(p["slug"], []).append(p)
    # A translation without its own `image` reuses the cluster's (English
    # first), so every language shares the post's hero and social card.
    for cl in clusters.values():
        imgs = [q["image"] for q in sorted(cl, key=lambda q: q["lang"] != "en")
                if q["image"]]
        for q in cl:
            if not q["image"] and imgs:
                q["image"] = imgs[0]
    return posts, clusters


def _post_image_url(post: dict) -> str:
    """Absolute social-card image for a post: its own `image` front-matter
    (http→as-is, root-relative→prefixed with BASE) or "" when it has none."""
    img = post.get("image", "")
    if not img:
        return ""
    return img if img.startswith("http") else BASE + img


def blog_head_seo(post: dict, cluster: list[dict]) -> str:
    """Canonical + hreflang (scoped to the cluster's langs) + OG article."""
    lang, slug = post["lang"], post["slug"]
    url = BASE + blog_post_url(lang, slug)
    cluster_langs = [p["lang"] for p in cluster]
    lines = [f'  <link rel="canonical" href="{url}">'] + _favicon_lines()
    for code in cluster_langs:
        lines.append(f'  <link rel="alternate" hreflang="{HREFLANG[code]}" '
                     f'href="{BASE}{blog_post_url(code, slug)}">')
    if "en" in cluster_langs:  # x-default → English when a translation exists
        lines.append(f'  <link rel="alternate" hreflang="x-default" '
                     f'href="{BASE}{blog_post_url("en", slug)}">')
    title = html.escape(post.get("og_title") or post["title"], quote=True)
    desc = html.escape(post.get("og_description") or post["summary"],
                       quote=True)
    custom = _post_image_url(post)
    image = custom or BASE + OG_IMAGE["blog"]
    lines += [
        '  <meta property="og:type" content="article">',
        '  <meta property="og:site_name" content="MIA Toolkit">',
        f'  <meta property="og:title" content="{title}">',
        f'  <meta property="og:description" content="{desc}">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="article:published_time" content="{post["date"]}">',
        f'  <meta property="og:image" content="{image}">',
    ]
    if not custom:  # 1200x630 describes the default card only
        lines += [
            '  <meta property="og:image:width" content="1200">',
            '  <meta property="og:image:height" content="630">',
        ]
    lines += [
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{title}">',
        f'  <meta name="twitter:description" content="{desc}">',
        f'  <meta name="twitter:image" content="{image}">',
    ]
    return "\n".join(lines)


def blog_json_ld(post: dict, cluster: list[dict]) -> str:
    url = BASE + blog_post_url(post["lang"], post["slug"])
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"],
        "datePublished": post["date"],
        "inLanguage": HREFLANG.get(post["lang"], post["lang"]),
        "description": post["summary"],
        "image": _post_image_url(post) or BASE + OG_IMAGE["blog"],
        "author": {"@type": "Organization", "name": "Fritanga",
                   "url": "https://fritanga.co"},
        "publisher": {"@type": "Organization", "name": "Fritanga",
                      "url": "https://fritanga.co"},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
    }
    out = _ld_script(data)
    faq = blog_faq(post["body"])
    if faq:
        out += "\n" + _ld_script({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "inLanguage": HREFLANG.get(post["lang"], post["lang"]),
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in faq
            ],
        })
    return out


# The FAQ section of a post is its LAST `## ` heading when that heading is one
# of these (one per blog language). Each Q&A is a paragraph whose first line is
# a bold question (`**…**`) and whose remaining lines are the answer.
BLOG_FAQ_HEADINGS = frozenset({
    "FAQ", "Preguntas frecuentes", "Häufige Fragen", "Questions fréquentes",
    "Soalan Lazim", "அடிக்கடி கேட்கப்படும் கேள்விகள்", "常见问题",
})
_FAQ_Q_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
_TAG_RE = re.compile(r"<[^>]+>")


def blog_faq(body_md: str) -> list[tuple[str, str]]:
    """(question, plain-text answer) pairs from a post's FAQ section, for the
    FAQPage JSON-LD. Empty when the post has no FAQ section (or < 1 pair)."""
    heads = list(re.finditer(r"(?m)^## +(.+?)\s*$", body_md))
    if not heads or heads[-1].group(1).strip() not in BLOG_FAQ_HEADINGS:
        return []
    section = body_md[heads[-1].end():]
    pairs = []
    for para in re.split(r"\n\s*\n", section.strip()):
        first, _, rest = para.strip().partition("\n")
        m = _FAQ_Q_RE.match(first.strip())
        if not m or not rest.strip():
            continue
        answer = markdown.markdown(rest.strip())
        answer = html.unescape(_TAG_RE.sub("", answer))
        pairs.append((m.group(1).strip(), " ".join(answer.split())))
    return pairs


def _blog_langsel(langs: dict, current_lang: str, target: dict) -> str:
    """Render a language dropdown over ONLY the languages in `target` (the
    Wikipedia model: offer just the languages this content actually exists in,
    so switching always lands on a real translation). `target` maps lang code →
    URL. Omitted entirely when there's nothing to switch to (≤1 language)."""
    codes = [c for c in LANG_ORDER if c in target]
    if len(codes) <= 1:
        return ""
    label = langs[current_lang].get("_selector_label", "Language")
    opts = []
    for code in codes:
        sel = " selected" if code == current_lang else ""
        opts.append(f'          <option value="{target[code]}"{sel}>'
                    f'{langs[code]["_lang_name"]}</option>')
    return (f'        <select class="langsel" aria-label="{label}"\n'
            '                onchange="if(this.value)location.href=this.value">\n'
            + "\n".join(opts) + "\n        </select>")


def blog_langsel(cluster: list[dict], langs: dict, current_lang: str) -> str:
    """Post selector: only the languages this post is actually translated into,
    each pointing at the real translation (never the homepage, never a 404)."""
    slug = cluster[0]["slug"]
    target = {p["lang"]: blog_post_url(p["lang"], slug) for p in cluster}
    return _blog_langsel(langs, current_lang, target)


def _blog_chrome(lang: str, prefix: str) -> dict:
    """Root-relative nav/footer links + asset prefix shared by both templates."""
    return {"P": prefix, **site_links(lang),
            "BLOG_INDEX": blog_index_url(lang)}


# Internal blog-post links in a post body: /blog/<slug>/ or /<lang>/blog/<slug>/.
_BLOG_LINK_RE = re.compile(
    r'<a href="(/(?:[a-z]{2}/)?blog/[a-z0-9-]+/)"[^>]*>(.*?)</a>', re.S)


def _prune_dead_blog_links(body: str, live_urls: set[str]) -> str:
    """Unlink internal blog cross-links whose target isn't live yet (keep the
    text). A post can link a sibling that's scheduled for a later date or that
    has no translation in this language; rather than ship a 404, we drop just
    the <a> wrapper. The link re-activates automatically on the daily rebuild
    once the target publishes — no manual upkeep, and cross-links can't rot."""
    return _BLOG_LINK_RE.sub(
        lambda m: m.group(0) if m.group(1) in live_urls else m.group(2), body)


def render_post(post: dict, cluster: list[dict], langs: dict,
                template: str, live_urls: set[str] | None = None) -> str:
    s = langs[post["lang"]]
    body = markdown.markdown(post["body"],
                             extensions=["extra", "toc", "sane_lists"])
    if live_urls is not None:
        body = _prune_dead_blog_links(body, live_urls)
    # Footer note on translated posts inviting readers to improve the wording.
    # Localized via blog.tr_note where present, with an English fallback.
    if post.get("translation") == "machine":
        note = s.get("blog.tr_note", "Translations welcome — corrections at "
                     "<a href=\"mailto:support@miatools.tech\">"
                     "support@miatools.tech</a>.")
        body += f'\n<p class="tr-note">{note}</p>'
    prefix = "../../" if post["lang"] == "en" else "../../../"
    computed = _blog_chrome(post["lang"], prefix)
    hero = ""
    if post.get("image"):
        alt = html.escape(post["title"], quote=True)
        hero = (f'      <figure class="blog-hero"><img src="{post["image"]}" '
                f'alt="{alt}" loading="lazy"></figure>')
    computed.update({
        "HEAD_SEO": blog_head_seo(post, cluster),
        "JSON_LD": blog_json_ld(post, cluster),
        "LANGSEL": blog_langsel(cluster, langs, post["lang"]),
        "BLOG_TITLE": html.escape(post["title"]),
        "BLOG_SUMMARY": html.escape(post["summary"], quote=True),
        "BLOG_DATE": post["date"],
        "BLOG_IMAGE": hero,
        "BLOG_BODY": body,
    })
    return render(template, s, computed)


def render_blog_index(lang: str, posts: list[dict], langs: dict,
                      template: str) -> str:
    s = langs[lang]
    mine = sorted((p for p in posts if p["lang"] == lang),
                  key=lambda p: p["date"], reverse=True)  # newest first
    items = []
    for p in mine:
        url = blog_post_url(lang, p["slug"])
        # Decorative thumbnail: a bare <img alt=""> (not a link) — the title link
        # is the single click/tab target, and a non-interactive image needs no
        # aria-hidden/tabindex, so there's no double-target or a11y conflict.
        thumb = (f'          <img class="blog-thumb" src="{p["image"]}" alt="" '
                 f'loading="lazy">\n') if p.get("image") else ""
        items.append(
            '        <li class="blog-item">\n'
            + thumb +
            '          <div class="blog-item-body">\n'
            f'            <h2><a href="{url}">{html.escape(p["title"])}</a></h2>\n'
            f'            <p class="post-meta">{s["blog.published"]} '
            f'<time datetime="{p["date"]}">{p["date"]}</time></p>\n'
            f'            <p>{html.escape(p["summary"])}</p>\n'
            f'            <p><a href="{url}">{s["blog.read_more"]}</a></p>\n'
            '          </div>\n'
            '        </li>')
    prefix = "../" if lang == "en" else "../../"
    computed = _blog_chrome(lang, prefix)
    computed.update({
        "HEAD_SEO": blog_index_head_seo(lang, langs, posts),
        "JSON_LD": "",
        "LANGSEL": blog_index_langsel(lang, langs, posts),
        "BLOG_INDEX_TITLE": s["blog.index_title"],
        "BLOG_LIST": "\n".join(items),
    })
    return render(template, s, computed)


def _blog_langs(posts: list[dict]) -> list[str]:
    """Languages (in LANG_ORDER) that have ≥1 published post."""
    have = {p["lang"] for p in posts}
    return [c for c in LANG_ORDER if c in have]


def blog_index_head_seo(lang: str, langs: dict, posts: list[dict]) -> str:
    """Canonical + hreflang for a blog index, scoped to langs that have posts."""
    url = BASE + blog_index_url(lang)
    codes = _blog_langs(posts)
    lines = [f'  <link rel="canonical" href="{url}">'] + _favicon_lines()
    for code in codes:
        lines.append(f'  <link rel="alternate" hreflang="{HREFLANG[code]}" '
                     f'href="{BASE}{blog_index_url(code)}">')
    if "en" in codes:
        lines.append(f'  <link rel="alternate" hreflang="x-default" '
                     f'href="{BASE}{blog_index_url("en")}">')
    title = html.escape(langs[lang]["blog.index_title"], quote=True)
    desc = html.escape(langs[lang].get("blog.og_desc",
                                       langs[lang]["blog.meta_desc"]),
                       quote=True)
    img = BASE + OG_IMAGE["blog"]
    lines += [
        '  <meta property="og:type" content="website">',
        '  <meta property="og:site_name" content="MIA Toolkit">',
        f'  <meta property="og:title" content="{title}">',
        f'  <meta property="og:description" content="{desc}">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="og:image" content="{img}">',
        '  <meta property="og:image:width" content="1200">',
        '  <meta property="og:image:height" content="630">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{title}">',
        f'  <meta name="twitter:description" content="{desc}">',
        f'  <meta name="twitter:image" content="{img}">',
    ]
    return "\n".join(lines)


def blog_index_langsel(lang: str, langs: dict, posts: list[dict]) -> str:
    """Index selector: only the languages that actually have a blog index
    (≥1 published post), each pointing at that language's index."""
    target = {c: blog_index_url(c) for c in _blog_langs(posts)}
    return _blog_langsel(langs, lang, target)


def rss_feed(en_posts: list[dict]) -> str:
    """Valid RSS 2.0 for the English blog (newest first). En only for now."""
    items = []
    for p in sorted(en_posts, key=lambda p: p["date"], reverse=True):
        link = BASE + blog_post_url("en", p["slug"])
        try:  # date is YYYY-MM-DD → RFC-822 pubDate
            d = _dt.datetime.strptime(p["date"], "%Y-%m-%d")
            pub = _eut.format_datetime(d.replace(tzinfo=_dt.timezone.utc))
        except ValueError:
            pub = ""
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(p['title'])}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid>{link}</guid>\n"
            + (f"      <pubDate>{pub}</pubDate>\n" if pub else "")
            + f"      <description>{html.escape(p['summary'])}</description>\n"
            "    </item>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0">\n'
            '  <channel>\n'
            '    <title>The MIA Toolkit Blog</title>\n'
            f'    <link>{BASE}/blog/</link>\n'
            '    <description>Plain-language guides on organizing your medical '
            'imaging.</description>\n'
            '    <language>en</language>\n'
            f'    <atom:link xmlns:atom="http://www.w3.org/2005/Atom" '
            f'href="{BASE}/blog/feed.xml" rel="self" type="application/rss+xml"/>\n'
            + "\n".join(items)
            + "\n  </channel>\n</rss>\n")


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


def redirect_stub(target: str, card: str = "") -> str:
    """Meta-refresh stub. `card` is the target page's og:/twitter: lines, so
    a link shared to the old URL still previews like the page it opens."""
    url = BASE + target
    card = f"\n{card}" if card else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={target}">
  <link rel="canonical" href="{url}">{card}
  <title>Redirecting…</title>
</head>
<body>
  <p>This page has moved: <a href="{target}">{url}</a></p>
</body>
</html>
"""


def _iso_date(raw: str) -> str:
    """A normalized YYYY-MM-DD, or "" when `raw` isn't a valid ISO date.

    load_posts() deliberately publishes a post whose front-matter date is
    missing or malformed — it warns and carries on — so an unvalidated value
    reaches the sitemap: "not-a-date" emits a <lastmod> the sitemap spec
    rejects, and a value containing & or < makes sitemap.xml not well-formed,
    taking every URL down with it. Validate at the choke point instead."""
    try:
        return datetime.date.fromisoformat((raw or "").strip()).isoformat()
    except (ValueError, TypeError):
        return ""


def _sitemap_url(loc: str, alt_pairs: list[tuple[str, str]],
                 lastmod: str = "") -> str:
    """One <url> entry with xhtml:link hreflang alternates (code, href).

    `lastmod` is emitted only where we hold a real date — blog posts carry one
    in front matter. Static pages deliberately omit it rather than stamp the
    build date on every URL: a sitemap whose lastmod always reads "now" is one
    Google learns to distrust, which costs more than the tag gains."""
    alts = [f'    <xhtml:link rel="alternate" hreflang="{hl}" href="{href}"/>'
            for hl, href in alt_pairs]
    iso = _iso_date(lastmod)
    mod = f"\n    <lastmod>{iso}</lastmod>" if iso else ""
    return ("  <url>\n    <loc>" + loc + "</loc>" + mod + "\n"
            + "\n".join(alts) + "\n  </url>")


def sitemap(langs: dict, posts: list[dict] | None = None,
            clusters: dict | None = None,
            inst_alts: list[tuple[str, str]] | None = None) -> str:
    entries = []
    # Institutions: one entry per emitted page, each listing the whole
    # regional-variant cluster (hub = en + x-default). See inst_cluster().
    if inst_alts:
        for loc in dict.fromkeys(href for _hl, href in inst_alts):
            entries.append(_sitemap_url(loc, inst_alts))
    for page in PAGES:
        for lang in langs:
            loc = BASE + page_url(lang, page)
            pairs = [(HREFLANG[c], f"{BASE}{page_url(c, page)}") for c in langs]
            pairs.append(("x-default", f'{BASE}{page_url("en", page)}'))
            entries.append(_sitemap_url(loc, pairs))

    # Blog: one entry per index (langs with posts) + one per published post,
    # each with hreflang alternates scoped to its cluster / available langs.
    if posts:
        blog_langs = _blog_langs(posts)
        for lang in blog_langs:
            loc = BASE + blog_index_url(lang)
            pairs = [(HREFLANG[c], f"{BASE}{blog_index_url(c)}")
                     for c in blog_langs]
            if "en" in blog_langs:
                pairs.append(("x-default", f'{BASE}{blog_index_url("en")}'))
            # _iso_date first: max() over raw strings would rank a
            # malformed value like "not-a-date" above every real date.
            newest = max((_iso_date(p["date"])
                          for p in posts if p["lang"] == lang), default="")
            entries.append(_sitemap_url(loc, pairs, newest))
        # Only reference languages whose blog pages were actually emitted
        # (posts is already filtered to the guard-passing `ready` langs) — else
        # a post that exists for a skipped language would emit an hreflang
        # alternate pointing at a page that was never built.
        emitted_langs = {p["lang"] for p in posts}
        for p in posts:
            loc = BASE + blog_post_url(p["lang"], p["slug"])
            cl = (clusters or {}).get(p["slug"], [p])
            cl_langs = [c for c in LANG_ORDER
                        if c in {q["lang"] for q in cl} and c in emitted_langs]
            pairs = [(HREFLANG[c], f"{BASE}{blog_post_url(c, p['slug'])}")
                     for c in cl_langs]
            if "en" in cl_langs:
                pairs.append(("x-default",
                              f'{BASE}{blog_post_url("en", p["slug"])}'))
            entries.append(_sitemap_url(loc, pairs, p["date"]))

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + "\n".join(entries) + "\n</urlset>\n")


def load_metrics():
    path = os.path.join(HERE, "data", "metrics.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def stats_chart_svg(snapshots, pending_text: str) -> str:
    """Build-time SVG bar chart of downloads/day — zero client JS."""
    if len(snapshots) < 2:
        return f'        <p class="note">{pending_text}</p>'
    days = []
    for prev, cur in zip(snapshots, snapshots[1:]):
        days.append((cur["date"], max(0, cur["total"] - prev["total"])))
    days = days[-60:]
    peak = max((n for _d, n in days), default=1) or 1
    w, h, pad = 640, 140, 4
    bw = max(2, (w - 2 * pad) // max(len(days), 1) - 2)
    bars = []
    for i, (d, n) in enumerate(days):
        bh = int((h - 30) * n / peak)
        x = pad + i * (bw + 2)
        bars.append(f'<rect x="{x}" y="{h - 20 - bh}" width="{bw}" '
                    f'height="{bh}" fill="#2c5282"><title>{d}: {n}</title></rect>')
    first, last = days[0][0], days[-1][0]
    return (f'        <svg viewBox="0 0 {w} {h}" role="img" class="stats-chart" '
            f'preserveAspectRatio="xMidYMid meet">'
            + "".join(bars)
            + f'<text x="{pad}" y="{h - 4}" font-size="11" fill="#4a5568">{first}</text>'
            + f'<text x="{w - pad}" y="{h - 4}" font-size="11" fill="#4a5568" '
              f'text-anchor="end">{last}</text></svg>')


def stats_blocks(metrics, s: dict) -> dict:
    empty4 = '            <tr><td colspan="4">—</td></tr>'
    empty2 = '            <tr><td colspan="2">—</td></tr>'
    if not metrics:
        return {"STATS_UPDATED": "—", "STATS_TOTAL": "—", "STATS_CHART": "",
                "STATS_TABLE": empty4, "STATS_VIEWS": "—", "STATS_UNIQUES": "—",
                "STATS_REFERRERS": empty2}
    snaps = metrics.get("snapshots", [])
    latest = snaps[-1] if snaps else {}
    rows = []
    for r in metrics.get("releases", []):
        mac = sum(a["count"] for a in r["assets"] if a["name"].endswith(".dmg"))
        win = sum(a["count"] for a in r["assets"] if a["name"].endswith(".exe"))
        rows.append(f'            <tr><td>{html.escape(r["tag"])}</td>'
                    f'<td>{mac:,}</td>'
                    f'<td>{win:,}</td><td>{mac + win:,}</td></tr>')
    rows = rows or [empty4]
    refs = [f'            <tr><td>{html.escape(r["referrer"])}</td>'
            f'<td>{r["count"]:,}</td></tr>'
            for r in metrics.get("referrers", [])] or [empty2]
    return {
        "STATS_UPDATED": metrics.get("updated", "—"),
        "STATS_TOTAL": f'{latest.get("total", 0):,}',
        "STATS_CHART": stats_chart_svg(snaps, s.get("stats.chart_pending", "")),
        "STATS_TABLE": "\n".join(rows),
        "STATS_VIEWS": f'{latest.get("views14", 0):,}',
        "STATS_UNIQUES": f'{latest.get("uniques14", 0):,}',
        "STATS_REFERRERS": "\n".join(refs),
    }


GC_SNIPPET = ('  <script data-goatcounter="https://{code}.goatcounter.com/count"\n'
              '          async src="https://gc.zgo.at/count.js"></script>\n')
ANALYTICS_SNIPPETS = {
    "goatcounter": GC_SNIPPET,
    "umami": ('  <script defer src="https://cloud.umami.is/script.js"\n'
              '          data-website-id="{code}"></script>\n'),
    "plausible": ('  <script defer data-domain="{code}"\n'
                  '          src="https://plausible.io/js/script.js"></script>\n'),
}


def _analytics_snippet() -> str:
    code = {"goatcounter": GOATCOUNTER, "umami": UMAMI_WEBSITE_ID,
            "plausible": PLAUSIBLE_DOMAIN}.get(ANALYTICS_PROVIDER, "")
    if not (ANALYTICS_PROVIDER and code):
        return ""
    return ANALYTICS_SNIPPETS[ANALYTICS_PROVIDER].format(code=code)


def _inject_gc(html_str: str) -> str:
    """Inject the cookieless analytics beacon (ANALYTICS_PROVIDER; GoatCounter
    today) before the LAST </body> (if enabled). Using the last close tag is
    robust to a stray '</body>' appearing inside blog Markdown (raw HTML),
    which would otherwise misplace the beacon."""
    snippet = _analytics_snippet()
    if not snippet:
        return html_str
    i = html_str.rfind("</body>")
    if i == -1:
        return html_str + snippet
    return html_str[:i] + snippet + html_str[i:]


# ───────────────────── institutions (/institutions/) ─────────────────────
# The institutional storefront (INSTITUTIONS-SITE-SPEC). One template
# (templates/institutions.html) × one data file per market (markets/<m>.json).
# Each market has exactly ONE page language (MX = es-MX, US = en-US,
# SG = en-SG); markets/<m>.json lists it under "pages" and the build refuses a
# market with more than one. Shared copy lives in the instp.* keys of
# i18n/<lang>.json; market-specific copy (m.* strings, use cases, compliance
# rows, trust assets) lives in the market file. URLs nest like the rest of the
# site: English at /institutions/<m>/, others at /<lang>/institutions/<m>/. A
# neutral English hub with a market picker sits at /institutions/. All pages
# form ONE hreflang cluster (es-MX / en-US / en-SG) with the hub as x-default.
# A page whose language lacks any instp.* key is skipped with a warning
# instead of crashing the build.

INST_MARKETS = ["mx", "us", "sg"]   # market-menu order

# Brand shown in the institutional header, <title> suffixes, og:site_name and
# the JSON-LD Brand. Naming is still being decided: this is the one line to
# change. Keyed by page language.
INST_BRAND = {"en": "MIA Tools – Clinics & Hospitals",
              "es": "MIA Tools – Clínicas y Hospitales"}


def inst_brand(lang: str) -> str:
    return INST_BRAND.get(lang, INST_BRAND["en"])


def inst_title(title: str, lang: str) -> str:
    """Page <title>: the page's own title + the brand suffix."""
    return f"{title} | {inst_brand(lang)}"

# Windows Authenticode signing status (launch-readiness R1). False renders the
# honest "not yet signed" compliance row; flip to True once a signed release
# ships and the row switches to instp.sign_signed in every language.
WINDOWS_SIGNED = False

INST_EMAIL = "support@miatools.tech"

# Pilot-request form backend (the Cloudflare Worker in workers/forms/), e.g.
# "https://forms.miatools.tech/submit". Empty = not deployed yet: the form
# still renders, but its submit button is disabled and a visible note offers
# the mailto fallback, so nothing silently breaks. Set it only after the
# Worker is live AND the privacy-policy update (launch-readiness R4) ships.
FORM_ENDPOINT = "https://forms.miatools.tech/submit"

# Where the Worker 303-redirects a no-JS submission (keep in sync with
# THANKS in workers/forms/src/index.js). Not indexed, not in the sitemap.
INST_THANKS = {"en": "/institutions/thanks/",
               "es": "/es/institutions/mx/gracias/"}

# One request form, several entry points. Every CTA that asks us for
# something (the pilot CTA, each pricing tier, the procurement kit) opens the
# SAME form in a <dialog> on the market page; the form's hidden request_type
# says which (keep in sync with REQUEST_TYPES in workers/forms/src/index.js).
# Without JS each CTA is a real link to a standalone, prefilled form page:
# /institutions/<m>/pilot/ (es: /es/institutions/mx/piloto/) for the pilot,
# /institutions/<m>/request/<slug>/ (es: …/solicitud/<slug>/) for the rest.
# All noindex and not in the sitemap. Per type the i18n keys are
# instp.req_title_<type> (form heading), instp.req_submit_<type> (button) and
# instp.req_ctx_<type> (the context line at the top of the form).
INST_REQUEST_TYPES = ["pilot", "pricing_clinic", "pricing_hospital",
                      "pricing_network", "pricing_public", "kit"]
INST_REQUEST_SLUG = {"pricing_clinic": "clinic", "pricing_hospital": "hospital",
                     "pricing_network": "network", "pricing_public": "public",
                     "kit": "kit"}
INST_PILOT_SLUG = {"en": "pilot", "es": "piloto"}
INST_REQUEST_DIR = {"en": "request", "es": "solicitud"}
# mailto fallback (FORM_ENDPOINT empty) per type: (subject key, body key)
INST_REQUEST_MAIL = {
    "pilot": ("instp.subj_pilot", "instp.body_pilot"),
    "pricing_clinic": ("instp.subj_clinic", ""),
    "pricing_hospital": ("instp.subj_hospital", ""),
    "pricing_network": ("instp.subj_network", ""),
    "pricing_public": ("instp.subj_public", ""),
    "kit": ("instp.subj_kit", "instp.body_kit"),
}


def inst_pilot_url(lang: str, market: str) -> str:
    return inst_url(lang, market) + INST_PILOT_SLUG.get(lang, "pilot") + "/"


def inst_request_url(lang: str, market: str, rtype: str = "pilot") -> str:
    """No-JS fallback page for one request type."""
    if rtype == "pilot":
        return inst_pilot_url(lang, market)
    return (inst_url(lang, market) + INST_REQUEST_DIR.get(lang, "request")
            + f"/{INST_REQUEST_SLUG[rtype]}/")


def inst_request_mailto(s: dict, rtype: str, mname: str) -> str:
    subj, body = INST_REQUEST_MAIL[rtype]
    return _mailto(s[subj].replace("{market}", mname), s[body] if body else "")


def inst_request_attrs(s: dict, lang: str, market: str, rtype: str) -> str:
    """Attributes that make a link a request-form trigger: href = the no-JS
    page; data-* = what /inst.js swaps into the modal before opening it."""
    e = lambda v: html.escape(v, quote=True)  # noqa: E731
    mname = s[f"instp.market_{market}"]
    return (f'href="{inst_request_url(lang, market, rtype)}" '
            f'data-request="{rtype}" data-market="{market}" '
            f'data-title="{e(s["instp.req_title_" + rtype])}" '
            f'data-submit="{e(s["instp.req_submit_" + rtype])}" '
            f'data-context="{e(s["instp.req_ctx_" + rtype])}" '
            f'data-mailto="{inst_request_mailto(s, rtype, mname)}"')


# Procurement-kit PDFs (scripts/build_procurement_pdfs.py writes them and
# kit/manifest.json; the build copies kit/ to /kit/). Order = the list on the
# market page; each maps to its instp.kit_N description.
KIT_ORDER = ["security", "it-guide", "license-terms", "certificate"]


def load_kit() -> dict:
    path = os.path.join(HERE, "kit", "manifest.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _kit_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{max(1, round(n / 1024))} KB"


def inst_kit_list(s: dict, lang: str, kit: dict) -> str:
    """<li> download links for the page language's procurement-kit PDFs (title,
    language, pages and size from kit/manifest.json). Falls back to the plain
    instp.kit_N descriptions if a document is missing from the manifest; a
    manifest entry whose PDF is missing fails the build (no dead links)."""
    e = html.escape
    base = kit.get("base_path", "/kit/")
    docs = {d["key"]: d for d in kit.get("documents", []) if d["lang"] == lang}
    items = []
    for i, key in enumerate(KIT_ORDER, 1):
        text = s[f"instp.kit_{i}"]
        d = docs.get(key)
        if not d:
            items.append(f"          <li>{text}</li>")
            continue
        if not os.path.isfile(os.path.join(HERE, "kit", d["filename"])):
            raise FileNotFoundError(f"kit/{d['filename']} listed in "
                                    "kit/manifest.json but missing")
        desc = text.split("</strong>", 1)[-1] if "</strong>" in text else ""
        pages = s["instp.kit_page_one" if d["pages"] == 1
                  else "instp.kit_page_many"]
        meta = (f'PDF · {s["instp.kit_lang"]} · {d["pages"]} {pages} · '
                f'{_kit_size(d["bytes"])}')
        items.append(
            f'          <li><a href="{e(base + d["filename"], quote=True)}" '
            f'type="application/pdf" hreflang="{d["lang"]}" '
            f'data-track="kit_download:{key}"><strong>{e(d["title"])}</strong>'
            f'</a>{desc} <span class="i-kit-meta">{meta}</span></li>')
    return "\n".join(items)


# Disc-volume ranges for the pilot form: (value sent, i18n key suffix). The
# values are the Worker's allow-list (DISCS in workers/forms/src/index.js).
INST_DISC_RANGES = [("lt10", "lt10"), ("10-50", "10_50"),
                    ("51-200", "51_200"), ("gt200", "gt200"),
                    ("unsure", "unsure")]


def inst_url(lang: str, market: str | None = None) -> str:
    """Root-absolute URL of the hub (market=None) or a market page."""
    prefix = "/" if lang == "en" else f"/{lang}/"
    return f"{prefix}institutions/" + (f"{market}/" if market else "")


def load_markets() -> dict[str, dict]:
    markets = {}
    for code in INST_MARKETS:
        path = os.path.join(HERE, "markets", f"{code}.json")
        if not os.path.exists(path):
            print(f"  ! markets/{code}.json missing — skipping {code}")
            continue
        with open(path, encoding="utf-8") as f:
            markets[code] = json.load(f)
        n = len(markets[code].get("pages", {}))
        if n != 1:
            raise ValueError(f"markets/{code}.json must list exactly one page "
                             f"language (one language per market), got {n}")
    return markets


def _inst_required_keys(langs: dict) -> set[str]:
    """instp.* keys a market page needs (the hub-only keys are English-only)."""
    return {k for k in langs["en"]
            if k.startswith("instp.") and not k.startswith("instp.hub_")}


def inst_pages(langs: dict, markets: dict) -> list[tuple[str, str, dict]]:
    """(market, lang, page-data) for every market page that can be built."""
    need = _inst_required_keys(langs)
    out = []
    for m in INST_MARKETS:
        for lang, pdata in markets.get(m, {}).get("pages", {}).items():
            if lang not in langs:
                print(f"  ! institutions: skipping {lang}/{m} — "
                      f"i18n/{lang}.json not loaded")
                continue
            missing = need - langs[lang].keys()
            if missing:
                print(f"  ! institutions: skipping {lang}/{m} — missing "
                      f"{len(missing)} instp.* keys in i18n/{lang}.json")
                continue
            out.append((m, lang, pdata))
    return out


def inst_cluster(pages: list[tuple[str, str, dict]]) -> list[tuple[str, str]]:
    """(hreflang, absolute URL) for the hub + every market page + x-default."""
    pairs = [("en", BASE + inst_url("en"))]
    pairs += [(p["locale"], BASE + inst_url(lang, m)) for m, lang, p in pages]
    pairs.append(("x-default", BASE + inst_url("en")))
    return pairs


def _mailto(subject: str, body: str = "") -> str:
    from urllib.parse import quote
    q = "subject=" + quote(subject, safe="")
    if body:
        q += "&body=" + quote(body, safe="")
    return html.escape(f"mailto:{INST_EMAIL}?{q}", quote=True)


def inst_head_seo(url: str, cluster: list[tuple[str, str]], title: str,
                  desc: str, og_locale: str, lang: str) -> str:
    """`title`/`desc` are the social-card texts (≤60 / ≤155 chars): the
    og:site_name already carries the brand, so no "| MIA Tools" suffix."""
    title, desc = html.escape(title, quote=True), html.escape(desc, quote=True)
    og_img = BASE + OG_IMAGE["institutions"]
    site_name = html.escape(inst_brand(lang), quote=True)
    lines = [f'  <link rel="canonical" href="{url}">'] + _favicon_lines()
    lines += [f'  <link rel="alternate" hreflang="{hl}" href="{href}">'
              for hl, href in cluster]
    lines += [
        '  <meta property="og:type" content="website">',
        f'  <meta property="og:site_name" content="{site_name}">',
        f'  <meta property="og:title" content="{title}">',
        f'  <meta property="og:description" content="{desc}">',
        f'  <meta property="og:url" content="{url}">',
        f'  <meta property="og:locale" content="{og_locale}">',
        f'  <meta property="og:image" content="{og_img}">',
        '  <meta property="og:image:width" content="1200">',
        '  <meta property="og:image:height" content="630">',
        f'  <meta property="og:image:alt" content="{title}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        f'  <meta name="twitter:title" content="{title}">',
        f'  <meta name="twitter:description" content="{desc}">',
        f'  <meta name="twitter:image" content="{og_img}">',
    ]
    return "\n".join(lines)


INST_TIERS = [("clinic", "99"), ("hospital", "499"), ("network", "1499")]


def inst_json_ld(s: dict, url: str, locale: str, desc: str, lang: str) -> str:
    """Organization + SoftwareApplication with the three paid tiers as Offers
    (annual, USD). No ratings or reviews — we have none to cite."""
    org_id = BASE + "/institutions/#org"
    org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": org_id,
        "name": "Fritanga",
        "url": "https://fritanga.co",
        "email": INST_EMAIL,
        "brand": {"@type": "Brand", "name": inst_brand(lang)},
        "contactPoint": {"@type": "ContactPoint", "contactType": "sales",
                         "email": INST_EMAIL},
    }
    offers = []
    for key, price in INST_TIERS:
        offers.append({
            "@type": "Offer",
            "name": f"MIA Toolkit — {s[f'inst.{key}']}",
            "description": s[f"inst.{key}_scope"],
            "price": price,
            "priceCurrency": "USD",
            "url": url + "#pricing",
            "priceSpecification": {
                "@type": "UnitPriceSpecification",
                "price": price,
                "priceCurrency": "USD",
                "referenceQuantity": {"@type": "QuantitativeValue",
                                      "value": 1, "unitCode": "ANN"},
            },
        })
    app = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "MIA Toolkit",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "macOS, Windows",
        "url": url,
        "inLanguage": locale,
        "description": desc,
        "license": "https://opensource.org/licenses/MIT",
        "publisher": {"@id": org_id},
        "offers": offers,
    }
    return _ld_script(org) + "\n" + _ld_script(app)


def _inst_market_target(m: str, pages) -> tuple[str, str] | None:
    """(url, locale) of a market's page (one language per market)."""
    for mm, l, p in pages:
        if mm == m:
            return inst_url(l, m), p["locale"]
    return None


def inst_shell(langs: dict, lang: str, market: str | None, pages,
               here: bool = True) -> str:
    """Dark top bar: brand, ONE market menu, For patients.

    The market menu is a <details> disclosure holding plain links: it opens,
    closes and navigates with no JavaScript (keyboard: Tab to the summary,
    Enter/Space to open, Tab through the links). /inst.js only adds the
    niceties (Escape and click-outside close it). Each market has a single
    language, so there is no separate language switcher."""
    s = langs[lang]
    e = html.escape
    cur_locale = next((p["locale"] for m, l, p in pages
                       if m == market and l == lang), "en")
    items = []
    for m in INST_MARKETS:
        t = _inst_market_target(m, pages)
        if not t:
            continue
        url, loc = t
        cur = ' aria-current="page"' if (m == market and here) else ""
        hl = (f' hreflang="{loc}"'
              if loc.split("-")[0] != cur_locale.split("-")[0] else "")
        items.append(f'          <li><a href="{url}"{hl}{cur}>'
                     f'{s[f"instp.market_{m}"]}</a></li>')
    current = (s[f"instp.market_{market}"] if market
               else s["instp.market_choose"])
    brand = inst_brand(lang)
    home = inst_url(lang, market) if market else inst_url("en")
    head, sep, tail = brand.partition(" – ")
    brand_html = (f'{e(head)}<span>{e(sep + tail)}</span>' if sep
                  else e(brand))
    return (
        '  <header class="i-shell">\n'
        '    <div class="i-shell-in">\n'
        f'      <a class="i-brand" href="{home}">'
        f'{brand_html}</a>\n'
        '      <details class="i-market">\n'
        '        <summary><span class="i-nav-label">{{instp.market_label}}</span>'
        f'<span class="i-market-cur">{current}</span></summary>\n'
        '        <ul class="i-market-menu" aria-label="{{instp.market_label}}">\n'
        + "\n".join(items) + "\n"
        '        </ul>\n'
        '      </details>\n'
        f'      <a class="i-patients" href="{page_url(lang, "patients")}">'
        '{{instp.for_patients}} →</a>\n'
        '    </div>\n'
        '  </header>')


def inst_footer(lang: str, hours: str) -> str:
    analytics = ("{{instp.foot_analytics}}" if GOATCOUNTER
                 else "{{instp.foot_noanalytics}}")
    return (
        '  <footer class="i-footer">\n'
        '    <div class="i-container i-footer-grid">\n'
        '      <div>\n'
        '        <p class="i-eyebrow">{{instp.foot_contact}}</p>\n'
        f'        <p><a href="mailto:{INST_EMAIL}">{INST_EMAIL}</a></p>\n'
        f'        <p>{html.escape(hours)}</p>\n'
        '      </div>\n'
        '      <div>\n'
        f'        <p>{analytics} · <a href="{page_url(lang, "privacy")}">'
        '{{instp.foot_privacy}}</a></p>\n'
        '        <p>{{instp.foot_disclaimer}}</p>\n'
        '        <p>{{footer.made_by_pre}}<a href="https://fritanga.co">'
        'Fritanga</a>{{footer.made_by_post}}</p>\n'
        '      </div>\n'
        '    </div>\n'
        '  </footer>')


def inst_pilot_form(s: dict, lang: str, market: str, hlevel: str = "h3",
                    rtype: str = "pilot") -> str:
    """The pilot-request form (#pilot). A plain HTML POST to FORM_ENDPOINT
    that works with no JavaScript (the Worker 303-redirects to INST_THANKS);
    /inst.js adds the utm_campaign hidden value and inline success/error. With
    FORM_ENDPOINT empty the form renders with its submit disabled plus a
    visible mailto fallback."""
    e = html.escape
    live = bool(FORM_ENDPOINT)
    action = f' action="{e(FORM_ENDPOINT, quote=True)}"' if live else ""
    opt = f' <span class="i-opt">({s["instp.form_optional"]})</span>'
    req = ' <span class="i-req" aria-hidden="true">*</span>'

    def field(name: str, key: str, kind: str = "text", required: bool = False,
              auto: str = "", maxlen: int = 200) -> str:
        fid = f"pf-{name}"
        attrs = f' maxlength="{maxlen}"'
        if required:
            attrs += " required"
        if auto:
            attrs += f' autocomplete="{auto}"'
        return (f'            <div class="i-field">\n'
                f'              <label for="{fid}">{s[key]}'
                f'{req if required else opt}</label>\n'
                f'              <input id="{fid}" name="{name}" type="{kind}"'
                f'{attrs}>\n'
                f'            </div>')

    discs = "\n".join(
        f'                <option value="{v}">{s["instp.form_discs_" + k]}'
        f'</option>' for v, k in INST_DISC_RANGES)
    submit = s["instp.req_submit_" + rtype]
    mailto = inst_request_mailto(s, rtype, s[f"instp.market_{market}"])
    if live:
        button = (f'          <button class="i-btn i-btn-primary" type="submit">'
                  f'{submit}</button>')
        pending = ""
    else:
        button = (f'          <button class="i-btn i-btn-primary" type="submit" '
                  f'disabled aria-describedby="pf-pending">'
                  f'{submit}</button>')
        pending = (f'\n          <p class="i-form-pending" id="pf-pending">'
                   f'{s["instp.form_pending"]} <a href="{mailto}">'
                   f'{s["instp.form_pending_link"]}</a>.</p>')
    privacy = s["instp.form_privacy"].replace("{privacy}",
                                              page_url(lang, "privacy"))
    return (
        f'        <{hlevel} id="pf-h">{s["instp.req_title_" + rtype]}</{hlevel}>\n'
        f'        <form class="i-form" id="pilot-form" method="post"{action}'
        f' accept-charset="utf-8" aria-labelledby="pf-h"'
        f' data-msg-ok="{e(s["instp.form_ok"], quote=True)}"'
        f' data-msg-err="{e(s["instp.form_err"], quote=True)}"'
        f' data-msg-sending="{e(s["instp.form_sending"], quote=True)}">\n'
        f'          <p class="i-form-context" id="pf-context">'
        f'{s["instp.req_ctx_" + rtype]}</p>\n'
        f'          <p class="i-small">{s["instp.form_req_note"]}</p>\n'
        f'          <input type="hidden" name="form" value="pilot">\n'
        f'          <input type="hidden" name="request_type" value="{rtype}">\n'
        f'          <input type="hidden" name="market" value="{market}">\n'
        f'          <input type="hidden" name="lang" value="{lang}">\n'
        f'          <input type="hidden" name="utm_campaign" value="">\n'
        f'          <div class="i-hp" aria-hidden="true">\n'
        f'            <label for="pf-website">{s["instp.form_hp"]}</label>\n'
        f'            <input id="pf-website" name="website" type="text" '
        f'tabindex="-1" autocomplete="off">\n'
        f'          </div>\n'
        f'          <div class="i-form-grid">\n'
        + field("name", "instp.form_name", required=True, auto="name",
                maxlen=120) + "\n"
        + field("email", "instp.form_email", "email", required=True,
                auto="email", maxlen=254) + "\n"
        + field("organisation", "instp.form_org", required=True,
                auto="organization") + "\n"
        + field("role", "instp.form_role", auto="organization-title",
                maxlen=120) + "\n"
        + f'            <div class="i-field">\n'
          f'              <label for="pf-discs">{s["instp.form_discs"]}{opt}'
          f'</label>\n'
          f'              <select id="pf-discs" name="discs_per_month">\n'
          f'                <option value="">{s["instp.form_discs_choose"]}'
          f'</option>\n{discs}\n'
          f'              </select>\n'
          f'            </div>\n'
        + field("pacs", "instp.form_pacs") + "\n"
        + f'            <div class="i-field i-field-wide">\n'
          f'              <label for="pf-message">{s["instp.form_message"]}'
          f'{opt}</label>\n'
          f'              <textarea id="pf-message" name="message" rows="4" '
          f'maxlength="2000"></textarea>\n'
          f'            </div>\n'
          f'          </div>\n'
          f'          <p class="i-small i-form-privacy">{privacy}</p>\n'
        + button + pending + "\n"
        + '          <p class="i-form-status" role="status" aria-live="polite"'
          ' hidden></p>\n'
          '        </form>')


def inst_pilot_block(s: dict, lang: str, market: str) -> str:
    """#pilot CTA + the form in a <dialog>. The CTA is a real link to the
    standalone pilot page (works without JS); /inst.js turns it into a
    showModal() trigger. A closed <dialog> is not rendered, so without JS
    the form only appears on the pilot page."""
    form = inst_pilot_form(s, lang, market)
    form = "\n".join("  " + ln if ln else ln for ln in form.split("\n"))
    return (
        f'        <p class="i-pilot-cta"><a class="i-btn i-btn-primary" '
        f'id="pilot-cta" {inst_request_attrs(s, lang, market, "pilot")}>'
        f'{s["instp.pilot_cta"]}</a></p>\n'
        f'        <dialog class="i-dialog" id="pilot-dialog" '
        f'aria-labelledby="pf-h" aria-describedby="pf-context">\n'
        f'          <div class="i-dialog-in">\n'
        f'            <button class="i-dialog-close" type="button" data-close '
        f'aria-label="{html.escape(s["instp.dialog_close"], quote=True)}">'
        f'<span aria-hidden="true">×</span></button>\n'
        + form + "\n"
        '          </div>\n'
        '        </dialog>')


# Illustrations on the institution pages (img/inst/<slug>-<w>.<ext>): WebP at
# 800w and 1600w plus a 1600w JPEG fallback, all 16:9 (1600x900). The width/
# height attributes reserve the box (no layout shift); CSS may crop to 21:9.
INST_IMG_W, INST_IMG_H = 1600, 900


def inst_picture(slug: str, alt: str, cls: str, sizes: str,
                 eager: bool = False, particles: str = "") -> str:
    """particles: a scene name in /particles.js; it animates a canvas over
    the image (decorative, skipped with reduced motion)."""
    base = f"/img/inst/{slug}"
    anim = f' data-particles="{particles}"' if particles else ""
    load = ('loading="eager" fetchpriority="high"' if eager
            else 'loading="lazy"')
    return (f'<picture class="{cls}"{anim}>'
            f'<source type="image/webp" srcset="{base}-800.webp 800w, '
            f'{base}-1600.webp 1600w" sizes="{sizes}">'
            f'<img src="{base}-1600.jpg" alt="{html.escape(alt)}" '
            f'width="{INST_IMG_W}" height="{INST_IMG_H}" {load} '
            f'decoding="async"></picture>')


def inst_images(s: dict) -> dict:
    """Computed {{IMG_*}} blocks shared by the hub and the market pages."""
    hero_sizes = "(max-width: 800px) calc(100vw - 32px), 400px"
    card_sizes = "(max-width: 800px) calc(100vw - 32px), 600px"
    return {
        "IMG_HERO": inst_picture("disc-to-usb-real", s["instp.img_hero_alt"],
                                 "i-hero-img", hero_sizes, eager=True,
                                 particles="stream"),
        "IMG_TK": inst_picture("disc-to-usb-real", s["instp.img_tk_alt"],
                               "i-card-img", card_sizes, particles="stream"),
        "IMG_BR": inst_picture("network-to-pacs-beam", s["instp.img_br_alt"],
                               "i-card-img i-img-server", card_sizes,
                               particles="network"),
    }


def render_inst_page(langs: dict, market: str, lang: str, pdata: dict,
                     pages, cluster, template: str, kit: dict) -> str:
    s = dict(langs[lang])
    s.update(pdata["strings"])
    url = BASE + inst_url(lang, market)
    e = html.escape
    use_cases = "\n".join(
        f'          <article class="i-card"><h3>{e(u["title"])}</h3>'
        f'<p>{e(u["text"])}</p></article>' for u in pdata["use_cases"])
    rows = [(e(r["topic"]), e(r["text"])) for r in pdata["compliance"]]
    rows += [(s["instp.net_topic"], s["instp.net_text"]),
             (s["instp.out_topic"], s["instp.out_text"]),
             (s["instp.sign_topic"], s["instp.sign_signed"] if WINDOWS_SIGNED
              else s["instp.sign_unsigned"])]
    compliance = "\n".join(
        f'            <tr><th scope="row">{t}</th><td>{x}</td></tr>'
        for t, x in rows)
    # Market-specific trust assets render only once they exist ("ready").
    trust = "".join(f'\n          <li>{e(t["text"])}</li>'
                      for t in pdata.get("trust_assets", []) if t.get("ready"))
    computed = {
        "INST_LOCALE": pdata["locale"],
        "PAGE_TITLE": e(inst_title(s["m.title"], lang)),
        "HEAD_SEO": inst_head_seo(url, cluster,
                                  s.get("m.og_title", s["m.title"]),
                                  s.get("m.og_desc", s["m.meta_desc"]),
                                  pdata["og_locale"], lang),
        "JSON_LD": inst_json_ld(s, url, pdata["locale"], s["m.meta_desc"],
                                lang),
        "INST_SHELL": inst_shell(langs, lang, market, pages),
        "INST_FOOTER": inst_footer(lang, s["m.contact_hours"]),
        "INST_USE_CASES": use_cases,
        "INST_COMPLIANCE": compliance,
        "INST_TRUST": trust,
        "INST_PILOT": inst_pilot_block(s, lang, market),
        "INST_KIT": inst_kit_list(s, lang, kit),
        "REQ_CLINIC": inst_request_attrs(s, lang, market, "pricing_clinic"),
        "REQ_HOSPITAL": inst_request_attrs(s, lang, market, "pricing_hospital"),
        "REQ_NETWORK": inst_request_attrs(s, lang, market, "pricing_network"),
        "REQ_PUBLIC": inst_request_attrs(s, lang, market, "pricing_public"),
        "REQ_KIT": inst_request_attrs(s, lang, market, "kit"),
        **inst_images(s),
    }
    return render(template, s, computed)


def render_inst_hub(langs: dict, pages, cluster, template: str) -> str:
    s = langs["en"]
    url = BASE + inst_url("en")
    cards = []
    for m in INST_MARKETS:
        t = _inst_market_target(m, pages)
        if not t:
            continue
        href, loc = t
        hl = f' hreflang="{loc}"' if not loc.startswith("en") else ""
        cards.append(
            f'          <li><a class="i-card i-card-link" href="{href}"{hl}>'
            f'<span class="i-eyebrow">{s[f"instp.hub_lang_{m}"]}</span>'
            f'<h3>{s[f"instp.market_{m}"]}</h3>'
            f'<p>{s[f"instp.hub_card_{m}"]}</p>'
            f'<span class="i-more">{s["instp.hub_open"]} →</span></a></li>')
    computed = {
        "PAGE_TITLE": html.escape(inst_title(s["instp.hub_title"], "en")),
        "HEAD_SEO": inst_head_seo(url, cluster,
                                  s.get("instp.hub_og_title",
                                        s["instp.hub_title"]),
                                  s.get("instp.hub_og_desc",
                                        s["instp.hub_meta"]),
                                  s["_og_locale"], "en"),
        "JSON_LD": inst_json_ld(s, url, "en", s["instp.hub_meta"], "en"),
        "INST_SHELL": inst_shell(langs, "en", None, pages),
        "INST_FOOTER": inst_footer("en", s["instp.hub_contact_hours"]),
        "INST_HUB_CARDS": "\n".join(cards),
        **inst_images(s),
    }
    return render(template, s, computed)


def render_inst_thanks(langs: dict, lang: str, market: str | None, pages,
                       hours: str, template: str) -> str:
    """Thank-you page the Worker redirects a no-JS form post to (noindex)."""
    s = langs[lang]
    url = BASE + INST_THANKS[lang]
    back = inst_url(lang, market) if market else inst_url("en")
    computed = {
        "INST_LOCALE": "es-MX" if lang == "es" else "en",
        "PAGE_TITLE": html.escape(inst_title(s["instp.thanks_title"], lang)),
        "CANONICAL": url,
        "FAVICONS": "\n".join(_favicon_lines() + og_meta(
            s["instp.thanks_title"], s["instp.form_ok"], url, OG_IMAGE["institutions"], inst_brand(lang))),
        "INST_SHELL": inst_shell(langs, lang, market, pages, here=False),
        "INST_FOOTER": inst_footer(lang, hours),
        "BACK_URL": back,
    }
    return render(template, s, computed)


def render_inst_pilot(langs: dict, market: str, lang: str, pdata: dict,
                      pages, template: str, rtype: str = "pilot") -> str:
    """Standalone request-form page for one request type: the no-JS target
    of that CTA, prefilled at build time (noindex, not in the sitemap)."""
    s = dict(langs[lang])
    s.update(pdata["strings"])
    computed = {
        "INST_LOCALE": pdata["locale"],
        "PAGE_TITLE": html.escape(inst_title(s["instp.req_title_" + rtype],
                                             lang)),
        "CANONICAL": BASE + inst_request_url(lang, market, rtype),
        "FAVICONS": "\n".join(_favicon_lines() + og_meta(
            s["instp.req_title_" + rtype],
            s.get("m.og_desc", s["m.meta_desc"]),
            BASE + inst_request_url(lang, market, rtype),
            OG_IMAGE["institutions"], inst_brand(lang), pdata["og_locale"])),
        "INST_SHELL": inst_shell(langs, lang, market, pages, here=False),
        "INST_FOOTER": inst_footer(lang, s["m.contact_hours"]),
        "INST_PILOT_FORM": inst_pilot_form(s, lang, market, hlevel="h1",
                                           rtype=rtype),
        "BACK_URL": inst_url(lang, market) + (
            "#pricing" if rtype.startswith("pricing_")
            else "#kit" if rtype == "kit" else "#pilot"),
    }
    return render(template, s, computed)


def build_institutions(site: str, langs: dict,
                       pages=None) -> tuple[int, list[str]]:
    """Emit the hub + every market page. Returns (page count, sitemap URLs)."""
    if pages is None:
        pages = inst_pages(langs, load_markets())
    cluster = inst_cluster(pages)
    kit = load_kit()
    tdir = os.path.join(HERE, "templates")
    with open(os.path.join(tdir, "institutions.html"), encoding="utf-8") as f:
        tmpl = f.read()
    with open(os.path.join(tdir, "institutions_hub.html"), encoding="utf-8") as f:
        hub_tmpl = f.read()
    with open(os.path.join(tdir, "institutions_thanks.html"),
              encoding="utf-8") as f:
        thanks_tmpl = f.read()
    with open(os.path.join(tdir, "institutions_pilot.html"),
              encoding="utf-8") as f:
        pilot_tmpl = f.read()

    def write(path: str, content: str) -> None:
        d = os.path.join(site, path.strip("/"))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(_inject_gc(content))

    write(inst_url("en"), render_inst_hub(langs, pages, cluster, hub_tmpl))
    for m, lang, pdata in pages:
        write(inst_url(lang, m),
              render_inst_page(langs, m, lang, pdata, pages, cluster, tmpl,
                               kit))
        for rtype in INST_REQUEST_TYPES:
            write(inst_request_url(lang, m, rtype),
                  render_inst_pilot(langs, m, lang, pdata, pages, pilot_tmpl,
                                    rtype))
    # Thank-you pages: English (US + SG) and Spanish (MX).
    thanks = 0
    for lang, path in INST_THANKS.items():
        own = [(m, p) for m, l, p in pages if l == lang]
        if not own:
            continue
        market = own[0][0] if len(own) == 1 else None
        hours = (own[0][1]["strings"]["m.contact_hours"] if market
                 else langs["en"]["instp.hub_contact_hours"])
        write(path, render_inst_thanks(langs, lang, market, pages, hours,
                                       thanks_tmpl))
        thanks += 1
    return (1 + len(pages) * (1 + len(INST_REQUEST_TYPES)) + thanks,
            cluster)


# Chooser region pre-selection by page language (others: the first option).
HOME_REGION_DEFAULT = {"es": "mx", "zh": "sg", "ms": "sg", "ta": "sg"}


def home_region_form(s: dict, lang: str, ipages) -> str:
    """The chooser's "Select your region" control. Without JS the GET form
    lands on the /institutions/ hub (which lists every market) and the
    <noscript> list links each market page directly; /home.js sends the
    visitor straight to the selected market page instead."""
    e = html.escape
    targets = [(m, _inst_market_target(m, ipages)) for m in INST_MARKETS]
    targets = [(m, t) for m, t in targets if t]
    want = HOME_REGION_DEFAULT.get(lang, "us")
    opts, links = [], []
    for m, (url, loc) in targets:
        sel = " selected" if m == want else ""
        name = s[f"home.region_{m}"]
        opts.append(f'                <option value="{url}" data-market="{m}"'
                    f'{sel}>{name}</option>')
        links.append(f'              <li><a href="{url}" hreflang="{loc}">'
                     f'{name}</a></li>')
    return (
        f'            <form class="region-form" action="{inst_url("en")}" '
        f'method="get" data-region-form>\n'
        f'              <label for="region-select">{s["home.region_label"]}'
        f'</label>\n'
        f'              <div class="region-row">\n'
        f'                <select id="region-select" name="region">\n'
        + "\n".join(opts) + "\n"
        f'                </select>\n'
        f'                <button class="btn btn-light" type="submit">'
        f'{e(s["home.region_go"])} <span aria-hidden="true">→</span></button>\n'
        f'              </div>\n'
        f'            </form>\n'
        f'            <noscript>\n'
        f'            <ul class="region-links" aria-label="{s["home.region_label"]}">\n'
        + "\n".join(links) + "\n"
        '            </ul>\n'
        '            </noscript>')


def _display_path(path: str) -> str:
    """Path relative to the cwd for the build summary; absolute when that
    isn't possible (Windows: output and cwd on different drives)."""
    try:
        return os.path.relpath(path)
    except ValueError:
        return os.path.abspath(path)


def main(site: str | None = None) -> int:
    langs = load_langs()
    if "en" not in langs:
        print("FATAL: i18n/en.json is required")
        return 1
    site = site or os.path.join(HERE, "_site")
    shutil.rmtree(site, ignore_errors=True)
    os.makedirs(site)

    templates = {}
    for p in PAGES:
        with open(os.path.join(HERE, "templates", f"{p}.html"),
                  encoding="utf-8") as f:
            templates[p] = f.read()
    metrics = load_metrics()
    ipages = inst_pages(langs, load_markets())

    pages = 0
    for lang, s in langs.items():
        if GOATCOUNTER and "privacy.site_li1_gc" in s:
            s = dict(s)
            s["privacy.site_li1"] = s["privacy.site_li1_gc"]
        outdir = site if lang == "en" else os.path.join(site, lang)
        os.makedirs(outdir, exist_ok=True)
        for page in PAGES:
            # Relative path back to the site root (for styles/scripts/img).
            prefix = ("" if lang == "en" else "../") + (
                "../" if page in DIR_PAGES else "")
            computed = {
                **site_links(lang),
                "P": prefix,
                "LANG": lang,   # directory code (en/es/zh/…), not the _lang
                                # locale (es-MX); used for per-language asset paths
                "HELP_IMG_LANG": help_img_lang(lang),  # screenshots, en-fallback
                "HEAD_SEO": head_seo(langs, lang, page, s),
                "JSON_LD": json_ld(lang, s, page),
                "LANGSEL": langsel(langs, lang, page),
            }
            if page == "stats":
                computed.update(stats_blocks(metrics, s))
            if page == "index":
                computed["REGION_FORM"] = home_region_form(s, lang, ipages)
            html = render(templates[page], s, computed)
            # i18n strings may carry a relative help link (index.note);
            # make it root-absolute so it works from /patients/ too.
            html = html.replace('href="help.html#', f'href="{page_url(lang, "help")}#')
            html = _inject_gc(html)
            if page in DIR_PAGES:
                os.makedirs(os.path.join(outdir, page), exist_ok=True)
                out = os.path.join(outdir, page, "index.html")
            else:
                out = os.path.join(outdir, f"{page}.html")
            with open(out, "w", encoding="utf-8") as f:
                f.write(html)
            pages += 1

    # ── Blog (/blog) ──────────────────────────────────────────────
    # Only emit blog pages for languages that (a) have ≥1 published post AND
    # (b) carry the blog.* i18n keys — render() raises KeyError on a missing
    # key, so a future es post without es blog.* keys must NOT crash the build.
    all_posts, clusters = load_posts()
    blog_tmpl = {
        "index": open(os.path.join(HERE, "templates", "blog_index.html"),
                      encoding="utf-8").read(),
        "post": open(os.path.join(HERE, "templates", "blog_post.html"),
                     encoding="utf-8").read(),
    }
    ready = {c for c in _blog_langs(all_posts)
             if c in langs and REQUIRED_BLOG_KEYS <= langs[c].keys()}
    skipped = sorted({p["lang"] for p in all_posts} - ready)
    for c in skipped:
        if c not in langs:
            print(f"  ! blog: skipping {c} — i18n/{c}.json not loaded "
                  f"(not in LANG_ORDER or file missing)")
        else:
            missing = ", ".join(sorted(REQUIRED_BLOG_KEYS - langs[c].keys()))
            print(f"  ! blog: skipping {c} — missing blog.* i18n keys "
                  f"({missing}) in i18n/{c}.json")
    posts = [p for p in all_posts if p["lang"] in ready]
    # URLs that actually exist this build — used to unlink dead cross-links
    # (sibling not yet published, or no translation in this language).
    live_urls = {blog_post_url(p["lang"], p["slug"]) for p in posts}
    blog_pages = 0
    if posts:
        for lang in _blog_langs(posts):
            outdir = (os.path.join(site, "blog") if lang == "en"
                      else os.path.join(site, lang, "blog"))
            os.makedirs(outdir, exist_ok=True)
            idx = _inject_gc(render_blog_index(lang, posts, langs,
                                               blog_tmpl["index"]))
            with open(os.path.join(outdir, "index.html"), "w",
                      encoding="utf-8") as f:
                f.write(idx)
            blog_pages += 1
        for p in posts:
            cluster = [q for q in clusters[p["slug"]] if q["lang"] in ready]
            postdir = os.path.join(site, "" if p["lang"] == "en" else p["lang"],
                                   "blog", p["slug"])
            os.makedirs(postdir, exist_ok=True)
            out = _inject_gc(render_post(p, cluster, langs, blog_tmpl["post"],
                                         live_urls))
            with open(os.path.join(postdir, "index.html"), "w",
                      encoding="utf-8") as f:
                f.write(out)
            blog_pages += 1
        # RSS for the English blog only (for now).
        en_posts = [p for p in posts if p["lang"] == "en"]
        if en_posts:
            os.makedirs(os.path.join(site, "blog"), exist_ok=True)
            with open(os.path.join(site, "blog", "feed.xml"), "w",
                      encoding="utf-8") as f:
                f.write(rss_feed(en_posts))

    # ── Institutions (/institutions/) ─────────────────────────────
    inst_count, inst_alts = build_institutions(site, langs, ipages)

    for legacy, target in LEGACY.items():
        tfile = os.path.join(site, target.strip("/"))
        if target.endswith("/"):
            tfile = os.path.join(tfile, "index.html")
        card = ""
        if os.path.exists(tfile):
            with open(tfile, encoding="utf-8") as f:
                card = "\n".join(re.findall(
                    r'^ *<meta (?:property="og:|name="twitter:).*>$', f.read(),
                    re.M))
        path = os.path.join(site, legacy)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(redirect_stub(target, card))

    with open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap(langs, posts, clusters, inst_alts))

    for asset in ASSETS:
        src = os.path.join(HERE, asset)
        if not os.path.exists(src):
            print(f"  ! asset missing: {asset}")
            continue
        dst = os.path.join(site, asset)
        if asset == "track.js":  # bake the configured analytics provider in
            with open(src, encoding="utf-8") as f:
                js = f.read().replace("__ANALYTICS_PROVIDER__",
                                      ANALYTICS_PROVIDER)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(js)
        elif os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    print(f"✓ built {pages} pages × {len(langs)} languages "
          f"({', '.join(langs)}), {blog_pages} blog pages "
          f"({len(posts)} posts), {inst_count} institution pages, "
          f"{len(LEGACY)} redirects, sitemap, assets "
          f"→ {_display_path(site)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
