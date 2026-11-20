"""Gleichlauf: Alias-Listen, Versionsnummer und Doku muessen zum Code passen."""
import json
import re
from pathlib import Path

import pytest

import pseudonym as ps

ROOT = Path(__file__).parent.parent
HTML = (ROOT / "pseudonym_gui.html").read_text(encoding="utf-8")


def gui_aliases():
    block = re.search(r"const COLUMN_ALIASES = (\{.*?\n\});", HTML, re.S).group(1)
    block = re.sub(r"//[^\n]*", "", block)                 # Kommentare
    block = re.sub(r"(\w+):\s*\[", r'"\1": [', block)      # Schluessel in Anfuehrungszeichen
    block = re.sub(r",\s*([\]}])", r"\1", block)           # haengende Kommas
    return json.loads(block)


def test_gui_and_cli_have_identical_aliases():
    gui = gui_aliases()
    assert list(gui) == list(ps.COLUMN_ALIASES)
    assert gui == ps.COLUMN_ALIASES


def test_gui_and_cli_have_identical_name_aliases():
    gui = json.loads(re.search(r"const NAME_ALIASES = (\[.*?\]);", HTML).group(1))
    assert gui == ps.NAME_ALIASES


def test_no_alias_is_listed_twice():
    seen = {}
    for key, aliases in ps.COLUMN_ALIASES.items():
        for a in aliases:
            assert a.lower() not in seen, f"{a!r} steht bei {seen.get(a.lower())} und {key}"
            seen[a.lower()] = key


@pytest.mark.parametrize("doc", ["README.md", "ANLEITUNG_pseudonym.md", "docs/column-reference.md", "CLAUDE.md"])
def test_docs_list_every_alias(doc):
    text = (ROOT / doc).read_text(encoding="utf-8").lower()
    missing = [a for aliases in ps.COLUMN_ALIASES.values() for a in aliases if a.lower() not in text]
    assert missing == []


def test_version_is_the_same_everywhere():
    assert f"v{ps.__version__} " in HTML
    assert f"v{ps.__version__}" in (ROOT / "docs" / "installation.md").read_text(encoding="utf-8")


def test_external_scripts_are_pinned_with_integrity():
    tags = re.findall(r"<script[^>]*\bsrc=[^>]*>", HTML)
    assert tags, "keine externen Skripte gefunden"
    for tag in tags:
        assert re.search(r'integrity="sha(384|512)-[A-Za-z0-9+/=]+"', tag), tag
        assert 'crossorigin="anonymous"' in tag, tag
        assert re.search(r"\d+\.\d+\.\d+", tag), tag


def test_gui_has_no_unescaped_sheet_name():
    assert "${sh.name}" not in HTML


def test_secret_field_does_not_offer_autocomplete():
    tag = re.search(r'<input[^>]*id="secretInput"[^>]*>', HTML).group(0)
    assert 'autocomplete="off"' in tag


def test_gitignore_blocks_all_data_formats():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    for pattern in ("*.csv", "*.tsv", "*.xlsx", "*.xlsm", "*.xls", "*.zip"):
        assert pattern in lines


def test_sources_contain_no_invisible_whitespace():
    """Unsichtbare Leerzeichen (geschuetztes Leerzeichen, Zeilentrenner U+2028 ...) gehoeren als
    Escape-Folge in den Code. Als echtes Zeichen sind sie nicht zu sehen, und U+2028 bricht JavaScript."""
    invisible = [0x00A0, 0x1680, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF] + list(range(0x2000, 0x200C))
    for name in ("pseudonym.py", "pseudonym_gui.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        found = sorted({f"U+{cp:04X}" for cp in invisible if chr(cp) in text})
        assert found == [], f"{name}: {found}"
