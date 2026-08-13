"""Tests for the PDF generation pipeline (Python script + CI workflow)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


def test_generator_script_exists(root: Path):
    script = root / "scripts" / "generate_pdf.py"
    assert script.exists(), "scripts/generate_pdf.py is missing"
    text = script.read_text(encoding="utf-8")
    assert "playwright" in text
    assert "cv.pdf" in text


def test_requirements_lists_playwright(root: Path):
    req = root / "scripts" / "requirements.txt"
    assert req.exists()
    assert "playwright" in req.read_text(encoding="utf-8")


def test_workflow_builds_and_ships_the_pdf(root: Path):
    """cv.pdf is gitignored, so the deploy workflow is the only thing that
    produces the PDF the site serves — it has to build it and copy it in."""
    wf = root / ".github" / "workflows" / "deploy.yml"
    assert wf.exists(), "Missing .github/workflows/deploy.yml"
    text = wf.read_text(encoding="utf-8")

    assert "scripts/ci_docker.sh" in text, \
        "workflow should build the PDF via scripts/ci_docker.sh, so CI and " \
        "local builds use the same container"
    assert "cv.pdf" in text, "workflow should copy cv.pdf into the site artifact"
    assert "branches: [main]" in text


def test_pdf_build_runs_in_the_pinned_container(root: Path):
    """Chromium's PDF text layout is host-dependent, so the build container and
    the Playwright version pinned in requirements.txt must agree — a mismatch
    makes Playwright reject the image's preinstalled browser and fetch its own,
    quietly reintroducing the drift the container exists to prevent."""
    script = (root / "scripts" / "ci_docker.sh").read_text(encoding="utf-8")
    req = (root / "scripts" / "requirements.txt").read_text(encoding="utf-8")

    image = re.search(r"mcr\.microsoft\.com/playwright/python:v([\d.]+)-", script)
    assert image, "ci_docker.sh should pin a versioned Playwright image"

    pin = re.search(r"^playwright==([\d.]+)", req, re.M)
    assert pin, "requirements.txt should pin playwright to an exact version"

    assert image.group(1) == pin.group(1), (
        f"image is Playwright v{image.group(1)} but requirements.txt pins "
        f"{pin.group(1)} — they must match"
    )


def test_verifier_guards_against_renderer_regressions(root: Path):
    script = root / "scripts" / "verify_pdf.py"
    assert script.exists(), "scripts/verify_pdf.py is missing"
    text = script.read_text(encoding="utf-8")
    assert "Type3" in text, "should still check for Type 3 font fallback"
    assert "Td" in text, "should still check glyph advances aren't hint-quantised"


@pytest.mark.skipif(
    not os.environ.get("RUN_E2E"),
    reason="end-to-end test runs Playwright; set RUN_E2E=1 to enable",
)
def test_generator_produces_valid_pdf(root: Path):
    """End-to-end: run the script and verify the output is a real PDF."""
    pytest.importorskip("playwright")

    output = root / "cv.pdf"
    before_mtime = output.stat().st_mtime if output.exists() else 0

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "generate_pdf.py")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"generator failed: {result.stderr}"
    assert output.exists(), "cv.pdf was not produced"
    assert output.stat().st_mtime > before_mtime
    head = output.read_bytes()[:8]
    assert head.startswith(b"%PDF-"), f"output is not a PDF, starts with {head!r}"
    assert output.stat().st_size > 5_000, "PDF is suspiciously small"
