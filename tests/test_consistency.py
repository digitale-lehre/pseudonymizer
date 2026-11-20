"""Gleichlauf: Alias-Listen, Versionsnummer und Doku muessen zum Code passen."""
import json
import re
from pathlib import Path

import pytest

import pseudonym as ps

ROOT = Path(__file__).parent.parent
HTML = (ROOT / "pseudonym_gui.html").read_text(encoding="utf-8")
LIB_BLOCK = re.compile(r'<script id="(lib-[a-z]+)"([^>]*)>.*?</script>', re.S)
OWN_HTML = LIB_BLOCK.sub("", HTML)   # eigener Code, ohne die eingebetteten Bibliotheken
DOCS = ["README.md", "ANLEITUNG_pseudonym.md", "CLAUDE.md"] + sorted(
    str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "docs").glob("*.md"))


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


def test_gui_loads_nothing_from_the_network():
    """Die Seite ist eigenstaendig: keine fremden Skripte, Stylesheets, Bilder oder Schriften."""
    assert len(LIB_BLOCK.findall(HTML)) == 2
    for pattern in (r"<script[^>]*\bsrc\s*=", r"<link\b", r"<img[^>]*\bsrc\s*=\s*[\"']?https?:",
                    r"@import", r"url\(\s*[\"']?https?:", r"\bfetch\(", r"XMLHttpRequest", r"sendBeacon"):
        assert not re.search(pattern, OWN_HTML, re.I), pattern


def test_content_security_policy_allows_no_foreign_address():
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]*)"', HTML).group(1)
    assert "http" not in csp and "*" not in csp
    rules = dict(part.strip().split(" ", 1) for part in csp.split(";"))
    assert rules["default-src"] == "'none'"
    assert rules["script-src"] == "'unsafe-inline'"
    assert rules["connect-src"] == "'none'"


@pytest.mark.parametrize("doc", DOCS)
def test_docs_name_the_embedded_library_versions(doc):
    versions = {key: re.search(r'data-version="([^"]+)"', attrs).group(1) for key, attrs in LIB_BLOCK.findall(HTML)}
    text = (ROOT / doc).read_text(encoding="utf-8")
    for name, key in (("SheetJS", "lib-xlsx"), ("JSZip", "lib-jszip")):
        for found in re.findall(name + r" (\d+\.\d+\.\d+)", text):
            assert found == versions[key], f"{doc} nennt {name} {found}, eingebettet ist {versions[key]}"


DEVELOPER_DOCS = ("CLAUDE.md", "docs/development.md")   # nennen die Quellen fuer tools/gui_libs.py


@pytest.mark.parametrize("doc", DOCS)
def test_docs_do_not_send_users_to_the_network(doc):
    text = (ROOT / doc).read_text(encoding="utf-8")
    outdated = ["PSEUDO_GUI_LIBS", "Internetverbindung beim Start", "integrity"]
    if doc not in DEVELOPER_DOCS:
        outdated += ["cdn.sheetjs.com", "cdnjs.cloudflare.com"]
    for old in outdated:
        assert old not in text, f"{doc}: {old}"


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
    sources = {"pseudonym.py": (ROOT / "pseudonym.py").read_text(encoding="utf-8"),
               "pseudonym_gui.html": OWN_HTML,
               "tools/gui_libs.py": (ROOT / "tools" / "gui_libs.py").read_text(encoding="utf-8")}
    for name, text in sources.items():
        found = sorted({f"U+{cp:04X}" for cp in invisible if chr(cp) in text})
        assert found == [], f"{name}: {found}"
