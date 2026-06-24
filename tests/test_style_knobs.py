"""Tests for the optional `style:` frontmatter knobs."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ALLOWED_STYLE_KEYS = {
    "main-text",
    "sidebar-text",
    "main-heading",
    "sidebar-heading",
    "name-color",
    "icon-color",
    "marker-color",
}

CSS_VARS_BACKING = {
    "main-text":       ("--font-size-main",),
    "sidebar-text":    ("--font-size-sidebar",),
    "main-heading":    ("--font-size-main-h",),
    "sidebar-heading": ("--font-size-sidebar-h",),
    "name-color":      ("--color-name",),
    "icon-color":      ("--color-icon",),
    "marker-color":    ("--color-marker-sidebar", "--color-marker-main"),
}


# ---------- content.md ----------

def test_style_block_present_and_keys_documented(frontmatter, content_text):
    """The content file should expose every knob (commented out is fine)
    so users can discover what's available."""
    assert "style" in frontmatter, "frontmatter should expose a `style:` block"

    # Every key should appear somewhere in the frontmatter text — either
    # active or as a commented stub. We look in the raw text so we catch
    # commented entries too.
    fm_text = content_text.split("---", 2)[1]
    for key in ALLOWED_STYLE_KEYS:
        assert key in fm_text, f"style knob `{key}` should be documented in content.md frontmatter"


def test_style_block_only_uses_known_keys(frontmatter):
    """If the user activates style keys, they must be ones the renderer handles."""
    style = frontmatter.get("style") or {}
    if not isinstance(style, dict):
        pytest.skip("style block is empty/null")
    unknown = set(style) - ALLOWED_STYLE_KEYS
    assert not unknown, f"unknown style keys: {unknown}"


# ---------- CSS backing ----------

@pytest.mark.parametrize("knob,css_vars", CSS_VARS_BACKING.items())
def test_css_defines_default_for_each_knob(root: Path, knob, css_vars):
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    for v in css_vars:
        # Must be defined inside :root with a default value
        pattern = rf"{re.escape(v)}\s*:\s*[^;]+;"
        assert re.search(pattern, css), f"CSS missing default for {v} (backs `{knob}`)"


def test_css_uses_the_variables_in_real_rules(root: Path):
    """Defaults are pointless if no rule actually consumes the variable."""
    css = (root / "css/styles.css").read_text(encoding="utf-8")
    knobs = [v for vars_ in CSS_VARS_BACKING.values() for v in vars_]
    for var in knobs:
        # The variable should be referenced via var(--…) at least once
        # outside of its own declaration line.
        usages = re.findall(rf"var\(\s*{re.escape(var)}\s*\)", css)
        assert usages, f"var({var}) is declared but never consumed by a rule"


# ---------- JS wiring ----------

def test_js_has_style_map_for_every_knob(root: Path):
    js = (root / "js/main.js").read_text(encoding="utf-8")
    assert "STYLE_MAP" in js, "JS is missing the STYLE_MAP that drives applyStyle"
    for key in ALLOWED_STYLE_KEYS:
        assert f"'{key}'" in js, f"STYLE_MAP missing entry for `{key}`"


def test_js_calls_applystyle(root: Path):
    js = (root / "js/main.js").read_text(encoding="utf-8")
    assert "applyStyle(data.style)" in js, \
        "init() must call applyStyle(data.style) before rendering"


def test_js_validates_values(root: Path):
    """Letting arbitrary strings into setProperty would let a malicious
    content.md inject CSS. The JS should sanity-check values."""
    js = (root / "js/main.js").read_text(encoding="utf-8")
    assert "SAFE_VALUE" in js or "safe_value" in js.lower(), \
        "applyStyle should validate values before passing to setProperty"
