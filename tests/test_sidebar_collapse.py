"""Tests for the narrow-viewport collapsible sidebar sections."""
from __future__ import annotations

import re
from pathlib import Path

EXPECTED_COLLAPSIBLE = {
    "Certifications",
    "Languages",
    "Hobbies",
    "Office / Creative Tools",
    "Technical Tools",
}


def _extract_collapsible_set(js: str) -> set[str]:
    m = re.search(
        r"COLLAPSIBLE_SIDEBAR_SECTIONS\s*=\s*new\s+Set\(\s*\[([^\]]+)\]",
        js,
    )
    assert m, "COLLAPSIBLE_SIDEBAR_SECTIONS literal not found in main.js"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def test_collapsible_set_matches_spec(root: Path):
    js = (root / "js/main.js").read_text(encoding="utf-8")
    got = _extract_collapsible_set(js)
    assert got == EXPECTED_COLLAPSIBLE, (
        f"COLLAPSIBLE_SIDEBAR_SECTIONS mismatch.\n"
        f"  missing: {EXPECTED_COLLAPSIBLE - got}\n"
        f"  unexpected: {got - EXPECTED_COLLAPSIBLE}"
    )


def test_introduction_is_not_collapsible(root: Path):
    """The user explicitly wanted Introduction to stay always-expanded."""
    js = (root / "js/main.js").read_text(encoding="utf-8")
    got = _extract_collapsible_set(js)
    assert "Introduction" not in got


def test_renderer_emits_details_for_collapsible(root: Path):
    js = (root / "js/main.js").read_text(encoding="utf-8")
    # The conditional rendering path: collapsible → details, else → section
    assert "createElement(collapsible ? 'details' : 'section')" in js
    # Collapsible branch must put the body in its own .sidebar-section-body
    # wrapper so CSS can force-show it on wide screens / in print.
    assert "sidebar-section-body" in js


def test_setup_function_is_wired(root: Path):
    js = (root / "js/main.js").read_text(encoding="utf-8")
    assert "function setupSidebarCollapse" in js
    assert "setupSidebarCollapse()" in js, "init() must call setupSidebarCollapse"
    assert "matchMedia(NARROW_VIEWPORT)" in js
    # Print path: open everything before the browser captures the PDF
    assert "beforeprint" in js


def test_css_disables_chevron_above_breakpoint(root: Path):
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    # Find the @media block scoping the wide-viewport override
    m = re.search(
        r"@media\s+screen\s+and\s+\(min-width:\s*701px\)\s*\{([^@]+)\}",
        css,
    )
    assert m, "missing @media (min-width: 701px) block"
    body = m.group(1)
    assert ".sidebar-section.collapsible" in body
    assert "pointer-events: none" in body, \
        "summary must be non-interactive at wide widths"
    assert "display: none" in body, \
        "chevron (::after) must be hidden at wide widths"


def test_print_css_hides_chevron_and_shows_body(root: Path):
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    m = re.search(r"@media\s+print\s*\{([^@]+(?:@page[^{]*\{[^}]*\}[^@]*)*)\}", css)
    # Simpler: just check both rules exist anywhere alongside @media print
    assert "@media print" in css
    assert re.search(
        r"\.sidebar-section\.collapsible\s*>\s*summary::after\s*\{\s*display:\s*none",
        css,
    ), "print rule must hide the chevron"
    assert re.search(
        r"\.sidebar-section\.collapsible\s*>\s*\.sidebar-section-body\s*\{[^}]*display:\s*block",
        css,
    ), "print rule must force the body visible"


def test_collapsible_summary_has_chevron(root: Path):
    """The chevron text marker exists for the toggle UI."""
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    assert re.search(
        r"\.sidebar-section\.collapsible\s*>\s*summary::after\s*\{[^}]*content:\s*['\"]\+['\"]",
        css,
    ), "collapsed summary should render a + chevron"
    assert re.search(
        r"\.sidebar-section\.collapsible\[open\]\s*>\s*summary::after\s*\{[^}]*content:\s*['\"]−['\"]",
        css,
    ), "expanded summary should render a − chevron"
