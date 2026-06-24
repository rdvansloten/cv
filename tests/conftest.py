import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def content_text(root: Path) -> str:
    return (root / "content.md").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def parsed(content_text: str):
    """Split content.md into (frontmatter dict, body markdown)."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", content_text, re.DOTALL)
    assert m, "content.md is missing YAML frontmatter delimiters"
    data = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    return data, body


@pytest.fixture(scope="session")
def frontmatter(parsed):
    return parsed[0]


@pytest.fixture(scope="session")
def body(parsed) -> str:
    return parsed[1]


def split_h2(body: str):
    """Return list of (title, content) tuples for each ## heading."""
    sections = []
    current = None
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if current:
                sections.append(current)
            current = (m.group(1).strip(), [])
        elif current:
            current[1].append(line)
    if current:
        sections.append(current)
    return [(t, "\n".join(lines)) for t, lines in sections]


def split_h3(section_body: str):
    """Return list of (title, content) tuples for each ### heading within a section."""
    entries = []
    current = None
    for line in section_body.splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            if current:
                entries.append(current)
            current = (m.group(1).strip(), [])
        elif current:
            current[1].append(line)
    if current:
        entries.append(current)
    return [(t, "\n".join(lines)) for t, lines in entries]


@pytest.fixture(scope="session")
def sections(body):
    return split_h2(body)


@pytest.fixture(scope="session")
def section_map(sections):
    return {title: content for title, content in sections}
