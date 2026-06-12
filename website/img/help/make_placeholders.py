#!/usr/bin/env python3
"""Generate neutral placeholder screenshots for the /help page.

Real screenshots are portrait 1544×1786 (the app window). Until they exist,
this writes a labeled placeholder to every img/help/<lang>/<slug>.png slot so
the page renders with the correct layout (no broken images, no layout shift).
Drop a real 1544×1786 PNG over any placeholder to replace it.

Usage:  python3 website/img/help/make_placeholders.py
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1544, 1786
LANGS = ["en", "es", "zh", "ms", "ta", "de"]
SLUGS = ["home", "welcome", "add-studies", "review", "documents",
         "build-deliver", "done"]

BG = (236, 240, 244)        # --panel-ish
FG = (74, 85, 104)          # --muted
ACCENT = (44, 82, 130)      # --accent


def _font(size: int):
    for path in ("/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _centered(draw, y, text, font, fill):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


def make(lang: str, slug: str, path: str) -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([8, 8, W - 8, H - 8], outline=(203, 213, 224), width=4)
    _centered(d, H // 2 - 230, "screenshot", _font(70), FG)
    _centered(d, H // 2 - 130, slug, _font(120), ACCENT)
    _centered(d, H // 2 + 40, f"({lang})", _font(80), FG)
    _centered(d, H // 2 + 170, f"{W} × {H}", _font(56), FG)
    _centered(d, H - 140, "placeholder — replace with a real screenshot",
              _font(44), FG)
    img.save(path, "PNG")


def main() -> int:
    n = 0
    for lang in LANGS:
        d = os.path.join(HERE, lang)
        os.makedirs(d, exist_ok=True)
        for slug in SLUGS:
            make(lang, slug, os.path.join(d, f"{slug}.png"))
            n += 1
    print(f"wrote {n} placeholders to img/help/<lang>/<slug>.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
