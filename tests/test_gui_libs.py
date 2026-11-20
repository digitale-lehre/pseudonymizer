"""Tests fuer die eingebetteten Bibliotheken der GUI und fuer tools/gui_libs.py.

Kein Test braucht das Netz: Die Abfragen beim Hersteller sind durch eine Attrappe ersetzt."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import gui_libs  # noqa: E402

HTML = (ROOT / "pseudonym_gui.html").read_bytes().decode("utf-8")   # Zeilenenden unveraendert


# ---------- Die echte Seite ----------

def test_both_libraries_are_embedded():
    libs = gui_libs.read_embedded(HTML)
    assert sorted(libs) == ["lib-jszip", "lib-xlsx"]
    for lib in libs.values():
        assert re.fullmatch(r"\d+\.\d+\.\d+", lib["version"])
        assert len(lib["code"]) > 50_000


def test_embedded_code_matches_its_checksum():
    for key, lib in gui_libs.read_embedded(HTML).items():
        assert gui_libs.checksum(lib["code"]) == lib["sha512"], key


def test_embedded_code_cannot_end_its_script_block_early():
    for key, lib in gui_libs.read_embedded(HTML).items():
        assert gui_libs.problems(lib["code"]) == [], key


def test_libraries_stand_after_the_own_code():
    assert HTML.index('<script id="app">') < HTML.index('<script id="lib-xlsx"') < HTML.index('<script id="lib-jszip"')


# ---------- Versionsvergleich ----------

@pytest.mark.parametrize("candidate, current, expected", [
    ("0.20.10", "0.20.3", True),
    ("0.21.0", "0.20.3", True),
    ("1.0.0", "0.20.3", True),
    ("0.20.3", "0.20.3", False),
    ("0.20.2", "0.20.3", False),
    ("v3.10.2", "3.10.1", True),
])
def test_is_newer(candidate, current, expected):
    assert gui_libs.is_newer(candidate, current) is expected


# ---------- check und update mit einer kleinen Beispielseite ----------

XLSX_OLD, XLSX_NEW = "var XLSX = 1;\n", "var XLSX = 2; // ä\n"
ZIP_OLD = "var JSZip = 1;"


def page(xlsx=XLSX_OLD, xlsx_version="1.0.0", zip_code=ZIP_OLD, zip_version="3.0.0"):
    return ('<html>\r\n<script id="app">\r\nlet a = 1;\r\n</script>\r\n'
            + gui_libs.block("lib-xlsx", xlsx_version, xlsx) + "\r\n"
            + gui_libs.block("lib-jszip", zip_version, zip_code) + "\r\n</html>\r\n")


def vendor(xlsx_latest="1.0.0", zip_latest="3.0.0", files=None):
    """Attrappe fuer die Server der Hersteller."""
    answers = {
        gui_libs.LIBRARIES["lib-xlsx"]["latest"]: json.dumps({"version": xlsx_latest}).encode(),
        gui_libs.LIBRARIES["lib-jszip"]["latest"]: json.dumps({"version": zip_latest}).encode(),
        gui_libs.LIBRARIES["lib-xlsx"]["file"].format(version="1.0.0"): XLSX_OLD.encode("utf-8"),
        gui_libs.LIBRARIES["lib-xlsx"]["file"].format(version="1.0.1"): XLSX_NEW.encode("utf-8"),
        gui_libs.LIBRARIES["lib-jszip"]["file"].format(version="3.0.0"): ZIP_OLD.encode("utf-8"),
    }
    answers.update(files or {})

    def fetch(url):
        if url not in answers:
            raise OSError("nicht erreichbar: " + url)
        return answers[url]
    return fetch


def write_page(tmp_path, text):
    path = tmp_path / "seite.html"
    path.write_bytes(text.encode("utf-8"))
    return path


def test_check_is_fine_when_everything_is_current(tmp_path, capsys):
    path = write_page(tmp_path, page())
    assert gui_libs.check(path, fetch=vendor()) == 0
    out = capsys.readouterr().out
    assert "SheetJS 1.0.0" in out and "JSZip 3.0.0" in out


def test_check_reports_a_newer_version(tmp_path, capsys):
    path = write_page(tmp_path, page())
    assert gui_libs.check(path, fetch=vendor(xlsx_latest="1.0.1")) == 1
    out = capsys.readouterr().out
    assert "1.0.1" in out and "gui_libs.py update" in out


def test_check_reports_code_that_differs_from_the_vendor_file(tmp_path, capsys):
    path = write_page(tmp_path, page(xlsx="var XLSX = 'veraendert';\n"))
    assert gui_libs.check(path, fetch=vendor()) == 1
    assert "weicht" in capsys.readouterr().out


def test_check_reports_an_edited_block_without_asking_the_vendor(tmp_path, capsys):
    text = page().replace("var XLSX = 1;", "var XLSX = 9;")   # Code geaendert, Pruefsumme nicht
    assert gui_libs.check(write_page(tmp_path, text), fetch=vendor()) == 1
    assert "Pruefsumme" in capsys.readouterr().out


def test_check_says_so_when_the_vendor_cannot_be_reached(tmp_path, capsys):
    def offline(url):
        raise OSError("kein Netz")
    assert gui_libs.check(write_page(tmp_path, page()), fetch=offline) == 2
    assert "nicht pruefen" in capsys.readouterr().out


def test_update_embeds_the_latest_version_and_leaves_the_rest_alone(tmp_path):
    path = write_page(tmp_path, page())
    assert gui_libs.update(path, fetch=vendor(xlsx_latest="1.0.1")) == 0
    text = path.read_bytes().decode("utf-8")
    libs = gui_libs.read_embedded(text)
    assert libs["lib-xlsx"]["version"] == "1.0.1"
    assert libs["lib-xlsx"]["code"] == XLSX_NEW
    assert libs["lib-xlsx"]["sha512"] == gui_libs.checksum(XLSX_NEW)
    assert libs["lib-jszip"]["version"] == "3.0.0"
    assert text == page(xlsx=XLSX_NEW, xlsx_version="1.0.1")
    assert gui_libs.check(path, fetch=vendor(xlsx_latest="1.0.1")) == 0


def test_update_changes_nothing_when_everything_is_current(tmp_path):
    path = write_page(tmp_path, page())
    before = path.read_bytes()
    assert gui_libs.update(path, fetch=vendor()) == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize("bad", [b"a = '</script>';", b"a = '<SCRIPT>';", b"a = 1;\r\n", b"\xff\xfe"])
def test_update_refuses_code_that_cannot_be_embedded_unchanged(tmp_path, bad):
    path = write_page(tmp_path, page())
    before = path.read_bytes()
    files = {gui_libs.LIBRARIES["lib-xlsx"]["file"].format(version="1.0.1"): bad}
    assert gui_libs.update(path, fetch=vendor(xlsx_latest="1.0.1", files=files)) == 1
    assert path.read_bytes() == before
