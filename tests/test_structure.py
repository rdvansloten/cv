"""Static file & wiring checks — make sure the site has every piece it needs."""
import re
from pathlib import Path

import pytest

REQUIRED_FILES = [
    "index.html",
    "content.md",
    "css/styles.css",
    "js/main.js",
    ".nojekyll",
]


@pytest.mark.parametrize("rel", REQUIRED_FILES)
def test_required_file_exists(root: Path, rel: str):
    assert (root / rel).exists(), f"missing required file: {rel}"


def test_index_references_assets(root: Path):
    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'href="css/styles.css"' in html
    assert 'src="js/main.js"' in html
    # data-slot hooks the JS uses
    for slot in ("masthead", "contact", "sidebar", "main"):
        assert f'data-slot="{slot}"' in html, f"index.html missing data-slot={slot}"


def test_download_button_present(root: Path):
    html = (root / "index.html").read_text(encoding="utf-8")
    assert 'id="download-button"' in html
    # Must link to the pre-generated PDF with the download attribute
    assert 'href="cv.pdf"' in html
    assert "download" in html


def test_cdn_dependencies_pinned(root: Path):
    """Pinned versions keep the CV reproducible — bare 'latest' would silently break."""
    html = (root / "index.html").read_text(encoding="utf-8")
    assert "marked@" in html, "marked.js should be pinned to a version"
    assert "js-yaml@" in html, "js-yaml should be pinned to a version"


def test_print_button_hidden_in_print_css(root: Path):
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    # Inside @media print the button must be hidden so it doesn't show up in PDFs.
    print_block = css.split("@media print", 1)
    assert len(print_block) == 2, "@media print block missing from styles.css"
    assert ".print-button" in print_block[1] and "display: none" in print_block[1]


def test_page_break_rules_present(root: Path):
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    # Both modern and legacy properties — for Safari/older Chrome.
    assert "break-inside: avoid" in css
    assert "page-break-inside: avoid" in css
    assert "@page" in css


def test_a4_page_size(root: Path):
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    assert "size: A4" in css


def test_fonts_are_self_hosted(root: Path):
    """Inter must load from disk, not Google Fonts — keeps the site working
    offline and avoids a privacy-sensitive third-party request."""
    html = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "css/styles.css").read_text(encoding="utf-8")

    # No external font requests anywhere
    for needle in ("fonts.googleapis.com", "fonts.gstatic.com"):
        assert needle not in html, f"index.html still references {needle}"
        assert needle not in css, f"styles.css still references {needle}"

    # Every @font-face points at a file that actually ships in the repo
    assert "@font-face" in css, "styles.css should declare @font-face"
    urls = re.findall(r"@font-face[^}]*?url\(['\"]\.\./([^'\"]+)['\"]\)", css, re.S)
    assert urls, "no local font URLs found in the @font-face blocks"
    for rel in urls:
        assert (root / rel).exists(), f"@font-face references missing file: {rel}"

    # The served faces must be the static instances, not the variable font:
    # Chromium's print-to-PDF path can't embed a variable instance and falls
    # back to unhinted Type 3 glyphs, which look wrong in the PDF.
    assert not any(rel.endswith("fonts/Inter.woff2") for rel in urls), \
        "styles.css serves the variable Inter.woff2 — use the Inter-<weight>.woff2 " \
        "instances from scripts/build_fonts.py instead"
