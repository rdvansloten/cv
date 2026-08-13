#!/usr/bin/env python3
"""Instance static Inter weights from the variable Inter.woff2.

Chromium's print-to-PDF path can't embed a variable-font instance as a real
TrueType font — it degrades to unhinted Type 3 glyph procedures, which render
mushy in PDF viewers and inflate the file. Static per-weight instances embed
as proper subset TrueType, so the PDF matches what the browser shows.

Run after changing which weights css/styles.css uses:
    pip install -r scripts/requirements.txt
    python scripts/build_fonts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
SOURCE = FONT_DIR / "Inter.woff2"

# Must stay in sync with the @font-face blocks in css/styles.css.
WEIGHTS = (400, 500, 600, 700)


def main() -> int:
    if not SOURCE.exists():
        print(f"missing source font: {SOURCE}", file=sys.stderr)
        return 1

    for weight in WEIGHTS:
        font = TTFont(SOURCE)
        instancer.instantiateVariableFont(
            font, {"wght": weight}, inplace=True, updateFontNames=True
        )
        font.flavor = "woff2"
        out = FONT_DIR / f"Inter-{weight}.woff2"
        font.save(out)
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
