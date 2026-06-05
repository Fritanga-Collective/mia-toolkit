# MIA Toolkit website

Static, fast, multilingual, **no frameworks, no tracking**. Pages are
**generated**: one template per page × one strings file per language.

```
website/
├── templates/      index.html · support.html · privacy.html  ({{key}} placeholders)
├── i18n/           en.json · es.json · zh.json · ms.json · ta.json
├── build.py        stdlib-only generator → _site/ (gitignored)
├── styles.css      shared styles
├── lang.js         browser-language auto-select + remembered manual choice
├── download.js     OS detection + download config (CI-synced on release)
├── support.js      donation tiers + Lemon Squeezy checkout config
├── robots.txt · CNAME · img/
```

## Build & preview locally

```bash
python3 website/build.py
python3 -m http.server -d website/_site 8000
```

English lives at the site root (`/`, x-default); every other language under
`/<code>/` (`/es/`, `/zh/`, `/ms/`, `/ta/`). The generator also emits the
language dropdown, canonical + hreflang clusters, Open Graph blocks, JSON-LD,
`sitemap.xml`, and redirect stubs for the pre-2026 flat URLs (`es.html`,
`soporte.html`, …). CI (`.github/workflows/pages.yml`) runs the build and
deploys `_site/`.

## Add a language

1. Copy `i18n/en.json` → `i18n/<code>.json` and translate the values
   (keep the inline `<strong>`/`<em>` tags and product names).
2. Add the code to `LANG_ORDER` + `HREFLANG` in `build.py` and to `EXTRA`
   in `lang.js`; add a `STR` entry in `support.js` for the donation tiers.
3. `python3 website/build.py` — done. The selector, hreflang, and sitemap
   update themselves.

`support.html` / `soporte.html` / `support-zh.html` open with a manifesto on
owning your own records, then offer **fixed donation tiers** (Coffee $5.99 /
Supporter $15.99 / Patron $50.99 + Monthly $5/mo + a custom amount), the same for
everyone. The download is always free and one click away.

- **No tracking, no geolocation** — the tiers are static and identical
  everywhere; everything is client-side.
- One **Lemon Squeezy** Pay-What-You-Want product drives every fixed tier: we
  preset the amount with the `checkout[custom_price]` URL param (in cents), built
  in `support.js` → `CONFIG.pwyw` + each tier's `amount`. The bare URL (the
  "custom amount" link) lets the buyer choose.
- To use a **dedicated product** for a tier (e.g. a real monthly *subscription* —
  a URL param can't make PWYW recurring), set that tier's `url` in `CONFIG.tiers`
  to override the preset link.

## Privacy-respecting stats (optional)

If you ever want counts, add a cookieless GoatCounter or Plausible tag in the
`<head>` of both pages. Do **not** add Google Analytics — it conflicts with the
project's no-tracking promise.
