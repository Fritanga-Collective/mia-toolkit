# Website

A small static site — landing pages (English + Spanish) and support pages,
vanilla HTML + one CSS file + two small dependency-free JS files (OS detection
for downloads, and the country/time-zone support suggestion). No framework, no
build step, no web fonts, no cookies, no analytics. Each page loads in well
under a second.

```
website/
├── index.html      # English landing page
├── es.html         # Español (Mexico) landing page
├── support.html    # English support page (manifesto + fair-trade bands)
├── soporte.html    # Español support page
├── styles.css      # shared styles
├── download.js     # OS detection + download config (version, asset URLs)
├── support.js      # geo fair-trade suggestion + Lemon Squeezy checkout config
└── img/
    ├── hero.png    # source illustration (large; not served)
    └── hero.jpg    # optimized web version used by the pages (~115 KB)
```

### Hero image

The pages load `img/hero.jpg`, an optimized export of the source `hero.png`.
Regenerate it after editing the source (keeps the page under the 1-second budget):

```bash
sips -s format jpeg -s formatOptions 80 -Z 1600 img/hero.png --out img/hero.jpg
```

`hero.png` is kept only as the source; you can delete it from the repo if you
don't need it — only `hero.jpg` is referenced.

## Run it locally

No build step — just serve the folder over HTTP (opening the files with `file://`
also works, but a server matches production behavior):

```bash
cd website
python3 -m http.server 8000
# then open http://localhost:8000/  (and /support.html, /es.html, /soporte.html)
```

Any static server works equally well, e.g. `npx serve` or `php -S localhost:8000`.

## Deploy (GitHub Pages via Actions)

1. Repo **Settings → Pages → Source: GitHub Actions**.
2. Push to `main`. `.github/workflows/pages.yml` publishes `website/`.
3. Live at `https://luis-rodriguez.github.io/mia-toolkit/`.

## Custom domain — `mia-toolkit.fritanga.co`

The `website/CNAME` file pins the custom domain (it ships in the Pages artifact).
To make it resolve:

1. **DNS** (at your `fritanga.co` provider): add a **CNAME** record
   - Host/Name: `mia-toolkit`
   - Value/Target: `luis-rodriguez.github.io`  (no trailing path)
   (A subdomain uses a CNAME record. Only an apex like `fritanga.co` would need
   `A`/`AAAA` records to GitHub's IPs instead.)
2. **GitHub**: Settings → Pages → set **Custom domain** to
   `mia-toolkit.fritanga.co`, then enable **Enforce HTTPS** (after the cert
   provisions, usually a few minutes to a few hours).

To change or remove the domain later, edit `website/CNAME`.

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

## Support page (voluntary funding)

`support.html` / `soporte.html` open with a manifesto on owning your own
records, then offer a **Pay-What-You-Want** contribution with a fair-trade
suggestion by region. The download is always free and one click away.

- The region suggestion is **client-side only** (browser time zone → band) — no
  IP lookup, no network, no tracking. The visitor can always change it.
- Set your **Lemon Squeezy** Pay-What-You-Want checkout URL in `CONFIG.checkout`
  inside `support.js` (it points at the GitHub repo until then).
- For IP-accurate regional discounts you can add ParityDeals/Parity Kit, but that
  introduces a third-party geolocation script — weigh it against the no-tracking
  promise.

## Privacy-respecting stats (optional)

If you ever want counts, add a cookieless GoatCounter or Plausible tag in the
`<head>` of both pages. Do **not** add Google Analytics — it conflicts with the
project's no-tracking promise.
