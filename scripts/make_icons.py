#!/usr/bin/env python3
"""Generate every logo asset from the master at website/img/fritanga.co.logo.jpg.

Dev-time tool — requires Pillow (`pip install pillow`), which is deliberately
NOT a project dependency (the app excludes PIL). Run from the repo root on
macOS (the .icns step shells out to `iconutil`):

    python scripts/make_icons.py

Outputs (committed binaries):
    packaging/macos/app.icns            Dock icon (Big Sur rounded-rect style)
    packaging/windows/app.ico           multi-res 16..256 (exe + installer)
    website/favicon.ico                 16+32+48
    website/img/favicon-16.png /-32.png
    website/img/apple-touch-icon.png    180, solid background (iOS adds no alpha)
    website/img/icon-192.png /-512.png  manifest/search sizes
    mia/gui/assets/icon.png             256, Tk window iconphoto

The master is a hand-drawn cat peeking from the bottom-right of a mostly
empty 1228x1228 canvas, so everything starts from a tight square crop around
the drawing — full-frame exports would render the cat invisible at 16px.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "website" / "img" / "fritanga.co.logo.jpg"

WHITE = (255, 255, 255, 255)


def cat_square(margin_frac: float = 0.06) -> Image.Image:
    """Master -> square crop around the drawing's dark-pixel bounding box."""
    img = Image.open(MASTER).convert("L")
    # Dark pixels (the ink) -> white on black mask; getbbox finds the drawing.
    # The median filter erases the master's stray specks (a few px each)
    # without moving the strokes, so the bbox hugs the cat itself.
    mask = (ImageOps.invert(img)
            .point(lambda p: 255 if p > 96 else 0)
            .filter(ImageFilter.MedianFilter(9)))
    bbox = mask.getbbox()
    if bbox is None:
        sys.exit(f"no drawing found in {MASTER} — threshold removed "
                 "every pixel; is the master the line-art logo?")
    left, top, right, bottom = bbox
    side = max(right - left, bottom - top)
    # Add the margin, but never let the box outgrow the canvas (which would
    # break the clamping below with negative offsets).
    side = min(side + 2 * int(side * margin_frac), img.width, img.height)
    # Center the box on the drawing, clamped to the canvas.
    cx, cy = (left + right) // 2, (top + bottom) // 2
    x0 = min(max(cx - side // 2, 0), img.width - side)
    y0 = min(max(cy - side // 2, 0), img.height - side)
    return Image.open(MASTER).convert("RGBA").crop(
        (x0, y0, x0 + side, y0 + side))


def _for_size(art: Image.Image, size: int) -> Image.Image:
    """At favicon sizes the thin ink strokes wash out — thicken them first.

    MinFilter erodes white into the black strokes (bolding them) before the
    downscale; autocontrast then re-anchors the grays to full black.
    """
    if size > 48:
        return art
    bold = art.filter(ImageFilter.MinFilter(13 if size <= 24 else 9))
    return ImageOps.autocontrast(bold.convert("RGB")).convert("RGBA")


def flat(size: int, art: Image.Image, inset_frac: float = 0.0) -> Image.Image:
    """Square white tile with the art resized in (favicons, ico, touch icon)."""
    tile = Image.new("RGBA", (size, size), WHITE)
    inner = round(size * (1 - 2 * inset_frac))
    scaled = _for_size(art, size).resize((inner, inner), Image.LANCZOS)
    offset = (size - inner) // 2
    tile.paste(scaled, (offset, offset), scaled)
    return tile


def squircle(size: int, art: Image.Image) -> Image.Image:
    """macOS Big Sur style: white rounded-rect on transparency, art inset.

    Apple's grid: the icon shape spans ~824/1024 of the canvas with ~22.5%
    corner radius; keeping the margins makes the icon sit at the same visual
    size as neighbours in the Dock.
    """
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rect = round(size * 824 / 1024)
    offset = (size - rect) // 2
    radius = round(rect * 0.225)
    plate = Image.new("RGBA", (rect, rect), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    draw.rounded_rectangle((0, 0, rect - 1, rect - 1), radius=radius,
                           fill=WHITE)
    inner = round(rect * 0.80)
    scaled = _for_size(art, size).resize((inner, inner), Image.LANCZOS)
    pad = (rect - inner) // 2
    plate.paste(scaled, (pad, pad), scaled)
    canvas.paste(plate, (offset, offset), plate)
    return canvas


def make_icns(art: Image.Image, dest: Path) -> None:
    if shutil.which("iconutil") is None:
        print("!! iconutil not found (not macOS?) — skipping app.icns")
        return
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "app.iconset"
        iconset.mkdir()
        for pts in (16, 32, 128, 256, 512):
            squircle(pts, art).save(iconset / f"icon_{pts}x{pts}.png")
            squircle(pts * 2, art).save(
                iconset / f"icon_{pts}x{pts}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset),
                        "-o", str(dest)], check=True)
    print(f"   {dest.relative_to(ROOT)}")


def main() -> int:
    art = cat_square()
    print(f"-> cropped drawing: {art.width}x{art.height}")

    make_icns(art, ROOT / "packaging" / "macos" / "app.icns")

    ico = ROOT / "packaging" / "windows" / "app.ico"
    flat(256, art, inset_frac=0.04).save(
        ico, sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print(f"   {ico.relative_to(ROOT)}")

    web = ROOT / "website"
    flat(48, art).save(web / "favicon.ico", sizes=[(16, 16), (32, 32),
                                                   (48, 48)])
    flat(16, art).save(web / "img" / "favicon-16.png")
    flat(32, art).save(web / "img" / "favicon-32.png")
    flat(180, art, inset_frac=0.08).save(web / "img" / "apple-touch-icon.png")
    flat(192, art).save(web / "img" / "icon-192.png")
    flat(512, art).save(web / "img" / "icon-512.png")
    print("   website/favicon.ico + img/{favicon-16,favicon-32,"
          "apple-touch-icon,icon-192,icon-512}.png")

    assets = ROOT / "mia" / "gui" / "assets"
    assets.mkdir(exist_ok=True)
    flat(256, art).save(assets / "icon.png")
    print(f"   {(assets / 'icon.png').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
