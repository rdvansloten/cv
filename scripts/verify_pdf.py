#!/usr/bin/env python3
"""Post-build checks on cv.pdf — catches renderer regressions that are easy to
ship without noticing, because the PDF still *opens* fine.

Both guards here are for bugs this repo has actually hit:

  Type 3 fonts   A variable font (Inter.woff2 direct) can't be embedded by
                 Chromium's PDF path, so it falls back to unhinted Type 3 glyph
                 procedures — mushy text, ~3x the file size. Serving the static
                 Inter-<weight>.woff2 instances avoids it (scripts/build_fonts.py).

  Hinted glyph   Headless Chromium on Linux hints glyphs, rounding every advance
  positioning    to a whole point and emitting one Tj per glyph with integer Td
                 offsets. Text lands ~4% wide with uneven spacing and stops
                 matching the browser. --font-render-hinting=none avoids it
                 (see scripts/generate_pdf.py).

Deliberately stdlib-only, so it can run as a bare CI step with no extra install.
"""
from __future__ import annotations

import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "cv.pdf"

# Good builds sit at 0% integer offsets; hinted ones at ~89%. Anything above
# this means glyph positions are being quantised again.
MAX_INTEGER_TD_RATIO = 0.20


def page_content_streams(raw: bytes) -> list[bytes]:
    """Inflate every Flate stream that shows text (i.e. selects a font)."""
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            data = zlib.decompress(m.group(1))
        except zlib.error:
            continue
        if b" Tf" in data:
            out.append(data)
    return out


def main() -> int:
    if not PDF.exists():
        print(f"missing {PDF} — run scripts/generate_pdf.py first", file=sys.stderr)
        return 1

    raw = PDF.read_bytes()
    failures = []

    pages = raw.count(b"/Type /Page\n") or len(re.findall(rb"/Type\s*/Page[^s]", raw))
    print(f"cv.pdf: {len(raw):,} bytes, ~{pages} pages")

    # 1. No Type 3 fonts.
    if b"/Type3" in raw:
        failures.append(
            "embedded Type 3 fonts — css/styles.css is probably serving the "
            "variable Inter.woff2 instead of the static Inter-<weight>.woff2 "
            "instances (regenerate with scripts/build_fonts.py)"
        )
    else:
        print("fonts:   no Type 3 subsets ✓")

    # 2. Glyph advances must come from the font, not from rounded Td offsets.
    ints = fracs = 0
    for data in page_content_streams(raw):
        for x in re.findall(rb"(-?[\d.]+)\s+0\s+Td", data):
            if b"." in x:
                fracs += 1
            else:
                ints += 1

    total = ints + fracs
    if not total:
        failures.append("found no text-positioning operators — is the PDF empty?")
    else:
        ratio = ints / total
        print(f"spacing: {ratio:.1%} of {total:,} glyph offsets are integers "
              f"(limit {MAX_INTEGER_TD_RATIO:.0%})", end=" ")
        if ratio > MAX_INTEGER_TD_RATIO:
            print("✗")
            failures.append(
                f"{ratio:.1%} of glyph advances are whole-point integers — font "
                "hinting is quantising text layout. Chromium must be launched "
                "with --font-render-hinting=none"
            )
        else:
            print("✓")

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
