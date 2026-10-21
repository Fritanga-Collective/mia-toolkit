# MIA Toolkit website

Static, fast, multilingual, **no frameworks, no tracking**. Pages are
**generated**: one template per page × one strings file per language.

```
website/
├── templates/      index.html (chooser) · patients.html · help/support/privacy/stats.html · blog_*.html · institutions*.html  ({{key}} placeholders)
├── i18n/           en.json · es.json · zh.json · ms.json · ta.json · de.json · fr.json
├── content/blog/   <lang>/<slug>.md  (front-matter + Markdown blog posts)
├── build.py        generator → _site/ (gitignored); stdlib + `markdown` (build-time)
├── requirements.txt  build-time dep: Markdown (pinned)
├── styles.css      shared styles
├── lang.js         browser-language auto-select + remembered manual choice
├── download.js     OS detection + download config (CI-synced on release)
├── support.js      donation tiers + Lemon Squeezy checkout config
├── home.js         chooser: region select → market page (progressive enhancement)
├── inst.js         institutional pages: market menu, request form + modal
├── track.js        miaTrack(name): name-only funnel events (see below)
├── kit/            procurement-kit PDFs + manifest.json (scripts/build_procurement_pdfs.py)
├── robots.txt · CNAME · img/
```

## Build & preview locally

```bash
python3 -m venv /tmp/venv && /tmp/venv/bin/pip install -r website/requirements.txt
/tmp/venv/bin/python website/build.py
python3 -m http.server -d website/_site 8000
```

The generator itself is stdlib-only **except** for one **build-time** dependency
— [`markdown`](https://pypi.org/project/Markdown/) (pinned in
`website/requirements.txt`), used to render blog post bodies to HTML. Nothing
ships to users or runs in the browser; the output is plain static HTML.

English lives at the site root (`/`, x-default); every other language under
`/<code>/` (`/es/`, `/zh/`, `/ms/`, `/ta/`). The generator also emits the
language dropdown, canonical + hreflang clusters, Open Graph blocks, JSON-LD,
`sitemap.xml`, the `/blog` (see below), and redirect stubs for the pre-2026 flat
URLs (`es.html`, `soporte.html`, …). CI (`.github/workflows/pages.yml`) installs
the build dep, runs the build, and deploys `_site/`.

## Site structure: chooser + patient page

- `/` and `/<lang>/` are a **use-case chooser** (`templates/index.html`, i18n
  `home.*`): hero image, two cards — *For you or your family* (one-click OS
  download via `download.js` + "How it works →" `/patients/`) and *For clinics
  & hospitals* ("Select your region" → `/es/institutions/mx/`,
  `/institutions/us/`, `/institutions/sg/`) — and a trust strip. JSON-LD:
  Organization + WebSite. The region control is a GET form to the
  `/institutions/` hub plus a `<noscript>` list of the three links, so it works
  without JS; `home.js` sends the visitor straight to the chosen market page.
- `/patients/` and `/<lang>/patients/` are the **patient homepage**
  (`templates/patients.html`, i18n keys still `index.*`), with the
  SoftwareApplication JSON-LD. Both page types are in the sitemap with their
  own hreflang clusters. Internal "home" links go to `/patients/`; the brand
  goes to the chooser. `lang.js` knows `patients` is a directory page
  (`DIR_PAGES`), so `/patients/` auto-routes to `/<lang>/patients/`.
- Patient pages link "For clinics & hospitals" in the nav (`{{INSTITUTIONS}}`:
  `/es/institutions/mx/` for Spanish, the hub otherwise).

## Funnel events (privacy-first)

`track.js` exposes `miaTrack(name)`, which forwards **one event name** to the
cookieless analytics chosen by `ANALYTICS_PROVIDER` in `build.py`
(`"goatcounter"` today via `goatcounter.count({path, title, event: true})`;
`"umami"` → `umami.track(name)`; `"plausible"` → `plausible(name)`; `""` → no-op).
The build bakes the provider into `track.js` and emits its script tag. Names
are limited to `[A-Za-z0-9_:-]`, 64 chars; **never** field values, emails,
names, URLs or IDs. If the provider script is blocked, nothing happens.

| Event | Fired when |
|---|---|
| `region_select:<market>` | chooser "See solutions" (mx / us / sg) |
| `cta_click:<type>:<market>` | a request CTA is clicked (JS) |
| `form_open:<type>:<market>` | the request modal opens |
| `form_start:<type>:<market>` | first focus in any field, once per open / page view |
| `submit_attempt:<type>:<market>` | the form is submitted (after browser validation) |
| `submit_success:<type>:<market>` | the Worker accepted it (fetch). No-JS success = a page view of `/institutions/thanks/` or `/es/institutions/mx/gracias/` |
| `close_without_submit:<type>:<market>` | the modal closes without a successful submit |
| `kit_download:<doc>` | a procurement-kit PDF link (security / it-guide / license-terms / certificate) |

`<type>` is the form's `request_type`: `pilot`, `pricing_clinic`,
`pricing_hospital`, `pricing_network`, `pricing_public`, `kit` — so the pilot
funnel reads `cta_click:pilot:sg` → `form_open:pilot:sg` → `form_start:pilot:sg`
→ `submit_attempt:pilot:sg` → `submit_success:pilot:sg`. Drop-off = the gap
between consecutive steps in the GoatCounter dashboard (events appear as paths).
The privacy policy's GoatCounter sentence (`privacy.site_li1_gc`, swapped in
automatically when analytics is on) says "aggregate page and button-click
counts" in every language; keep it true if you add events.

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

## Institutions (`/institutions/`)

The institutional storefront: `templates/institutions.html` (market pages) +
`templates/institutions_hub.html` (English hub with a market picker) ×
`markets/{mx,us,sg}.json`. Shared copy is in the `instp.*` keys of
`i18n/<lang>.json`; market copy (`m.*` strings, use cases, compliance rows,
trust assets) is in the market file under `pages.<lang>`. Output:
`/institutions/`, `/institutions/us/`, `/institutions/sg/` (en) and
`/es/institutions/mx/` (es-MX), one hreflang cluster with the hub as
x-default. Pages use the Carbon-style layer in `styles.css` (scoped to
`body.inst`) with IBM Plex self-hosted from `fonts/` (OFL, `fonts/OFL.txt`);
patient pages load no web fonts.

- **One language per market:** MX = es-MX, US = en-US, SG = en-SG. The build
  refuses a market file with more than one `pages` entry. The header has a
  single market menu (`<details>` of links, works without JS) — no language
  switcher.
- **Brand:** `INST_BRAND` in `build.py` (one line per language) sets the
  header brand, `<title>` suffix, `og:site_name` and the JSON-LD Brand.
- **One request form, many entry points:** the pilot CTA, every pricing button
  and the kit's "Request the full package" open the same form in an
  accessible `<dialog>` (`inst.js`: showModal, focus in/out, Esc, backdrop
  click, inert page), set to that `request_type` with its own heading, context
  line ("Request: Hospital license — US$499/year") and submit label (i18n
  `instp.req_{title,ctx,submit}_<type>`). Without JS each CTA is a real link to
  a prefilled, noindex page: `/institutions/<m>/pilot/` (es `…/piloto/`) and
  `/institutions/<m>/request/<clinic|hospital|network|public|kit>/` (es
  `…/solicitud/…`). Types: `INST_REQUEST_TYPES` (keep in sync with the Worker).
- **Procurement kit PDFs:** listed from `kit/manifest.json` (title, language,
  pages, size; EN pages → EN PDFs, MX → ES PDFs) and served from `/kit/` (not in
  the sitemap). Regenerate with `scripts/build_procurement_pdfs.py`; the build
  fails if the manifest names a missing PDF.
- **Pilot form:** posts to `FORM_ENDPOINT` in `build.py` — the Cloudflare
  Worker in `workers/forms/` (see its README). Empty (default) = the form
  renders with its button disabled plus a mailto fallback. Set it only after
  the Worker is deployed **and** the privacy-policy update (R4) has shipped.
  No-JS posts land on `/institutions/thanks/` or `/es/institutions/mx/gracias/`
  (`INST_THANKS`, noindex). `inst.js` (first-party, no storage) fills the
  hidden `utm_campaign` and shows inline success/error.
- **Windows signing:** flip `WINDOWS_SIGNED` in `build.py` once a signed
  release ships; the compliance row switches in every language.
- **Trust assets** (SBOM, HECVAT, VPAT…) render only when `"ready": true`.
- With `FORM_ENDPOINT` empty, the form's mailto fallback uses the subject for
  the request type that opened it.

## Write a blog post (`/blog`)

The blog is self-hosted under `miatools.tech/blog` (en), `…/<code>/blog/` for
other languages — generated by the same `build.py`. To publish a post:

1. Drop a Markdown file at `content/blog/<lang>/<slug>.md` (one file per post
   **per language**; use the **same `slug`** across languages so they link as
   translations).
2. Start it with a `---`-fenced front-matter block:

   ```markdown
   ---
   title: Welcome to the MIA Toolkit Blog
   slug: welcome-to-the-mia-blog
   date: 2026-06-15
   summary: One-sentence teaser, also used for the card + RSS description.
   languages: [en]
   status: published
   tags: [announcements]
   ---

   # Welcome…

   Body is normal Markdown (headings, lists, links, **bold**, `code`, quotes).
   ```

   Only `status: published` posts are emitted. Drafts (any other status) are
   skipped, so you can commit work-in-progress safely.
3. Commit → push to `main`. CI rebuilds and deploys. The post URL is
   `…/blog/<slug>/`; the blog index, hreflang cluster, `BlogPosting` JSON-LD,
   `sitemap.xml`, and the English RSS feed (`/blog/feed.xml`) all update
   automatically. If the post's **last** `##` section is its FAQ (heading
   `FAQ`, `Preguntas frecuentes`, … — see `BLOG_FAQ_HEADINGS`), with each
   question as a bold line followed by its answer, the build also emits
   `FAQPage` JSON-LD for it.

**Adding a post in a new language** also requires that language's `blog.*` keys
in `i18n/<code>.json` (`blog.index_title`, `blog.meta_desc`, `blog.published`,
`blog.back`, `blog.read_more`). Without them the build prints a warning and
**skips that language's posts** rather than crashing — add the keys to publish.

### Scheduling a post (future-dating)

The `date:` field is a **publish gate**: a `status: published` post whose `date`
is in the **future** is held until that date (UTC), then goes live by itself.
`pages.yml` runs a **daily rebuild** (cron `0 7 * * *`), so a scheduled post
appears on its date with no push. To stage the upcoming week locally, run
`BLOG_PREVIEW=1 python3 website/build.py` to include future-dated posts. A post
with a missing/invalid `date` publishes immediately (with a build warning).

So a release cadence is just front-matter: set each post's `date:` to its
intended publish day and commit them together — they reveal themselves on
schedule.

### Machine-translated posts

For a translation produced with machine assistance (not a native-speaker
original), add `translation: machine` to its front-matter. The build appends a
small italic footer note inviting corrections at `support@miatools.tech`
(localized via the optional `blog.tr_note` i18n key, English fallback). Omit the
field for native originals (en, the es originals, zh).

## Privacy-respecting stats (optional)

Counts come from cookieless GoatCounter (`GOATCOUNTER` / `ANALYTICS_PROVIDER`
in `build.py`; see *Funnel events* above). Do **not** add Google Analytics — it conflicts with the
project's no-tracking promise.
