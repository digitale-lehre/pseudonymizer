import sys
import zipfile
import io
from pathlib import Path

from openpyxl import Workbook, load_workbook

sys.path.insert(0, str(Path(__file__).parent.parent))
from pseudonym import process_file, make_output_path, collect_input_files, create_output_zip


def _build_xlsx_bytes(rows):
    """rows: list of lists (first row = header). Returns .xlsx bytes."""
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_xlsm(path, rows):
    """Create an .xlsm: a normal workbook + an injected dummy xl/vbaProject.bin.
    openpyxl 3.1.5 ignores the unreferenced part on load and re-merges it on
    save when keep_vba=True."""
    xlsx_bytes = _build_xlsx_bytes(rows)
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as src, \
         zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            out.writestr(item, src.read(item.filename))
        out.writestr("xl/vbaProject.bin", b"DUMMY-VBA")


def test_process_file_csv(tmp_path):
    """process_file() dispatches CSV correctly and produces encrypted output."""
    src = tmp_path / "test.csv"
    src.write_text("Vorname,Familienname\nMax,Mustermann\n", encoding="utf-8")
    dst = tmp_path / "test_pseudo.csv"
    process_file(str(src), str(dst), "geheim", "encrypt", ",")
    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert "Max" not in content
    assert "Mustermann" not in content
    assert "Vorname" in content
    assert "Familienname" in content


def test_process_file_roundtrip(tmp_path):
    """Encrypt then decrypt produces original content."""
    original = "Vorname,Familienname\nMax,Mustermann\nEva,Testerin\n"
    src = tmp_path / "data.csv"
    src.write_text(original, encoding="utf-8")
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret123", "encrypt", ",")
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret123", "decrypt", ",")
    restored = dec.read_text(encoding="utf-8")
    assert "Max" in restored
    assert "Mustermann" in restored
    assert "Eva" in restored
    assert "Testerin" in restored


def test_make_output_path_encrypt():
    assert make_output_path(Path("/d/students.csv"), "encrypt") == "/d/students_pseudo.csv"


def test_make_output_path_decrypt():
    assert make_output_path(Path("/d/data_pseudo.csv"), "decrypt") == "/d/data_pseudo_restored.csv"


def test_make_output_path_xlsx():
    assert make_output_path(Path("/d/data.xlsx"), "encrypt") == "/d/data_pseudo.xlsx"


def test_make_output_path_with_output_dir(tmp_path):
    result = make_output_path(Path("/d/students.csv"), "encrypt", str(tmp_path))
    assert result == str(tmp_path / "students_pseudo.csv")


def test_collect_input_files_plain(tmp_path):
    f1 = tmp_path / "a.csv"
    f1.write_text("Vorname\nMax\n")
    f2 = tmp_path / "b.csv"
    f2.write_text("Vorname\nEva\n")
    result = collect_input_files([str(f1), str(f2)])
    assert [Path(r) for r in result] == [f1, f2]


def test_collect_input_files_zip(tmp_path):
    csv1 = tmp_path / "data.csv"
    csv1.write_text("Vorname\nMax\n")
    txt = tmp_path / "readme.txt"
    txt.write_text("ignore me")
    zp = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(csv1, "data.csv")
        zf.write(txt, "readme.txt")
    result = collect_input_files([str(zp)])
    assert len(result) == 1
    assert result[0].name == "data.csv"


def test_collect_input_files_mixed(tmp_path):
    plain = tmp_path / "plain.csv"
    plain.write_text("Vorname\nEva\n")
    inner = tmp_path / "inner.csv"
    inner.write_text("Vorname\nMax\n")
    zp = tmp_path / "archive.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(inner, "inner.csv")
    result = collect_input_files([str(plain), str(zp)])
    assert len(result) == 2
    names = [r.name for r in result]
    assert "plain.csv" in names
    assert "inner.csv" in names


def test_create_output_zip(tmp_path):
    f1 = tmp_path / "a_pseudo.csv"
    f1.write_text("encrypted_a")
    f2 = tmp_path / "b_pseudo.csv"
    f2.write_text("encrypted_b")
    zip_path = tmp_path / "output.zip"
    create_output_zip([(str(f1), str(f1)), (str(f2), str(f2))], str(zip_path))
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert "a_pseudo.csv" in names
        assert "b_pseudo.csv" in names
        assert zf.read("a_pseudo.csv").decode() == "encrypted_a"


def test_extra_cols_encrypts_custom_column(tmp_path):
    """Extra columns are encrypted alongside auto-detected ones."""
    src = tmp_path / "data.csv"
    src.write_text("Vorname,Familienname,Kommentar\nMax,Muster,Geheim\n", encoding="utf-8")
    dst = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(dst), "secret", "encrypt", ",", extra_cols=["Kommentar"])
    content = dst.read_text(encoding="utf-8")
    assert "Max" not in content
    assert "Muster" not in content
    assert "Geheim" not in content
    assert "Vorname" in content
    assert "Kommentar" in content


def test_extra_cols_roundtrip(tmp_path):
    """Extra-col encrypt then decrypt restores original."""
    src = tmp_path / "data.csv"
    src.write_text("Vorname,Familienname,Notiz\nEva,Test,Vertraulich\n", encoding="utf-8")
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "s", "encrypt", ",", extra_cols=["Notiz"])
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "s", "decrypt", ",", extra_cols=["Notiz"])
    content = dec.read_text(encoding="utf-8")
    assert "Vertraulich" in content


def test_extra_cols_missing_column_ignored(tmp_path):
    """Extra column that doesn't exist in file is silently ignored."""
    src = tmp_path / "data.csv"
    src.write_text("Vorname,Familienname\nMax,Muster\n", encoding="utf-8")
    dst = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(dst), "secret", "encrypt", ",", extra_cols=["NichtVorhanden"])
    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert "Max" not in content


def test_extra_cols_no_duplicates(tmp_path):
    """If extra col is already auto-detected, don't encrypt twice."""
    src = tmp_path / "data.csv"
    src.write_text("Vorname,Familienname\nMax,Muster\n", encoding="utf-8")
    dst = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(dst), "secret", "encrypt", ",", extra_cols=["Vorname"])
    assert dst.exists()


def test_xlsx_name_column_standalone_encrypted(tmp_path):
    """XLSX: standalone 'Name' column (no Familienname) is encrypted + round-trips."""
    src = tmp_path / "data.xlsx"
    src.write_bytes(_build_xlsx_bytes([["Name", "Vorname"], ["Mustermann", "Max"]]))
    enc = tmp_path / "data_pseudo.xlsx"
    process_file(str(src), str(enc), "secret", "encrypt")
    ws = load_workbook(enc).active
    assert ws.cell(row=2, column=1).value != "Mustermann"  # Name encrypted
    assert ws.cell(row=2, column=2).value != "Max"          # Vorname encrypted
    dec = tmp_path / "data_restored.xlsx"
    process_file(str(enc), str(dec), "secret", "decrypt")
    ws2 = load_workbook(dec).active
    assert ws2.cell(row=2, column=1).value == "Mustermann"
    assert ws2.cell(row=2, column=2).value == "Max"


def test_xlsx_name_column_only_sheet(tmp_path):
    """XLSX: a sheet whose only recognized column is 'Name' is still processed."""
    src = tmp_path / "names.xlsx"
    src.write_bytes(_build_xlsx_bytes([["Name"], ["Mustermann"], ["Testerin"]]))
    enc = tmp_path / "names_pseudo.xlsx"
    process_file(str(src), str(enc), "secret", "encrypt")
    ws = load_workbook(enc).active
    assert ws.cell(row=2, column=1).value != "Mustermann"  # encrypted
    assert ws.cell(row=3, column=1).value != "Testerin"
    dec = tmp_path / "names_restored.xlsx"
    process_file(str(enc), str(dec), "secret", "decrypt")
    ws2 = load_workbook(dec).active
    assert ws2.cell(row=2, column=1).value == "Mustermann"  # restored
    assert ws2.cell(row=3, column=1).value == "Testerin"


def test_name_column_standalone_encrypted(tmp_path):
    """A 'Name' column without separate Vorname/Familienname is encrypted whole."""
    src = tmp_path / "data.csv"
    src.write_text("Name,Vorname\nMustermann,Max\n", encoding="utf-8")
    dst = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(dst), "secret", "encrypt", ",")
    content = dst.read_text(encoding="utf-8")
    assert "Mustermann" not in content
    assert "Max" not in content
    assert "Name" in content and "Vorname" in content


def test_name_column_standalone_roundtrip(tmp_path):
    """Standalone 'Name' column round-trips exactly."""
    src = tmp_path / "data.csv"
    src.write_text("Name,Vorname\nMustermann,Max\nTesterin,Eva\n", encoding="utf-8")
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret123", "encrypt", ",")
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret123", "decrypt", ",")
    restored = dec.read_text(encoding="utf-8")
    assert "Mustermann" in restored and "Max" in restored
    assert "Testerin" in restored and "Eva" in restored


def test_name_not_composite_fallback_encrypted(tmp_path):
    """Name present alongside Vorname+Familienname but composite check fails
    (title) -> Name is still encrypted as a whole value, round-trips exactly."""
    src = tmp_path / "data.csv"
    src.write_text(
        "Vorname,Familienname,Name\nMax,Mustermann,Dr. Max Mustermann\n",
        encoding="utf-8",
    )
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ",")
    content = enc.read_text(encoding="utf-8")
    assert "Dr. Max Mustermann" not in content
    assert "Mustermann" not in content and "Max" not in content
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ",")
    assert "Dr. Max Mustermann" in dec.read_text(encoding="utf-8")


def test_name_composite_still_recomposed(tmp_path):
    """Regression: a real composite Name is recomposed from encrypted parts
    (value contains a space), not encrypted as one token."""
    src = tmp_path / "data.csv"
    src.write_text(
        "Vorname,Familienname,Name\nMax,Mustermann,Mustermann Max\n",
        encoding="utf-8",
    )
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ",")
    name_field = enc.read_text(encoding="utf-8").splitlines()[1].split(",")[2]
    assert " " in name_field
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ",")
    assert "Mustermann Max" in dec.read_text(encoding="utf-8")


def test_name_column_only_no_other_identity(tmp_path):
    """A CSV whose only recognized column is 'Name' is still encrypted (not rejected)."""
    src = tmp_path / "names.csv"
    src.write_text("Name\nMustermann\nTesterin\n", encoding="utf-8")
    enc = tmp_path / "names_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ",")
    content = enc.read_text(encoding="utf-8")
    assert "Mustermann" not in content
    assert "Testerin" not in content
    assert "Name" in content
    dec = tmp_path / "names_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ",")
    restored = dec.read_text(encoding="utf-8")
    assert "Mustermann" in restored and "Testerin" in restored


def test_xlsx_name_not_composite_fallback(tmp_path):
    """XLSX: Name alongside Vorname+Familienname but composite check fails
    (title) -> Name still encrypted as a whole single-token value, round-trips."""
    src = tmp_path / "data.xlsx"
    src.write_bytes(_build_xlsx_bytes(
        [["Vorname", "Familienname", "Name"],
         ["Max", "Mustermann", "Dr. Max Mustermann"]]))
    enc = tmp_path / "data_pseudo.xlsx"
    process_file(str(src), str(enc), "secret", "encrypt")
    ws = load_workbook(enc).active
    name_val = ws.cell(row=2, column=3).value
    assert name_val != "Dr. Max Mustermann"   # Name encrypted
    assert " " not in name_val                 # single token, NOT recomposed
    dec = tmp_path / "data_restored.xlsx"
    process_file(str(enc), str(dec), "secret", "decrypt")
    ws2 = load_workbook(dec).active
    assert ws2.cell(row=2, column=3).value == "Dr. Max Mustermann"


def test_make_output_path_xlsm():
    assert make_output_path(Path("/d/data.xlsm"), "encrypt") == "/d/data_pseudo.xlsm"


def test_collect_input_files_xlsm_plain(tmp_path):
    x = tmp_path / "macro.xlsm"
    x.write_bytes(b"PKdummy")  # content irrelevant: collection checks suffix only
    result = collect_input_files([str(x)])
    assert len(result) == 1 and Path(result[0]).name == "macro.xlsm"


def test_collect_input_files_xlsm_in_zip(tmp_path):
    inner = tmp_path / "macro.xlsm"
    inner.write_bytes(b"PKdummy")
    zp = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(inner, "macro.xlsm")
    result = collect_input_files([str(zp)])
    assert len(result) == 1 and Path(result[0]).name == "macro.xlsm"


def test_process_file_xlsm_roundtrip(tmp_path):
    src = tmp_path / "macro.xlsm"
    _make_xlsm(src, [["Vorname", "Familienname"], ["Max", "Mustermann"]])
    enc = tmp_path / "macro_pseudo.xlsm"
    process_file(str(src), str(enc), "secret123", "encrypt")
    assert enc.exists()
    ws = load_workbook(enc).active
    assert ws.cell(row=2, column=1).value != "Max"  # encrypted
    dec = tmp_path / "macro_restored.xlsm"
    process_file(str(enc), str(dec), "secret123", "decrypt")
    ws2 = load_workbook(dec).active
    assert ws2.cell(row=2, column=1).value == "Max"
    assert ws2.cell(row=2, column=2).value == "Mustermann"


def test_process_file_xlsm_preserves_vba(tmp_path):
    src = tmp_path / "macro.xlsm"
    _make_xlsm(src, [["Vorname", "Familienname"], ["Max", "Mustermann"]])
    with zipfile.ZipFile(src) as z:
        assert "xl/vbaProject.bin" in z.namelist()
    enc = tmp_path / "macro_pseudo.xlsm"
    process_file(str(src), str(enc), "secret123", "encrypt")
    with zipfile.ZipFile(enc) as z:
        assert "xl/vbaProject.bin" in z.namelist()
        assert z.read("xl/vbaProject.bin") == b"DUMMY-VBA"


def test_matnr_dot_alias_variants_recognized():
    """'Mat.Nr.'-Varianten werden als matnr erkannt (case-insensitive,
    mit/ohne Schlusspunkt, Bindestrich- und Leerzeichen-Schreibweise)."""
    from pseudonym import find_identity_cols
    for header in ["Mat.nr.", "Mat.Nr.", "MAT.NR.", "Mat.Nr", "Mat-Nr.", "Mat-Nr", "Mat. Nr."]:
        found = find_identity_cols([header])
        assert found.get("matnr") == header, f"{header!r} nicht als matnr erkannt: {found}"


def test_matnr_dot_alias_encrypted_roundtrip(tmp_path):
    """CSV mit 'Mat.nr.'-Spalte wird verschluesselt und exakt wiederhergestellt."""
    src = tmp_path / "data.csv"
    src.write_text("Mat.nr.,Vorname\n01634795,Max\n", encoding="utf-8")
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ",")
    content = enc.read_text(encoding="utf-8")
    assert "01634795" not in content
    assert "Mat.nr." in content  # Header bleibt
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ",")
    assert "01634795" in dec.read_text(encoding="utf-8")


def test_detect_file_encoding_cp1252_without_bom():
    """BOM-lose Dateien, die kein gueltiges UTF-8 sind, werden als Windows-1252 erkannt
    (ANSI-Exporte aus MedCampus/Excel)."""
    from pseudonym import detect_file_encoding
    assert detect_file_encoding("Universit\u00e4tsleitung".encode("cp1252")) == ("cp1252", 0)
    assert detect_file_encoding("Universit\u00e4tsleitung".encode("utf-8")) == ("utf-8", 0)
    assert detect_file_encoding(b"plain ascii") == ("utf-8", 0)


def test_cp1252_csv_roundtrip_byte_identical(tmp_path):
    """Windows-1252-CSV: Umlaute werden korrekt verschluesselt und byte-identisch
    wiederhergestellt; nicht verschluesselte Spalten bleiben in Windows-1252."""
    original = (
        '"Familienname";"Vorname";"Einrichtung"\r\n'
        '"M\u00fcller";"J\u00fcrgen";"B\u00fcro der Betriebsr\u00e4te \u20ac"\r\n'
    ).encode("cp1252")
    src = tmp_path / "ansi.csv"
    src.write_bytes(original)
    enc = tmp_path / "ansi_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ";")
    enc_text = enc.read_bytes().decode("cp1252")
    assert "M\u00fcller" not in enc_text
    assert "B\u00fcro der Betriebsr\u00e4te \u20ac" in enc_text
    dec = tmp_path / "ansi_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ";")
    assert dec.read_bytes() == original


def test_cp1252_tokens_match_utf8_tokens(tmp_path):
    """Gleicher Name ergibt denselben Token, egal ob die Quelldatei UTF-8 oder
    Windows-1252 kodiert ist."""
    text = "Familienname;Ort\nM\u00fcller;Gm\u00fcnd\n"
    for enc_name in ("utf-8", "cp1252"):
        (tmp_path / f"{enc_name}.csv").write_bytes(text.encode(enc_name))
        process_file(str(tmp_path / f"{enc_name}.csv"), str(tmp_path / f"{enc_name}_p.csv"),
                     "secret", "encrypt", ";")
    tok_utf8 = (tmp_path / "utf-8_p.csv").read_bytes().decode("utf-8").splitlines()[1].split(";")[0]
    tok_ansi = (tmp_path / "cp1252_p.csv").read_bytes().decode("cp1252").splitlines()[1].split(";")[0]
    assert tok_utf8 == tok_ansi


def test_cp1252_undefined_bytes_roundtrip(tmp_path):
    """In Windows-1252 undefinierte Bytes (0x81, 0x8D, 0x8F, 0x90, 0x9D) werden wie im
    Browser (WHATWG) auf C1-Zeichen abgebildet und unveraendert zurueckgeschrieben."""
    original = b"Familienname;Notiz\nM\xfcller;x\x81\x8d\x8f\x90\x9dy\n"
    src = tmp_path / "odd.csv"
    src.write_bytes(original)
    enc = tmp_path / "odd_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ";")
    dec = tmp_path / "odd_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ";")
    assert dec.read_bytes() == original


def test_csv_without_trailing_newline_roundtrip(tmp_path):
    """Fehlender Zeilenumbruch am Dateiende bleibt erhalten (byte-identisch)."""
    original = b'"Familienname";"Vorname"\r\n"Muster";"Max"\r\n"Test";"Eva"'
    src = tmp_path / "noeol.csv"
    src.write_bytes(original)
    enc = tmp_path / "noeol_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ";")
    assert not enc.read_bytes().endswith(b"\n")
    dec = tmp_path / "noeol_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ";")
    assert dec.read_bytes() == original


def test_ascii_input_with_non_ascii_output_gets_utf8_bom(tmp_path):
    """Reine ASCII-Eingabe (Kodierung unbestimmbar), Ausgabe mit Umlauten:
    UTF-8 mit BOM, damit Excel die Umlaute korrekt anzeigt."""
    for src_enc in ("cp1252", "utf-8"):
        src = tmp_path / f"{src_enc}.csv"
        src.write_bytes("Familienname;Vorname\nMüller;Jürgen\n".encode(src_enc))
        enc = tmp_path / f"{src_enc}_pseudo.csv"
        process_file(str(src), str(enc), "secret", "encrypt", ";")
        assert enc.read_bytes().isascii()
        dec = tmp_path / f"{src_enc}_restored.csv"
        process_file(str(enc), str(dec), "secret", "decrypt", ";")
        assert dec.read_bytes() == b"\xef\xbb\xbf" + "Familienname;Vorname\nMüller;Jürgen\n".encode("utf-8")


def test_ascii_roundtrip_stays_without_bom(tmp_path):
    """Ohne Umlaute bleibt eine ASCII-Datei ohne BOM (byte-identisch)."""
    original = b"Familienname;Vorname\nMuster;Max\n"
    src = tmp_path / "ascii.csv"
    src.write_bytes(original)
    enc = tmp_path / "ascii_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ";")
    dec = tmp_path / "ascii_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ";")
    assert dec.read_bytes() == original


def test_make_zip_name_common_prefix():
    """ZIP-Name aus gemeinsamem Dateinamen-Anfang (an Trennzeichen gekuerzt)."""
    from datetime import date
    from pseudonym import make_zip_name
    files = [
        "/x/Teilnehmerliste_LV101_2026W01.csv",
        "/x/Teilnehmerliste_LV101_2026S02.csv",
    ]
    today = date.today().isoformat()
    assert make_zip_name(files, "encrypt") == f"Teilnehmerliste_LV101_pseudo_2Dateien_{today}.zip"
    assert make_zip_name(["/x/Liste_A.csv", "/x/Liste_B.xlsx"], "decrypt") == \
        f"Liste_restored_2Dateien_{today}.zip"
    assert make_zip_name(["/x/alpha.csv", "/x/beta.csv"], "encrypt") == \
        f"Batch_pseudo_2Dateien_{today}.zip"


def test_make_zip_name_from_source_zip(tmp_path):
    """Alle Dateien aus einem ZIP: <ZIP-Name>_pseudo.zip."""
    from pseudonym import make_zip_name
    zp = tmp_path / "Export Okt.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.csv", "Vorname\nMax\n")
        zf.writestr("b.csv", "Vorname\nEva\n")
    files = collect_input_files([str(zp)])
    assert make_zip_name(files, "encrypt") == "Export Okt_pseudo.zip"


def test_cli_zip_input_writes_results_next_to_zip(tmp_path):
    """Ergebnisse aus einem ZIP-Eingang landen neben dem ZIP, nicht im
    (anschliessend geloeschten) Temp-Verzeichnis."""
    import subprocess
    zp = tmp_path / "Export.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("a.csv", "Vorname\nMax\n")
        zf.writestr("b.csv", "Vorname\nEva\n")
    script = Path(__file__).parent.parent / "pseudonym.py"
    subprocess.run([sys.executable, str(script), "encrypt", str(zp), "--secret", "s", "--zip"],
                   check=True, capture_output=True)
    assert (tmp_path / "a_pseudo.csv").exists()
    assert (tmp_path / "b_pseudo.csv").exists()
    with zipfile.ZipFile(tmp_path / "Export_pseudo.zip") as z:
        assert sorted(z.namelist()) == ["a_pseudo.csv", "b_pseudo.csv"]
