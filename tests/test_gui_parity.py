"""Gleichlauf GUI <-> CLI: Der JavaScript-Teil von pseudonym_gui.html laeuft in Node
(tests/gui_harness.js) und muss dieselben Bytes liefern wie pseudonym.py.

Voraussetzung: Node.js und die beiden Bibliotheken der GUI in einem Ordner, den die
Umgebungsvariable PSEUDO_GUI_LIBS nennt (siehe docs/development.md). Sonst werden
diese Tests uebersprungen. Alle Testdaten sind erfunden."""
import datetime
import json
import os
import random
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

import pseudonym as ps

ROOT = Path(__file__).parent.parent
LIBS = os.environ.get("PSEUDO_GUI_LIBS")
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(
    not (NODE and LIBS and (Path(LIBS) / "xlsx.full.min.js").exists() and (Path(LIBS) / "jszip.min.js").exists()),
    reason="Node.js oder PSEUDO_GUI_LIBS fehlt")

SECRET = "testSecret123"


def gui(tmp_path, jobs=(), evals=()):
    """Fuehrt Auftraege in der GUI aus. Gibt das Ergebnis-JSON zurueck."""
    spec = tmp_path / "auftrag.json"
    spec.write_text(json.dumps({"jobs": list(jobs), "eval": list(evals)}), encoding="utf-8")
    proc = subprocess.run([NODE, str(ROOT / "tests" / "gui_harness.js"), str(ROOT / "pseudonym_gui.html"),
                           LIBS, str(spec)], capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def job(files, mode, out_dir, **extra):
    out_dir.mkdir(parents=True, exist_ok=True)
    return dict({"files": [str(f) for f in files], "mode": mode, "secret": SECRET, "outDir": str(out_dir)}, **extra)


U = "utf-8"
CSV_CASES = {
    # Name: (Inhalt als Bytes, Zusatzspalten)
    "einfach.csv": ("Vorname;Familienname;Matrikelnummer;Punkte\nMax;Müller;01234567;5\n".encode(U), []),
    "komma_crlf.csv": ("Vorname,Familienname,E-Mail\r\nJürgen,Groß,j@example.org\r\n".encode(U), []),
    "bom.csv": (b"\xef\xbb\xbf" + "Vorname;Ort\nZoë;Gmünd\n".encode(U), []),
    "utf16le.csv": (b"\xff\xfe" + "Vorname\tE-Mail\r\nZoë\tz@example.org\r\n".encode("utf-16-le"), []),
    "utf16be.csv": (b"\xfe\xff" + "Vorname\tE-Mail\r\nZoë\tz@example.org\r\n".encode("utf-16-be"), []),
    "utf16_ohne_bom.csv": ("Vorname;Ort\r\nZoë;Gmünd\r\n".encode("utf-16-le"), []),
    "ansi.csv": ('"Familienname";"Vorname";"Ort"\r\n"Müller";"Jürgen";"Gmünd €"\r\n'.encode("cp1252"), []),
    "ansi_c1.csv": (b"Familienname;Notiz\nM\xfcller;x\x81\x8d\x8f\x90\x9dy\n", []),
    "mlw.csv": ("Export;Tertial 5\n\nFamilienname;Vorname;Name;E-Mail\nMuster;Max;Muster Max;m@example.org\n"
                "Test;Eva;Dr. Eva Test;e@example.org\nKlein;Tom;Tom Klein;\n".encode(U), []),
    "meta_komma.csv": ("Modul: Tertial 5, Gruppe A\nVorname;Familienname\nMax;Muster\n".encode(U), []),
    "meta_wie_kopf.csv": ("Prüfer;Dr. Beispiel\nFamilienname;Vorname\nMuster;Max\n".encode(U), []),
    "meta_mehrzeilig.csv": ('Titel;"Zeile A\nZeile B"\nVorname;Punkte\nMax;1\n'.encode(U), []),
    "mehrere_je_typ.csv": ("Vorname.x;Vorname.y;Telefon;Handy;E-Mail;Email;Name.x\n"
                           "Max;Moritz;0664 1;0664 2;a@example.org;b@example.org;Muster\n".encode(U), []),
    "doppelte_koepfe.csv": ("Vorname;Punkte;Punkte;;\nMax;1;2;a;b\n".encode(U), []),
    "unregelmaessig.csv": ("Vorname;Punkte\nMax;1;extra;noch\nEva\n\nTom;3\n\n".encode(U), []),
    "gemischt_quotes.csv": ('Vorname;Punkte\n"Max";1\nEva;"2"\n  Tom ; 3 \n'.encode(U), []),
    "quotes_im_wert.csv": ('"Vorname";"Notiz"\r\n"Max ""der Große""";"sagt ""Hallo"""\r\n'.encode(U), []),
    "trenner_im_wert.csv": ('Familienname;Vorname\n"Muster; jun.";Max\n'.encode(U), []),
    "crlf_in_zelle.csv": ('Vorname;Notiz\nMax;"Zeile A\r\nZeile B"\n'.encode(U), []),
    "ohne_zeilenende.csv": (b"Vorname;Punkte\r\nMax;1", []),
    "nur_name.csv": ("Bericht\n\nName;Punkte\nMuster Max;5\n".encode(U), []),
    "zusatzspalte.csv": ("Bericht\nKommentar;Punkte;Vorname\nGeheim;5;Max\n".encode(U), ["Kommentar", "Fehlt"]),
    "valuatic.csv": ("examiner_id,examiner_last_name,candidate_id,candidate_first_name,score\n"
                     "7,Beispiel,42,Anna,3\n".encode(U), []),
    "tab.tsv": ("Vorname\tFamilienname\tPunkte\nMax\tMuster\t1\n".encode(U), []),
    "emoji.csv": ("Vorname;Familienname\n\U0001f600 Max;Černý\n".encode(U), []),
}


def test_acceptance_vector_in_gui(tmp_path):
    out = gui(tmp_path, evals=['createCipher("testSecret123").then(c => c.encrypt("Mueller"))'])
    assert out["eval"] == ["a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc"]


def test_tokens_are_identical_for_random_values(tmp_path):
    rng = random.Random(7)
    alphabet = "abcXYZ 0123456789äöüßČřé'-.,;@\U0001f600漢"
    values = ["".join(rng.choice(alphabet) for _ in range(rng.randint(1, 60))).strip() or "x" for _ in range(300)]
    code = (f"createCipher({json.dumps(SECRET)}).then(async c => {{ const v = {json.dumps(values)}; "
            "const enc = []; for (const x of v) enc.push(await c.encrypt(x)); "
            "const dec = []; for (const t of enc) dec.push(await c.decrypt(t)); "
            "const wrong = await (await createCipher('falsch')).tryDecrypt(enc[0]); "
            "return { enc, dec, wrong, plain: await c.decrypt('Max') }; })")
    got = gui(tmp_path, evals=[code])["eval"][0]
    key = ps.derive_key(SECRET)
    assert got["enc"] == [ps.encrypt_value(key, v) for v in values]
    assert got["dec"] == values
    assert got["wrong"] is None and got["plain"] == "Max"


@pytest.mark.parametrize("mode", ["encrypt", "anonymize"])
def test_csv_output_is_byte_identical_to_cli(tmp_path, mode):
    src = tmp_path / "in"
    src.mkdir()
    jobs = []
    for name, (data, extra) in CSV_CASES.items():
        (src / name).write_bytes(data)
        jobs.append(job([src / name], mode, tmp_path / "gui", extraCols=extra))
    out = gui(tmp_path, jobs)
    for (name, (data, extra)), res in zip(CSV_CASES.items(), out["jobs"]):
        cli = tmp_path / "cli" / name
        cli.parent.mkdir(exist_ok=True)
        ps.process_file(str(src / name), str(cli), SECRET, mode, extra_cols=extra)
        result = res["results"][0]
        assert result["ok"], (name, result)
        assert (tmp_path / "gui" / result["name"]).read_bytes() == cli.read_bytes(), name


def test_csv_roundtrip_through_gui_is_byte_identical(tmp_path):
    """CLI verschluesselt, GUI entschluesselt: Das Original kommt Byte fuer Byte zurueck.
    Ausnahme laut Doku: reine ASCII-Pseudonym-Datei mit Umlauten im Ergebnis bekommt ein BOM."""
    src, pseudo = tmp_path / "in", tmp_path / "pseudo"
    src.mkdir()
    pseudo.mkdir()
    jobs = []
    for name, (data, extra) in CSV_CASES.items():
        (src / name).write_bytes(data)
        ps.process_file(str(src / name), str(pseudo / name), SECRET, "encrypt", extra_cols=extra)
        jobs.append(job([pseudo / name], "decrypt", tmp_path / "gui", extraCols=extra))
    out = gui(tmp_path, jobs)
    for (name, (data, extra)), res in zip(CSV_CASES.items(), out["jobs"]):
        restored = (tmp_path / "gui" / res["results"][0]["name"]).read_bytes()
        cli = tmp_path / "cli_restored.csv"
        ps.process_file(str(pseudo / name), str(cli), SECRET, "decrypt", extra_cols=extra)
        assert restored == cli.read_bytes(), name
        assert restored in (data, b"\xef\xbb\xbf" + data), name


def make_xlsx(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Liste"
    ws.append(["Stand", "2026-04-23", None, None, None, None, None])
    ws.append(["Vorname", "Familienname", "Name", "Matrikelnummer", "Geburtsdatum", "Pruefungsdatum", "Punkte", "Summe"])
    ws.append(["Max", "Müller", "Müller Max", 1234567, datetime.datetime(2000, 1, 31),
               datetime.datetime(2026, 4, 23), 17.5, "=G3*2"])
    ws.append([" Eva ", "Test", "Dr. Eva Test", "01234568", datetime.datetime(1999, 12, 24, 13, 30, 5),
               datetime.datetime(2026, 4, 24), 12, "=G4*2"])
    ws.append(["Tom", "Klein", "Tom Klein", 1234569.0, "24.12.1998", None, 3.25, None])
    for cell in ("E3", "E4", "F3", "F4"):
        ws[cell].number_format = "DD.MM.YYYY"
    ws2 = wb.create_sheet("<img src=x>")
    ws2.append(["Fach", "Punkte"])
    ws2.append(["Anatomie", 5])
    ws3 = wb.create_sheet("Pruefer")
    ws3.append(["Examiner", "Telefon"])
    ws3.append(["Dr. Beispiel", 6641234567])
    wb.properties.creator = "Erika Beispiel"
    wb.save(path)


def cells(path, sheet):
    ws = load_workbook(path)[sheet]
    return [[c.value for c in row] for row in ws.iter_rows()]


def test_xlsx_tokens_and_types_match_cli(tmp_path):
    src = tmp_path / "liste.xlsx"
    make_xlsx(src)
    out = gui(tmp_path, [job([src], "encrypt", tmp_path / "gui")],
              evals=["document.getElementById('sheetTabs').innerHTML"])
    assert out["jobs"][0]["results"][0]["ok"], out["jobs"][0]
    ps.process_file(str(src), str(tmp_path / "cli.xlsx"), SECRET, "encrypt")
    g, c = tmp_path / "gui" / "liste_pseudo.xlsx", tmp_path / "cli.xlsx"
    for sheet in ("Liste", "<img src=x>", "Pruefer"):
        gui_rows, cli_rows = cells(g, sheet), cells(c, sheet)
        assert gui_rows == cli_rows, sheet
    rows = cells(g, "Liste")
    assert rows[2][5] == datetime.datetime(2026, 4, 23) and rows[2][6] == 17.5 and rows[2][7] == "=G3*2"
    assert load_workbook(g)["Liste"]["F3"].number_format == "DD.MM.YYYY"
    # Blattname wird in der Seite maskiert
    assert "&lt;img src=x&gt;" in out["eval"][0] and "<img" not in out["eval"][0]


def test_xlsx_roundtrip_through_gui(tmp_path):
    src = tmp_path / "liste.xlsx"
    make_xlsx(src)
    ps.process_file(str(src), str(tmp_path / "liste_pseudo.xlsx"), SECRET, "encrypt")
    out = gui(tmp_path, [job([tmp_path / "liste_pseudo.xlsx"], "decrypt", tmp_path / "gui")])
    assert out["jobs"][0]["results"][0]["ok"], out["jobs"][0]
    ps.process_file(str(tmp_path / "liste_pseudo.xlsx"), str(tmp_path / "cli.xlsx"), SECRET, "decrypt")
    name = out["jobs"][0]["results"][0]["name"]
    for sheet in ("Liste", "Pruefer"):
        assert cells(tmp_path / "gui" / name, sheet) == cells(tmp_path / "cli.xlsx", sheet)
    assert cells(tmp_path / "gui" / name, "Liste")[3][:4] == [" Eva ", "Test", "Dr. Eva Test", "01234568"]


def test_xlsx_anonymize_matches_cli(tmp_path):
    src = tmp_path / "liste.xlsx"
    make_xlsx(src)
    out = gui(tmp_path, [job([src], "anonymize", tmp_path / "gui", secret="")])
    assert out["jobs"][0]["results"][0]["ok"], out["jobs"][0]
    ps.process_file(str(src), str(tmp_path / "cli.xlsx"), None, "anonymize")
    g = tmp_path / "gui" / "liste_anonym.xlsx"
    for sheet in ("Liste", "Pruefer"):
        assert cells(g, sheet) == cells(tmp_path / "cli.xlsx", sheet)
    assert cells(g, "Liste")[2][:5] == [None] * 5
    with zipfile.ZipFile(g) as z:
        assert not any(b"Erika" in z.read(n) for n in z.namelist())


def test_refusals_match_cli(tmp_path):
    """Falsches Secret, keine erkannten Spalten, leere Datei: kein Ergebnis, klare Meldung."""
    (tmp_path / "fach.csv").write_text("Fach;Punkte\nAnatomie;5\n", encoding="utf-8")
    (tmp_path / "leer.csv").write_bytes(b"")
    (tmp_path / "ok.csv").write_text("Vorname\nMax\n", encoding="utf-8")
    ps.process_file(str(tmp_path / "ok.csv"), str(tmp_path / "ok_pseudo.csv"), SECRET, "encrypt")
    out = gui(tmp_path, [
        job([tmp_path / "fach.csv", tmp_path / "leer.csv", tmp_path / "ok.csv"], "encrypt", tmp_path / "g1"),
        job([tmp_path / "ok_pseudo.csv"], "decrypt", tmp_path / "g2", secret="falsch"),
        job([tmp_path / "ok.csv"], "decrypt", tmp_path / "g3"),
    ])
    first = {r["source"]: r for r in out["jobs"][0]["results"]}
    assert not first["fach.csv"]["ok"] and "Spalten" in first["fach.csv"]["error"]
    assert not first["leer.csv"]["ok"] and "leer" in first["leer.csv"]["error"]
    assert first["ok.csv"]["ok"]
    assert [p.name for p in (tmp_path / "g1").iterdir()] == ["ok_pseudo.csv"]
    for res, folder in ((out["jobs"][1], "g2"), (out["jobs"][2], "g3")):
        assert not res["results"][0]["ok"] and "Secret" in res["results"][0]["error"]
        assert list((tmp_path / folder).iterdir()) == []


def test_zip_input_matches_cli(tmp_path):
    zp = tmp_path / "export.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("gruppeA/liste.csv", "Vorname;Familienname\nMax;Muster\n")
        zf.writestr("gruppeB/liste.csv", "Vorname;Familienname\nEva;Test\n")
        zf.writestr("__MACOSX/._liste.csv", "muell")
        zf.writestr("gruppeA/.versteckt.csv", "Vorname\nGeheim\n")
        zf.writestr("liesmich.txt", "kein Datenformat")
    out = gui(tmp_path, [job([zp], "encrypt", tmp_path / "gui", download=True)])["jobs"][0]
    assert [r["name"] for r in out["results"]] == ["liste_pseudo.csv", "liste_1_pseudo.csv"]
    assert out["download"]["name"] == "export_pseudo.zip"
    with zipfile.ZipFile(tmp_path / "gui" / "export_pseudo.zip") as z:
        assert sorted(z.namelist()) == ["liste_1_pseudo.csv", "liste_pseudo.csv"]
    assert ps.main(["encrypt", str(zp), "--secret", SECRET, "--output-dir", str(tmp_path / "cli")]) == 0
    for name in ("liste_pseudo.csv", "liste_1_pseudo.csv"):
        assert (tmp_path / "gui" / name).read_bytes() == (tmp_path / "cli" / name).read_bytes()


def test_same_names_do_not_get_lost_in_the_download(tmp_path):
    a, b = tmp_path / "x" / "liste.csv", tmp_path / "y" / "liste.csv"
    for f, v in ((a, "Max"), (b, "Eva")):
        f.parent.mkdir()
        f.write_text(f"Vorname\n{v}\n", encoding="utf-8")
    out = gui(tmp_path, [job([a, b], "encrypt", tmp_path / "gui", download=True)])["jobs"][0]
    with zipfile.ZipFile(tmp_path / "gui" / out["download"]["name"]) as z:
        assert sorted(z.namelist()) == ["liste_pseudo.csv", "liste_pseudo_1.csv"]


def test_unsupported_and_unreadable_files_are_reported(tmp_path):
    (tmp_path / "alt.xls").write_bytes(b"x")
    (tmp_path / "kaputt.xlsx").write_bytes(b"das ist keine Excel-Datei")
    (tmp_path / "ok.csv").write_text("Vorname\nMax\n", encoding="utf-8")
    out = gui(tmp_path, [job([tmp_path / "alt.xls", tmp_path / "kaputt.xlsx", tmp_path / "ok.csv"],
                             "encrypt", tmp_path / "gui")])["jobs"][0]
    assert [q["name"] for q in out["queue"]] == ["ok.csv"]
    assert len(out["notices"]) == 2 and "alt.xls" in out["notices"][0] and "kaputt.xlsx" in out["notices"][1]


def test_results_disappear_when_the_input_changes(tmp_path):
    (tmp_path / "a.csv").write_text("Vorname\nMax\n", encoding="utf-8")
    hidden = "document.getElementById('resultCard').classList.contains('hidden') && batchResults.length === 0"
    out = gui(tmp_path, [job([tmp_path / "a.csv"], "encrypt", tmp_path / "gui")], evals=[
        f"!({hidden})",
        f"(setMode('decrypt'), {hidden})",
    ])
    assert out["eval"] == [True, True]


def test_secret_is_never_written_to_storage(tmp_path):
    (tmp_path / "a.csv").write_text("Vorname\nMax\n", encoding="utf-8")
    out = gui(tmp_path, [job([tmp_path / "a.csv"], "encrypt", tmp_path / "gui", secret="streng-geheim-4711")])
    writes = out["jobs"][0]["storageWrites"]
    assert [k for k, _ in writes] == ["pseudo_history"]
    assert "streng-geheim-4711" not in json.dumps(out)
