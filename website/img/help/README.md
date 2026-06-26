# /help screenshots

The help page (`templates/help.html`) shows one screenshot per app screen,
**localized per language**.

## Convention

```
img/help/<lang>/<slug>.png
```

- `<lang>` — one of `en es zh ms ta de` (English is also the **fallback**)
- `<slug>` — one of: `home`, `welcome`, `add-studies`, `review`,
  `documents`, `build-deliver`, `done`

### English fallback (no broken images for new languages)

A site language **without** its own `img/help/<lang>/` directory automatically
falls back to the English screenshots — `build.py:help_img_lang()` picks the
locale's own set if the directory exists, else `en`, for both the `<img>` tags
and the JSON-LD. So adding a language to `LANG_ORDER` never ships broken `/help`
images; it just shows English screenshots until a localized set is dropped in.
(This is why `fr` works with no `fr/` directory.) The
`test_every_language_help_screenshots_resolve` test enforces this.
- Size — **1544 × 1786 px** (portrait, the app window). All screenshots share
  this size; the page reserves the aspect ratio so swapping images causes no
  layout shift.

## Replacing placeholders

The committed `.png` files are neutral placeholders. To replace one, capture
the real screen in that language at 1544×1786 and overwrite the file at the
path above — no markup or build changes needed.

Regenerate all placeholders (e.g. after adding a language or slug) with:

```bash
python3 website/img/help/make_placeholders.py
```

Keep the slug list in `make_placeholders.py` in sync with `HELP_STEPS` in
`build.py` and the `<img>` tags in `templates/help.html`.
