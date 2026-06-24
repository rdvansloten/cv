"""Tests for the PDF generation pipeline (Python script + CI workflow)."""
from __future__ import annotations

import os
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


def test_workflow_present_and_triggers_on_content_changes(root: Path):
    """The workflow should re-run on content/code changes but not on cv.pdf changes
    (otherwise the commit-back step would loop)."""
    wf = root / ".github" / "workflows" / "build-pdf.yml"
    assert wf.exists(), "Missing .github/workflows/build-pdf.yml"
    text = wf.read_text(encoding="utf-8")

    # Triggers on the things that affect the rendered PDF
    for needed in ("content.md", "index.html", "css/**", "js/**", "scripts/**"):
        assert needed in text, f"workflow missing trigger for {needed}"

    # Must NOT list cv.pdf in trigger paths (would create a loop)
    assert "'cv.pdf'" not in text and '"cv.pdf"' not in text, \
        "workflow should not trigger on cv.pdf changes (would loop)"

    # The commit-back step is what makes the loop possible; require [skip ci]
    # or an equivalent guard.
    assert "[skip ci]" in text, "commit-back message should include [skip ci] to be extra safe"

    # Needs write permission to push the regenerated PDF
    assert "contents: write" in text


def test_workflow_installs_chromium(root: Path):
    text = (root / ".github" / "workflows" / "build-pdf.yml").read_text(encoding="utf-8")
    assert "playwright install" in text
    assert "chromium" in text


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
