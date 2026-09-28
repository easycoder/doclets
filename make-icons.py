#!/usr/bin/env python3
"""Generate the Doclets PWA icons from one source image.

    python3 make-icons.py [SOURCE]        # SOURCE defaults to doclets.png

Writes, next to this script (i.e. the web root), the files that
manifest.json and index.html reference:

    icon-192.png           192x192   "any"
    icon-512.png           512x512   "any"
    icon-maskable-512.png  512x512   "maskable"
    apple-touch-icon.png   180x180   iOS home screen

The artwork is centred on an opaque white square. Doclets' mark is black
line art, so a transparent background would vanish on a dark launcher and
iOS would black-fill it anyway; white also matches the paper it depicts.

`fit` below is the fraction of the square the drawing is fitted into. The
maskable icon gets a small fit because Android launchers crop maskable
icons to an arbitrary shape (at minimum a circle inscribed in the central
80% "safe zone"), and the source drawing runs right to its own edges, so
anything near the edge is at risk of being cut.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
BACKGROUND = (255, 255, 255, 255)

# (filename, size, fit)
TARGETS = [
    ("icon-192.png", 192, 0.88),
    ("icon-512.png", 512, 0.88),
    ("apple-touch-icon.png", 180, 0.84),
    ("icon-maskable-512.png", 512, 0.56),
]


def render(source: Image.Image, size: int, fit: float) -> Image.Image:
    """Centre the artwork on an opaque square of `size` pixels."""
    box = max(1, int(round(size * fit)))
    scale = min(box / source.width, box / source.height)
    art = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.LANCZOS,
    )

    canvas = Image.new("RGBA", (size, size), BACKGROUND)
    canvas.alpha_composite(art, ((size - art.width) // 2, (size - art.height) // 2))
    return canvas.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "source",
        nargs="?",
        default="doclets.png",
        help="source image (default: %(default)s)",
    )
    args = parser.parse_args()

    path = Path(args.source)
    if not path.is_absolute():
        path = HERE / path
    if not path.is_file():
        print(f"error: source image not found: {path}", file=sys.stderr)
        return 2

    with Image.open(path) as img:
        source = img.convert("RGBA")
        print(f"source: {path.name} ({img.width}x{img.height} {img.mode})")

        for name, size, fit in TARGETS:
            icon = render(source, size, fit)
            out = HERE / name
            icon.save(out, "PNG", optimize=True)
            print(f"  {name:<24} {size}x{size}  fit={fit}  {out.stat().st_size:,} bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
