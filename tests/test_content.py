"""Content checks — keeps content.md in a shape the renderer understands."""
import re

import pytest

from conftest import split_h3


REQUIRED_FRONTMATTER = ["name", "title", "location", "github"]

# renderContact() in js/main.js drops any contact line whose value is missing,
# so these are shown when present and silently skipped when not.
OPTIONAL_FRONTMATTER = ["phone", "email"]

EXPECTED_SIDEBAR_SECTIONS = [
    "Introduction",
    "Certifications",
    "Languages",
    "Office / Creative Tools",
    "Technical Tools",
]

# Rendered if present, not required. The renderer still routes these to the
# sidebar (SIDEBAR_SECTIONS in js/main.js), so re-adding one just works.
OPTIONAL_SIDEBAR_SECTIONS = ["Hobbies"]

EXPECTED_MAIN_SECTIONS = [
    "Professional Experience",
    "Education",
    "Soft Skills",
    "Technical Skills",
]


# ---------- frontmatter ----------

@pytest.mark.parametrize("key", REQUIRED_FRONTMATTER)
def test_frontmatter_has_required_field(frontmatter, key):
    assert key in frontmatter, f"frontmatter missing required field: {key}"
    assert frontmatter[key], f"frontmatter field '{key}' is empty"


def test_email_looks_valid(frontmatter):
    if "email" not in frontmatter:
        pytest.skip("no email in frontmatter — it's optional")
    assert re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", frontmatter["email"]), \
        f"email doesn't look valid: {frontmatter['email']!r}"


def test_github_path_is_bare(frontmatter):
    """The renderer prepends https:// — a scheme here would double up."""
    gh = frontmatter["github"]
    assert not gh.startswith(("http://", "https://")), \
        "github should be a bare 'github.com/...' path; the renderer adds the scheme"


# ---------- sections ----------

@pytest.mark.parametrize("title", EXPECTED_SIDEBAR_SECTIONS + EXPECTED_MAIN_SECTIONS)
def test_section_present(section_map, title):
    assert title in section_map, f"missing ## {title} section"


def test_no_unexpected_sections(section_map):
    expected = set(
        EXPECTED_SIDEBAR_SECTIONS + OPTIONAL_SIDEBAR_SECTIONS + EXPECTED_MAIN_SECTIONS
    )
    extra = set(section_map) - expected
    assert not extra, f"unexpected ## sections present: {extra} (renderer ignores unknown sidebar titles)"


# ---------- experience entries ----------

def test_experience_has_entries(section_map):
    entries = split_h3(section_map["Professional Experience"])
    assert len(entries) >= 1, "Professional Experience needs at least one ### entry"


@pytest.mark.parametrize("section_name", ["Professional Experience", "Education"])
def test_entries_have_italic_meta_line(section_map, section_name):
    """Each ### entry must be followed by an italic line (*date, location*).
    The renderer pulls that line out into .entry-meta — without it the
    metadata renders as a normal paragraph. Either emphasis marker is fine:
    marked.js treats *x* and _x_ alike, and prettier rewrites * to _."""
    entries = split_h3(section_map[section_name])
    assert entries, f"{section_name} has no ### entries"
    for title, content in entries:
        first_line = next(
            (ln for ln in content.splitlines() if ln.strip()),
            "",
        )
        assert re.match(r"^\*[^*].*\*\s*$|^_[^_].*_\s*$", first_line), (
            f"entry '{title}' in {section_name}: first non-blank line must be "
            f"italic markdown like '*Date, Location*', got {first_line!r}"
        )


def test_technical_skills_has_groups(section_map):
    groups = split_h3(section_map["Technical Skills"])
    assert len(groups) >= 2, "Technical Skills should have at least two ### subsections"
    for title, content in groups:
        assert re.search(r"^\s*-\s+\S", content, re.MULTILINE), \
            f"skill group '{title}' has no bullet items"


# ---------- list-shaped sidebar sections ----------

@pytest.mark.parametrize("title", [
    "Certifications", "Languages", "Hobbies",
    "Office / Creative Tools", "Technical Tools",
])
def test_sidebar_list_section_has_items(section_map, title):
    """These sections render as bullet lists — they need at least one - item."""
    if title in OPTIONAL_SIDEBAR_SECTIONS and title not in section_map:
        pytest.skip(f"{title} isn't in content.md — it's optional")
    content = section_map[title]
    items = [ln for ln in content.splitlines() if re.match(r"^\s*-\s+\S", ln)]
    assert items, f"{title} has no '- ' bullet items"


def test_language_items_have_separator(section_map):
    """Language items render as two columns split on em-dash."""
    content = section_map["Languages"]
    items = [ln.strip() for ln in content.splitlines() if ln.strip().startswith("- ")]
    for item in items:
        assert re.search(r"\s[—–-]\s", item), \
            f"language entry {item!r} needs an em-dash separator (e.g. 'Dutch — Native')"


# ---------- markdown sanity ----------

def test_no_h1_in_body(body):
    """The masthead uses <h1>; markdown body should not have any H1s."""
    assert not re.search(r"^#\s", body, re.MULTILINE), \
        "Use ## (H2) for sections; H1 is reserved for the masthead name"


def test_no_tab_indentation(content_text):
    """YAML frontmatter parsers don't accept tabs."""
    fm_end = content_text.find("\n---\n", 4)
    fm = content_text[:fm_end] if fm_end != -1 else content_text
    assert "\t" not in fm, "frontmatter must not contain tab characters"
