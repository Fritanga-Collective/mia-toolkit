# Website

A single static landing page — vanilla HTML + one CSS file + ~40 lines of
dependency-free JS for OS detection. No framework, no build step, no web fonts,
no cookies, no analytics. It loads in well under a second.

```
website/
├── index.html     # English
├── es.html        # Español (Mexico)
├── styles.css     # shared styles
└── download.js    # OS detection + download config (version, asset URLs)
```

## Deploy (GitHub Pages via Actions)

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Push to `main`. `.github/workflows/pages.yml` publishes `website/`.
3. Live at `https://luis-rodriguez.github.io/mia-toolkit/`.

## Custom domain (~$15/yr)

1. Buy the domain; in your DNS, point it at GitHub Pages
   (`A`/`AAAA` records to GitHub's IPs, or a `CNAME` to
   `luis-rodriguez.github.io`).
2. Add the domain under **Settings → Pages → Custom domain** (this creates a
   `CNAME` file in the published site) and enable **Enforce HTTPS**.

## Download links

`download.js` holds the version and the per-OS asset URLs. They are intentionally
empty for now, so every button falls back to the GitHub **Releases (latest)**
page. When the signed installers ship, the release CI should rewrite
`VERSION` / `macUrl` / `winUrl` in `download.js` (the planned
"auto-update latest-version links" step), e.g.:

```js
version: "0.2.0",
macUrl: ".../releases/download/v0.2.0/MIA-Toolkit-0.2.0-universal.dmg",
winUrl: ".../releases/download/v0.2.0/MIA-Toolkit-Setup-0.2.0.exe",
```

## Privacy-respecting stats (optional)

If you ever want counts, add a cookieless GoatCounter or Plausible tag in the
`<head>` of both pages. Do **not** add Google Analytics — it conflicts with the
project's no-tracking promise.
