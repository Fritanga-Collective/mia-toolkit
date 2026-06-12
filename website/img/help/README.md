# /help screenshots

The help page (`templates/help.html`) shows one screenshot per app screen,
**localized per language**.

## Convention

```
img/help/<lang>/<slug>.png
```

- `<lang>` — one of `en es zh ms ta de`
- `<slug>` — one of: `home`, `welcome`, `add-studies`, `review`,
  `documents`, `build-deliver`, `done`
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
