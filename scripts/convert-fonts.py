#!/usr/bin/env python3
"""Convert the self-hosted TTF faces in assets/fonts/ to WOFF2 (about half the bytes).

Needs `pip install fonttools brotli`. Writes <name>.woff2 next to each .ttf and
prints the sizes; styles.css references the .woff2 files. The .ttf sources can
then be deleted from the repo (they are the same glyphs, just bigger).

Usage:
  python3 scripts/convert-fonts.py
"""
from __future__ import annotations

import pathlib

from fontTools.ttLib import TTFont

FONTS = pathlib.Path(__file__).resolve().parent.parent / "assets" / "fonts"


def main() -> int:
    total_in = total_out = 0
    for ttf in sorted(FONTS.glob("*.ttf")):
        out = ttf.with_suffix(".woff2")
        font = TTFont(str(ttf))
        font.flavor = "woff2"
        font.save(str(out))
        total_in += ttf.stat().st_size
        total_out += out.stat().st_size
        print(f"{ttf.name}: {ttf.stat().st_size // 1024} KB -> {out.name}: {out.stat().st_size // 1024} KB")
    print(f"total {total_in // 1024} KB -> {total_out // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
