"""Tests fuer Kryptografie, Spaltenerkennung, CSV- und XLSX-Verarbeitung.

Alle Testdaten sind erfunden."""
import datetime
import io
import re
import time
import zipfile
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

import pseudonym as ps

SECRET = "testSecret123"
TOKEN = re.compile(r"^[A-Za-z0-9_-]{43,}$")


def encrypt(tmp_path, data, name="in.csv", sep=None, extra_cols=None, secret=SECRET):
    """Schreibt data (bytes oder str) und pseudonymisiert. Gibt die Ausgabe-Bytes zurueck."""
    src = tmp_path / name
    src.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))
    out = tmp_path / ("pseudo_" + name)
    ps.process_file(str(src), str(out), secret, "encrypt", sep, extra_cols=extra_cols)
    return out.read_bytes()


def roundtrip(tmp_path, data, name="in.csv", sep=None, extra_cols=None):
    """Pseudonymisiert und fuehrt zurueck. Gibt (pseudo_bytes, restored_bytes) zurueck."""
    pseudo = encrypt(tmp_path, data, name, sep, extra_cols)
    back = tmp_path / ("restored_" + name)
    ps.process_file(str(tmp_path / ("pseudo_" + name)), str(back), SECRET, "decrypt", sep,
                    extra_cols=extra_cols)
    return pseudo, back.read_bytes()


def xlsx(path, rows, sheet="Tabelle1"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


# ---------------------------------------------------------------- Kryptografie

def test_acceptance_vector():
    """Abnahmewert aus CLAUDE.md: muss in CLI und GUI gleich sein."""
    key = ps.derive_key("testSecret123")
    assert ps.encrypt_value(key, "Mueller") == "a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc"


@pytest.mark.parametrize("plain", ["Max", "Maxim", "1234567", "Müller", "a@x.at", "Dr. Eva Test"])
def test_decrypt_value_leaves_plaintext_unchanged(plain):
    """Klartext ist kein Pseudonym und bleibt unveraendert (kein angehaengtes '=')."""
    assert ps.decrypt_value(ps.derive_key(SECRET), plain) == plain


def test_decrypt_value_with_wrong_secret_returns_token_unchanged():
    token = ps.encrypt_value(ps.derive_key("richtig"), "Mustermann")
    assert ps.decrypt_value(ps.derive_key("falsch"), token) == token


def test_try_decrypt_never_returns_garbage_for_wrong_secret():
    """Ein falsches Secret wird bei jedem Pseudonym erkannt (Pruefung des Startwerts)."""
    k1, k2 = ps.derive_key("richtig"), ps.derive_key("falsch")
    for i in range(3000):
        assert ps.try_decrypt(k2, ps.encrypt_value(k1, f"Wert{i}")) is None
    assert ps.try_decrypt(k1, ps.encrypt_value(k1, "Wert")) == "Wert"


# ---------------------------------------------------------- Spaltenerkennung

def test_all_columns_of_one_type_are_encrypted(tmp_path):
    """Telefon UND Handy, E-Mail UND Email: keine Spalte bleibt im Klartext."""
    data = ("Vorname;Familienname;Telefon;Handy;E-Mail;Email\n"
            "Max;Muster;0664 111;0664 222;a@x.at;b@y.at\n")
    pseudo, restored = roundtrip(tmp_path, data)
    for plain in ("Max", "Muster", "0664 111", "0664 222", "a@x.at", "b@y.at"):
        assert plain.encode() not in pseudo
    assert restored == data.encode()


def test_merge_suffix_columns_are_all_encrypted(tmp_path):
    data = "Vorname.x;Vorname.y;Name.x\nMax;Moritz;Muster\n"
    pseudo = encrypt(tmp_path, data)
    assert b"Max" not in pseudo and b"Moritz" not in pseudo and b"Muster" not in pseudo


def test_header_row_is_the_row_with_most_recognized_columns():
    rows = [["Prüfer", "Dr. Beispiel"], ["Familienname", "Vorname", "Matrikelnummer"], ["Muster", "Max", "1"]]
    assert ps.find_header_row(rows) == 1


def test_metadata_row_that_looks_like_a_header_is_not_used(tmp_path):
    data = "Prüfer;Dr. Beispiel\nFamilienname;Vorname\nMuster;Max\n"
    pseudo, restored = roundtrip(tmp_path, data)
    lines = pseudo.decode().split("\n")
    assert lines[0] == "Prüfer;Dr. Beispiel"
    assert lines[1] == "Familienname;Vorname"
    assert all(TOKEN.match(c) for c in lines[2].split(";"))
    assert restored == data.encode()


def test_name_only_file_with_metadata_rows(tmp_path):
    data = "Export vom 01.01.2026\n\nName;Punkte\nMuster Max;5\n"
    pseudo, restored = roundtrip(tmp_path, data)
    assert b"Muster Max" not in pseudo
    assert restored == data.encode()


def test_extra_cols_only_file_with_metadata_rows(tmp_path):
    data = "Bericht\nKommentar;Punkte\nGeheim;5\n"
    pseudo = encrypt(tmp_path, data, extra_cols=["Kommentar"])
    assert b"Geheim" not in pseudo and pseudo.startswith(b"Bericht\nKommentar;Punkte\n")


def test_old_alias_spellings_still_recognized():
    """Die Alias-Liste wurde entdoppelt: alle Schreibweisen gelten weiter (case-insensitive)."""
    for header, key in [("FAMILIENNAME", "familienname"), ("zuname", "familienname"),
                        ("Firstname", "vorname"), ("MATNR", "matnr"), ("Registration_Number", "matnr"),
                        ("e-mail", "email"), ("PRÜFER", "pruefer"), ("PRUFER", "pruefer"),
                        ("display name", "anzeigename"), ("TELEFONNUMMER", "telefon"),
                        ("Birthdate", "geburtsdatum"), ("EXAMINER_LAST_NAME", "examiner_nachname")]:
        assert ps.find_identity_cols([header]) == {key: header}


# ------------------------------------------------------- CSV: Struktur bleibt

@pytest.mark.parametrize("data", [
    "Vorname;Punkte;Punkte\nMax;1;2\n",                       # doppelte Spaltennamen
    "Vorname;;\nMax;a;b\n",                                   # leere Spaltennamen
    "Vorname;Punkte\nMax;1;extra;noch\nEva\n",                # zu lange und zu kurze Zeilen
    "Vorname;Punkte\nMax;1\n\nEva;2\n\n",                     # Leerzeilen
    'Vorname;Punkte\n"Max";1\nEva;"2"\n',                     # gemischte Anfuehrungszeichen
    "Vorname;Punkte\n  Max ; 1 \n",                           # Leerzeichen am Rand
    'Vorname;Notiz\nMax;"Zeile A\r\nZeile B"\n',              # LF-Datei mit CRLF in einer Zelle
    'Titel;"Zeile A\nZeile B"\nVorname;Punkte\nMax;1\n',      # Zeilenumbruch vor der Kopfzeile
    '"Vorname";"Notiz"\r\n"Max";"sagt ""Hallo"""\r\n',        # verdoppelte Anfuehrungszeichen
    "Vorname;Punkte\r\nMax;1",                                # kein Zeilenende am Schluss
    'Familienname;Vorname\n"Muster; jun.";Max\n',             # Trennzeichen im Wert
])
def test_csv_roundtrip_is_byte_identical(tmp_path, data):
    pseudo, restored = roundtrip(tmp_path, data)
    assert b"Max" not in pseudo
    assert restored == data.encode()


def test_csv_untouched_cells_keep_their_bytes(tmp_path):
    """Nur die Identitaetszellen aendern sich, alles andere bleibt Zeichen fuer Zeichen."""
    data = 'Vorname;Punkte;Punkte\n Max ;"1"; 2\n'
    pseudo = encrypt(tmp_path, data).decode()
    head, row = pseudo.split("\n")[:2]
    assert head == "Vorname;Punkte;Punkte"
    cells = row.split(";")
    assert cells[1:] == ['"1"', " 2"]
    assert cells[0].startswith(" ") and cells[0].endswith(" ") and TOKEN.match(cells[0].strip())


def test_token_ignores_surrounding_whitespace(tmp_path):
    a = encrypt(tmp_path, "Vorname\nMax\n", "a.csv").split(b"\n")[1]
    b = encrypt(tmp_path, "Vorname\n Max \n", "b.csv").split(b"\n")[1]
    assert b.strip() == a


@pytest.mark.parametrize("codec,bom", [("utf-8", b""), ("utf-8", b"\xef\xbb\xbf"),
                                       ("utf-16-le", b"\xff\xfe"), ("utf-16-be", b"\xfe\xff"),
                                       ("utf-16-le", b""), ("utf-16-be", b""), ("cp1252", b"")])
def test_csv_roundtrip_all_encodings(tmp_path, codec, bom):
    text = "Familienname;Vorname;Ort\r\nMüller;Jürgen;Gmünd\r\n"
    data = bom + text.encode(codec)
    pseudo, restored = roundtrip(tmp_path, data)
    assert "Müller".encode(codec) not in pseudo
    assert restored == data


def test_decrypt_falls_back_to_utf8_bom_when_cp1252_cannot_encode(tmp_path):
    """Pseudonym-Datei in Windows-1252, der zurueckgefuehrte Name passt nicht hinein."""
    key = ps.derive_key(SECRET)
    token = ps.encrypt_value(key, "Černý")
    src = tmp_path / "p.csv"
    src.write_bytes(f"Familienname;Ort\n{token};Gmünd\n".encode("cp1252"))
    out = tmp_path / "r.csv"
    ps.process_file(str(src), str(out), SECRET, "decrypt")
    assert out.read_bytes() == b"\xef\xbb\xbf" + "Familienname;Ort\nČerný;Gmünd\n".encode("utf-8")


# ------------------------------------------------------------ CSV: Trennzeichen

@pytest.mark.parametrize("sep", [";", ",", "\t"])
def test_separator_is_detected(tmp_path, sep):
    data = sep.join(["Vorname", "Familienname", "Punkte"]) + "\n" + sep.join(["Max", "Muster", "1"]) + "\n"
    pseudo, restored = roundtrip(tmp_path, data)
    assert b"Max" not in pseudo and restored == data.encode()


def test_separator_detection_ignores_comma_in_first_metadata_line(tmp_path):
    data = "Modul: Tertial 5, Gruppe A\nVorname;Familienname\nMax;Muster\n"
    pseudo, restored = roundtrip(tmp_path, data)
    assert pseudo.startswith(b"Modul: Tertial 5, Gruppe A\nVorname;Familienname\n")
    assert b"Max" not in pseudo and restored == data.encode()


# ------------------------------------------------------------------ Name-Spalte

def test_name_composite_is_decided_per_row(tmp_path):
    data = ("Vorname;Familienname;Name\n"
            "Max;Muster;Muster Max\n"
            "Eva;Test;Dr. Eva Test\n"
            "Anna;Bei;Bei, Anna\n"
            "Tom;Klein;Tom Klein\n")
    pseudo, restored = roundtrip(tmp_path, data)
    rows = [r.split(";") for r in pseudo.decode().split("\n")[1:5]]
    assert rows[0][2] == f"{rows[0][1]} {rows[0][0]}"      # Familienname Vorname
    assert rows[3][2] == f"{rows[3][0]} {rows[3][1]}"      # Vorname Familienname
    assert TOKEN.match(rows[1][2]) and TOKEN.match(rows[2][2])   # ganzer Wert, ein Pseudonym
    assert restored == data.encode()


def test_name_composite_with_empty_first_data_row(tmp_path):
    data = "Vorname;Familienname;Name\n;;\nEva;Test;Dr. Eva Test\n"
    assert roundtrip(tmp_path, data)[1] == data.encode()


def test_old_composite_pseudo_files_still_decrypt(tmp_path):
    """Dateien aelterer Versionen: Name = 'Token Token' wird weiter zurueckgefuehrt."""
    key = ps.derive_key(SECRET)
    fam, vor = ps.encrypt_value(key, "Muster"), ps.encrypt_value(key, "Max")
    src = tmp_path / "alt_pseudo.csv"
    src.write_text(f"Vorname;Familienname;Name\n{vor};{fam};{fam} {vor}\n", encoding="utf-8")
    out = tmp_path / "alt.csv"
    ps.process_file(str(src), str(out), SECRET, "decrypt")
    assert out.read_text(encoding="utf-8") == "Vorname;Familienname;Name\nMax;Muster;Muster Max\n"


# ---------------------------------------------------------- Falsches Secret usw.

def test_wrong_secret_is_reported_and_writes_no_file(tmp_path):
    encrypt(tmp_path, "Vorname;Familienname\nMax;Muster\nEva;Test\n")
    out = tmp_path / "restored.csv"
    with pytest.raises(ps.PseudoError, match="Secret"):
        ps.process_file(str(tmp_path / "pseudo_in.csv"), str(out), "falsch", "decrypt")
    assert not out.exists()


def test_decrypt_keeps_plaintext_rows_and_counts_them(tmp_path):
    """Nachgetragene Klartextzeile in einer Pseudonym-Datei bleibt unveraendert."""
    pseudo = encrypt(tmp_path, "Vorname;Familienname\nMax;Muster\n")
    src = tmp_path / "gemischt.csv"
    src.write_bytes(pseudo + b"Eva;Test\n")
    out = tmp_path / "gemischt_restored.csv"
    stats = ps.process_file(str(src), str(out), SECRET, "decrypt")
    assert out.read_bytes() == b"Vorname;Familienname\nMax;Muster\nEva;Test\n"
    assert stats["cells"] == 2 and stats["failed"] == 2


def test_decrypting_a_plain_file_is_refused(tmp_path):
    src = tmp_path / "klar.csv"
    src.write_text("Vorname;Matrikelnummer\nMax;1234567\n", encoding="utf-8")
    with pytest.raises(ps.PseudoError):
        ps.process_file(str(src), str(tmp_path / "x.csv"), SECRET, "decrypt")
    assert not (tmp_path / "x.csv").exists()


def test_encrypting_twice_gives_a_warning(tmp_path, capsys):
    encrypt(tmp_path, "Vorname\nMax\n")
    capsys.readouterr()
    ps.process_file(str(tmp_path / "pseudo_in.csv"), str(tmp_path / "doppelt.csv"), SECRET, "encrypt")
    assert "bereits" in capsys.readouterr().out


def test_file_without_recognized_columns_is_refused(tmp_path):
    for name in ("fach.csv", "fach.xlsx"):
        src = tmp_path / name
        if name.endswith(".csv"):
            src.write_text("Fach;Punkte\nAnatomie;5\n", encoding="utf-8")
        else:
            xlsx(src, [["Fach", "Punkte"], ["Anatomie", 5]])
        out = tmp_path / ("out_" + name)
        with pytest.raises(ps.PseudoError, match="Spalten"):
            ps.process_file(str(src), str(out), SECRET, "encrypt")
        assert not out.exists()


def test_unknown_extra_col_is_reported(tmp_path, capsys):
    encrypt(tmp_path, "Vorname;Kommentar\nMax;x\n", extra_cols=["Komentar"])
    assert "Komentar" in capsys.readouterr().out


def test_empty_file_gives_a_clear_error(tmp_path):
    src = tmp_path / "leer.csv"
    src.write_bytes(b"")
    with pytest.raises(ps.PseudoError, match="leer"):
        ps.process_file(str(src), str(tmp_path / "o.csv"), SECRET, "encrypt")


# ------------------------------------------------------------------------ XLSX

def test_xlsx_roundtrip_with_several_columns_per_type(tmp_path):
    src = xlsx(tmp_path / "a.xlsx", [["Vorname", "Telefon", "Handy", "Punkte"], ["Max", "0664 1", "0664 2", 17.5]])
    ps.process_file(str(src), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    row = [c.value for c in load_workbook(tmp_path / "p.xlsx").active[2]]
    assert all(TOKEN.match(v) for v in row[:3]) and row[3] == 17.5
    ps.process_file(str(tmp_path / "p.xlsx"), str(tmp_path / "r.xlsx"), SECRET, "decrypt")
    assert [c.value for c in load_workbook(tmp_path / "r.xlsx").active[2]] == ["Max", "0664 1", "0664 2", 17.5]


def test_xlsx_other_columns_keep_type_and_format(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Vorname", "Pruefungsdatum", "Punkte", "Summe"])
    ws.append(["Max", datetime.datetime(2026, 4, 23), 17.5, "=C2*2"])
    ws["B2"].number_format = "DD.MM.YYYY"
    wb.save(tmp_path / "a.xlsx")
    ps.process_file(str(tmp_path / "a.xlsx"), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    ws2 = load_workbook(tmp_path / "p.xlsx").active
    assert ws2["B2"].value == datetime.datetime(2026, 4, 23) and ws2["B2"].number_format == "DD.MM.YYYY"
    assert ws2["C2"].value == 17.5 and ws2["D2"].value == "=C2*2"


def test_xlsx_number_cell_gets_the_same_token_as_text(tmp_path):
    src = xlsx(tmp_path / "a.xlsx", [["Matrikelnummer"], [1234567], [1234568.0], ["1234567"]])
    ps.process_file(str(src), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    ws = load_workbook(tmp_path / "p.xlsx").active
    key = ps.derive_key(SECRET)
    assert ws["A2"].value == ws["A4"].value == ps.encrypt_value(key, "1234567")
    assert ws["A3"].value == ps.encrypt_value(key, "1234568")


def test_xlsx_date_cell_token_uses_iso_text(tmp_path):
    src = xlsx(tmp_path / "a.xlsx", [["Geburtsdatum"], [datetime.datetime(2000, 1, 31)]])
    ps.process_file(str(src), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    token = load_workbook(tmp_path / "p.xlsx").active["A2"].value
    assert ps.decrypt_value(ps.derive_key(SECRET), token) == "2000-01-31 00:00:00"


def test_xlsx_header_after_metadata_rows_and_name_per_row(tmp_path):
    src = xlsx(tmp_path / "a.xlsx", [["Prüfer", "Dr. Beispiel", None],
                                      ["Vorname", "Familienname", "Name"],
                                      ["Max", "Muster", "Muster Max"],
                                      ["Eva", "Test", "Dr. Eva Test"]])
    ps.process_file(str(src), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    ws = load_workbook(tmp_path / "p.xlsx").active
    assert [c.value for c in ws[1]] == ["Prüfer", "Dr. Beispiel", None]
    assert ws["C3"].value == f"{ws['B3'].value} {ws['A3'].value}" and TOKEN.match(ws["C4"].value)
    ps.process_file(str(tmp_path / "p.xlsx"), str(tmp_path / "r.xlsx"), SECRET, "decrypt")
    ws = load_workbook(tmp_path / "r.xlsx").active
    assert [c.value for c in ws[3]] == ["Max", "Muster", "Muster Max"]
    assert [c.value for c in ws[4]] == ["Eva", "Test", "Dr. Eva Test"]


def test_xlsx_wrong_secret_writes_no_file(tmp_path):
    src = xlsx(tmp_path / "a.xlsx", [["Vorname"], ["Max"]])
    ps.process_file(str(src), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    with pytest.raises(ps.PseudoError, match="Secret"):
        ps.process_file(str(tmp_path / "p.xlsx"), str(tmp_path / "r.xlsx"), "falsch", "decrypt")
    assert not (tmp_path / "r.xlsx").exists()


def test_xlsx_large_sheet_is_fast(tmp_path):
    """Zeilen- und Spaltenzahl duerfen nicht pro Zeile neu berechnet werden."""
    wb = Workbook(write_only=True)
    ws = wb.create_sheet()
    ws.append(["Matrikelnummer", "Vorname"] + [f"C{i}" for i in range(18)])
    for i in range(4000):
        ws.append([10000000 + i, f"Vorname{i}"] + list(range(18)))
    wb.save(tmp_path / "gross.xlsx")
    start = time.time()
    ps.process_file(str(tmp_path / "gross.xlsx"), str(tmp_path / "gross_p.xlsx"), SECRET, "encrypt")
    assert time.time() - start < 5


def test_xlsx_broken_drawing_reference_keeps_valid_drawings(tmp_path):
    """Ein Blatt verweist auf eine fehlende Zeichnung: nur dieser Verweis wird entfernt."""
    from openpyxl.chart import BarChart, Reference
    wb = Workbook()
    ws = wb.active
    ws.append(["Vorname", "Punkte"])
    ws.append(["Max", 5])
    chart = BarChart()
    chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=2), titles_from_data=True)
    ws.add_chart(chart, "D2")
    ws2 = wb.create_sheet("Zwei")
    ws2.append(["Vorname"])
    ws2.append(["Eva"])
    buf = io.BytesIO()
    wb.save(buf)
    broken = tmp_path / "defekt.xlsx"
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/drawing" Target="../drawings/drawing99.xml"/></Relationships>')
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zin, zipfile.ZipFile(broken, "w") as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("xl/worksheets/_rels/sheet2.xml.rels", rels)
    ps.process_file(str(broken), str(tmp_path / "p.xlsx"), SECRET, "encrypt")
    with zipfile.ZipFile(tmp_path / "p.xlsx") as z:
        assert any(n.startswith("xl/charts/chart") for n in z.namelist())
    wb2 = load_workbook(tmp_path / "p.xlsx")
    assert TOKEN.match(wb2["Zwei"]["A2"].value) and TOKEN.match(wb2.worksheets[0]["A2"].value)


# ---------------------------------------------------------------- Anonymisieren

def test_anonymize_csv_clears_cells_and_needs_no_secret(tmp_path):
    src = tmp_path / "a.csv"
    src.write_text('Vorname;Familienname;Name;Punkte;Kommentar\nMax;"Muster";Muster Max;5;privat\n',
                   encoding="utf-8")
    out = tmp_path / "a_anonym.csv"
    stats = ps.process_file(str(src), str(out), None, "anonymize", extra_cols=["Kommentar"])
    assert out.read_text(encoding="utf-8") == 'Vorname;Familienname;Name;Punkte;Kommentar\n;"";;5;\n'
    assert stats["cells"] == 4


def test_anonymize_xlsx_clears_cells_and_author(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Vorname", "Matrikelnummer", "Punkte"])
    ws.append(["Max", 1234567, 5])
    wb.properties.creator = "Erika Beispiel"
    wb.properties.lastModifiedBy = "Erika Beispiel"
    wb.save(tmp_path / "a.xlsx")
    ps.process_file(str(tmp_path / "a.xlsx"), str(tmp_path / "o.xlsx"), None, "anonymize")
    wb2 = load_workbook(tmp_path / "o.xlsx")
    assert [c.value for c in wb2.active[1]] == ["Vorname", "Matrikelnummer", "Punkte"]
    assert [c.value for c in wb2.active[2]] == [None, None, 5]
    with zipfile.ZipFile(tmp_path / "o.xlsx") as z:
        assert b"Erika" not in z.read("docProps/core.xml")


def test_anonymize_without_recognized_columns_is_refused(tmp_path):
    src = tmp_path / "a.csv"
    src.write_text("Fach;Punkte\nAnatomie;5\n", encoding="utf-8")
    with pytest.raises(ps.PseudoError):
        ps.process_file(str(src), str(tmp_path / "o.csv"), None, "anonymize")
    assert not (tmp_path / "o.csv").exists()


def test_output_names_for_anonymize():
    assert ps.make_output_path(Path("/d/liste.csv"), "anonymize") == "/d/liste_anonym.csv"


def test_rows_longer_than_the_header_are_reported(tmp_path, capsys):
    """Fehlerhafte Zeile (Trennzeichen im Wert ohne Anfuehrungszeichen): Spalten verrutschen.
    Das Werkzeug kann das nicht reparieren, aber es warnt."""
    stats = ps.process_file(str(write_text(tmp_path / "a.csv", "Vorname;E-Mail;Punkte\nMax;m@example.org;1\n"
                                           "Eva; jun.;e@example.org;2\n")),
                            str(tmp_path / "o.csv"), SECRET, "encrypt")
    assert any("mehr Zellen als die Kopfzeile" in w for w in stats["warnings"])
    assert "mehr Zellen als die Kopfzeile" in capsys.readouterr().out


def write_text(path, text):
    path.write_text(text, encoding="utf-8")
    return path
