#!/usr/bin/env python3
"""
Pseudonymisierung & De-Pseudonymisierung mit nur einem Secret.
Keine separate Key-Datei noetig. Unterstuetzt CSV und XLSX.

Verwendet AES-Verschluesselung (deterministisch): gleicher Secret + gleiche Daten
= gleiches Pseudonym. Nur wer den Secret kennt, kann zurueckfuehren.

Verwendung:
    # CSV pseudonymisieren
    python pseudonym.py encrypt eingabe.csv --secret "MeinGeheimnis"

    # XLSX pseudonymisieren
    python pseudonym.py encrypt eingabe.xlsx --secret "MeinGeheimnis"

    # De-Pseudonymisieren (selber Secret)
    python pseudonym.py decrypt eingabe_pseudo.xlsx --secret "MeinGeheimnis"

    # Mit Semikolon-CSV
    python pseudonym.py encrypt eingabe.csv --secret "MeinGeheimnis" --sep ";"
"""

import argparse
import base64
import csv
import hashlib
import hmac
import io
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

__version__ = "0.2.0"

# Spaltennamen-Mapping: verschiedene Schreibweisen -> kanonischer Schluessel
# Jeder kanonische Schluessel hat eine Liste von moeglichen Spaltennamen
COLUMN_ALIASES = {
    "familienname": ["FAMILIENNAME", "Familienname", "familienname", "Zuname", "zuname",
                     "ZUNAME", "Nachname", "nachname", "NACHNAME", "Last Name", "LastName",
                     "FAMILY_NAME_OF_STUDENT", "Family_Name_of_Student",
                     "Familienname oder Nachname"],
    "vorname":      ["VORNAME", "Vorname", "vorname", "First Name", "FirstName", "Firstname",
                     "FIRST_NAME_OF_STUDENT", "First_Name_of_Student"],
    "matnr":        ["MATRIKELNUMMER", "Matrikelnummer", "matrikelnummer", "Matnr", "matnr",
                     "MATNR", "MatrNr", "Matrikel", "matrikel", "MATRIKEL",
                     "StudentID", "Student_ID",
                     "REGISTRATION_NUMBER", "Registration_Number", "Registration Number"],
    "email":        ["EMAIL_ADDRESS", "Email_Address", "E-Mail", "E-MAIL", "e-mail",
                     "Email", "email", "EMAIL", "Mail", "MAIL", "mail",
                     "E_MAIL", "EmailAddress", "email_address",
                     "E-Mail des Teilnehmers", "Attendee Email"],
    "pruefer":      ["Examiner", "EXAMINER", "examiner", "Prüfer", "PRÜFER", "prüfer",
                     "Pruefer", "PRUEFER", "pruefer", "Prufer", "PRUFER"],
    "anzeigename":  ["Anzeigename", "ANZEIGENAME", "anzeigename",
                     "Display Name", "DisplayName", "DISPLAY NAME", "display name"],
}
NAME_ALIASES = ["NAME", "Name", "name"]


def derive_key(secret: str) -> bytes:
    """Leitet einen 256-Bit AES-Key aus dem Secret ab (PBKDF2, 100k Runden)."""
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), b"MedUniWien-Pseudo-Salt", 100_000)


def deterministic_iv(key: bytes, plaintext: str) -> bytes:
    """Erzeugt einen deterministischen IV aus Key + Klartext (HMAC, 16 Bytes)."""
    return hmac.new(key, plaintext.encode("utf-8"), hashlib.sha256).digest()[:16]


def encrypt_value(key: bytes, plaintext: str) -> str:
    """Verschluesselt einen String -> URL-sicherer Base64-String."""
    if not plaintext:
        return plaintext
    iv = deterministic_iv(key, plaintext)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
    raw = iv + ct
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decrypt_value(key: bytes, token: str) -> str:
    """Entschluesselt einen Base64-Token -> Klartext-String."""
    if not token:
        return token
    pad_len = 4 - len(token) % 4
    if pad_len < 4:
        token += "=" * pad_len
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
    except Exception:
        return token
    if len(raw) < 32:
        return token
    iv = raw[:16]
    ct = raw[16:]
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded) + unpadder.finalize()
        return plaintext.decode("utf-8")
    except Exception:
        return token


def find_identity_cols(headers: list) -> dict:
    """Findet Identitaetsspalten anhand verschiedener Namenskonventionen (case-insensitive).
    Gibt dict zurueck: {kanonischer_key: tatsaechlicher_spaltenname}"""
    found = {}
    # Baue case-insensitive Lookup: lower(header) -> header
    header_lower = {h.strip().lower(): h for h in headers if h}
    for canon_key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in header_lower:
                found[canon_key] = header_lower[alias.lower()]
                break
    return found


def find_name_col(headers: list) -> str:
    """Findet die NAME-Spalte (falls vorhanden, case-insensitive)."""
    header_lower = {h.strip().lower(): h for h in headers if h}
    for alias in NAME_ALIASES:
        if alias.lower() in header_lower:
            return header_lower[alias.lower()]
    return None


def find_header_row(rows, max_scan=20):
    """Findet die Header-Zeile in einer Liste von Zeilen (als Listen).
    Scannt bis zu max_scan Zeilen nach bekannten Identitaetsspalten.
    Gibt den Index zurueck (0-basiert). Fallback: 0 (erste Zeile)."""
    for i, row in enumerate(rows[:max_scan]):
        # row is a list of cell values (strings)
        headers = [str(c).strip() if c is not None else "" for c in row]
        if find_identity_cols(headers):
            return i
    return 0


# ======================== CSV ========================

def detect_file_encoding(raw: bytes) -> tuple:
    """Erkennt Encoding und BOM-Laenge aus rohen Bytes.
    Unterstuetzt UTF-8 (mit/ohne BOM), UTF-16 LE und UTF-16 BE.
    Gibt (encoding, bom_length) zurueck."""
    if len(raw) >= 2 and raw[:2] == b"\xff\xfe":
        return "utf-16-le", 2
    if len(raw) >= 2 and raw[:2] == b"\xfe\xff":
        return "utf-16-be", 2
    if len(raw) >= 3 and raw[:3] == b"\xef\xbb\xbf":
        return "utf-8", 3
    return "utf-8", 0


def process_csv(input_path: str, output_path: str, secret: str, mode: str, sep: str = ","):
    key = derive_key(secret)
    transform = encrypt_value if mode == "encrypt" else decrypt_value

    # Datei als Bytes lesen und Encoding erkennen (UTF-8, UTF-16 LE/BE)
    with open(input_path, "rb") as f:
        raw = f.read()

    encoding, bom_len = detect_file_encoding(raw)
    text = raw[bom_len:].decode(encoding)
    has_crlf = "\r\n" in text

    # Alle Zeilen als Listen parsen, um Header-Zeile zu finden
    reader_raw = csv.reader(io.StringIO(text), delimiter=sep)
    all_rows = list(reader_raw)

    if not all_rows:
        print("FEHLER: Datei ist leer.", file=sys.stderr)
        sys.exit(1)

    # Header-Zeile finden (kann nach Metadaten-Zeilen liegen, z.B. MLW-Export)
    header_idx = find_header_row(all_rows)
    fieldnames = all_rows[header_idx]
    data_rows_raw = all_rows[header_idx + 1:]

    line_terminator = "\r\n" if has_crlf else "\n"

    # Rohtext-Zeilen fuer Metadaten-Bewahrung und Quoting-Erkennung
    # (Einfache Zeilen ohne Newlines in Quotes — MLW-Metadaten sind sicher)
    raw_lines = text.split("\r\n") if has_crlf else text.split("\n")

    # Rohe Metadaten-Zeilen als Text bewahren (fuer byte-identische Ausgabe)
    meta_raw_text = ""
    if header_idx > 0:
        meta_raw_text = line_terminator.join(raw_lines[:header_idx]) + line_terminator

    # Quoting anhand der Header-Zeile erkennen (nicht erste Datei-Zeile!)
    header_line_raw = raw_lines[header_idx].strip() if header_idx < len(raw_lines) else ""
    quoting = csv.QUOTE_ALL if header_line_raw.startswith('"') else csv.QUOTE_MINIMAL

    # Konvertiere zu Dicts (wie DictReader)
    rows = []
    for raw_row in data_rows_raw:
        d = {}
        for i, h in enumerate(fieldnames):
            d[h] = raw_row[i] if i < len(raw_row) else ""
        rows.append(d)

    if not fieldnames:
        print("FEHLER: Konnte keine Spalten erkennen.", file=sys.stderr)
        sys.exit(1)

    id_cols = find_identity_cols(fieldnames)
    name_col = find_name_col(fieldnames)
    if not id_cols:
        print(f"FEHLER: Keine Identitaetsspalten gefunden.", file=sys.stderr)
        print(f"Vorhandene Spalten: {fieldnames}", file=sys.stderr)
        sys.exit(1)

    # NAME composite check (erkennt auch Reihenfolge: "Fam Vor" vs "Vor Fam")
    name_is_composite = False
    name_order = "fam_vor"
    fam_col = id_cols.get("familienname")
    vor_col = id_cols.get("vorname")
    if name_col and fam_col and vor_col and rows:
        sample = rows[0]
        name_val = (sample.get(name_col) or "").strip()
        fam_val = (sample.get(fam_col) or "").strip()
        vor_val = (sample.get(vor_col) or "").strip()
        if name_val == f"{fam_val} {vor_val}".strip():
            name_is_composite = True
            name_order = "fam_vor"
        elif name_val == f"{vor_val} {fam_val}".strip():
            name_is_composite = True
            name_order = "vor_fam"

    # Ergebnis in StringIO schreiben, dann mit Original-Encoding ausgeben
    str_out = io.StringIO()

    # Metadaten-Zeilen als Rohtext ausgeben (byte-identisch, nicht re-serialisiert)
    if meta_raw_text:
        str_out.write(meta_raw_text)

    # Header + Daten mit DictWriter
    dict_writer = csv.DictWriter(
        str_out, fieldnames=fieldnames, delimiter=sep,
        quoting=quoting, lineterminator=line_terminator
    )
    dict_writer.writeheader()
    for row in rows:
        new_row = dict(row)
        for canon_key, actual_col in id_cols.items():
            val = (row.get(actual_col) or "").strip()
            if val:
                new_row[actual_col] = transform(key, val)
        if name_col and name_is_composite:
            fam = new_row.get(fam_col, "")
            vor = new_row.get(vor_col, "")
            if name_order == "vor_fam":
                new_row[name_col] = f"{vor} {fam}".strip()
            else:
                new_row[name_col] = f"{fam} {vor}".strip()
        dict_writer.writerow(new_row)

    output_text = str_out.getvalue()
    with open(output_path, "wb") as f:
        if bom_len > 0:
            f.write(raw[:bom_len])
        f.write(output_text.encode(encoding))

    cols_info = ", ".join(f"{v}" for v in id_cols.values())
    if name_col and name_is_composite:
        cols_info += f" + {name_col}"
    action = "Pseudonymisierung" if mode == "encrypt" else "De-Pseudonymisierung"
    print(f"{action} abgeschlossen.")
    print(f"  Eingabe:    {input_path} ({len(rows)} Zeilen)")
    print(f"  Ausgabe:    {output_path}")
    print(f"  Spalten:    {cols_info}")
    print(f"  Encoding:   {encoding.upper()}{' (BOM)' if bom_len > 0 else ''}")
    if header_idx > 0:
        print(f"  Metadaten:  {header_idx} Zeile(n) vor Header (unveraendert)")
    print(f"  Verfahren:  AES-256-CBC (deterministisch, PBKDF2)")
    if mode == "encrypt":
        print(f"\n  Zum Zurueckfuehren:")
        print(f"  python pseudonym.py decrypt {output_path} --secret <IhrSecret>")


# ======================== XLSX ========================

def _fix_xlsx_drawings(input_path: str) -> str:
    """Repariert XLSX-Dateien mit fehlenden Drawing-Referenzen.
    Gibt Pfad zur (ggf. reparierten) Datei zurueck."""
    import zipfile
    import tempfile
    import os
    import re

    with zipfile.ZipFile(input_path, "r") as zf:
        names = zf.namelist()
        # Pruefe ob es Sheet-Rels gibt, die auf fehlende Drawings verweisen
        broken = False
        for name in names:
            if name.startswith("xl/worksheets/_rels/") and name.endswith(".rels"):
                content = zf.read(name).decode("utf-8")
                # Finde alle Drawing-Referenzen
                for m in re.finditer(r'Target="([^"]*drawing[^"]*)"', content):
                    target = m.group(1)
                    # Pfad relativ zu xl/worksheets/ aufloesen
                    if target.startswith("../"):
                        full_path = "xl/" + target[3:]
                    elif target.startswith("/"):
                        full_path = target.lstrip("/")
                    else:
                        full_path = "xl/worksheets/" + target
                    # Normalisiere Pfad
                    full_path = os.path.normpath(full_path).replace("\\", "/")
                    if full_path not in names:
                        broken = True
                        break
            if broken:
                break

        if not broken:
            return input_path

        # Reparatur: Drawing-Relationships aus Sheet-Rels entfernen
        print("  HINWEIS: Repariere fehlende Drawing-Referenzen in XLSX...")
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
        os.close(tmp_fd)

        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zf.infolist():
                data = zf.read(item.filename)
                if item.filename.startswith("xl/worksheets/_rels/") and item.filename.endswith(".rels"):
                    content = data.decode("utf-8")
                    # Entferne Relationships mit Type=drawing, deren Target fehlt
                    cleaned = re.sub(
                        r'<Relationship[^>]*Type="[^"]*drawing[^"]*"[^>]*/>\s*',
                        '', content
                    )
                    data = cleaned.encode("utf-8")
                zout.writestr(item, data)

        return tmp_path


def process_xlsx(input_path: str, output_path: str, secret: str, mode: str):
    from openpyxl import load_workbook
    from copy import copy

    key = derive_key(secret)
    transform = encrypt_value if mode == "encrypt" else decrypt_value

    # Repariere fehlende Drawings falls noetig
    fixed_path = _fix_xlsx_drawings(input_path)
    try:
        wb = load_workbook(fixed_path)
    finally:
        if fixed_path != input_path:
            import os
            os.unlink(fixed_path)
    total_cells = 0
    sheets_processed = []
    sheets_skipped = []

    for ws in wb.worksheets:
        # Leere Sheets ueberspringen
        if ws.max_row is None or ws.max_row < 1:
            sheets_skipped.append(f"{ws.title} (leer)")
            continue

        # Alle Zeilen als Listen lesen, dann Header-Zeile finden
        all_rows = []
        for row_idx in range(1, (ws.max_row or 0) + 1):
            row_vals = []
            for col_idx in range(1, (ws.max_column or 0) + 1):
                val = ws.cell(row=row_idx, column=col_idx).value
                row_vals.append(str(val).strip() if val is not None else "")
            all_rows.append(row_vals)

        header_offset = find_header_row(all_rows)
        headers = all_rows[header_offset] if all_rows else []
        # header_row in openpyxl is 1-based: header_offset + 1
        header_row_num = header_offset + 1

        id_cols = find_identity_cols(headers)
        if not id_cols:
            # Warnung ausgeben, aber nicht abbrechen
            sheets_skipped.append(f"{ws.title} (keine Identitaetsspalten erkannt: {[h for h in headers if h]})")
            continue

        data_start_row = header_row_num + 1
        if ws.max_row < data_start_row:
            sheets_skipped.append(f"{ws.title} (nur Header, keine Daten)")
            continue

        name_col_name = find_name_col(headers)

        # Spaltenindizes ermitteln (1-basiert fuer openpyxl)
        col_indices = {}  # canon_key -> col_index (1-basiert)
        for canon_key, actual_name in id_cols.items():
            col_indices[canon_key] = headers.index(actual_name) + 1

        name_col_idx = None
        if name_col_name and name_col_name in headers:
            name_col_idx = headers.index(name_col_name) + 1

        # NAME composite check (anhand erster Datenzeile, erkennt Reihenfolge)
        name_is_composite = False
        name_order = "fam_vor"
        fam_idx = col_indices.get("familienname")
        vor_idx = col_indices.get("vorname")
        if name_col_idx and fam_idx and vor_idx and ws.max_row >= data_start_row:
            name_val = str(ws.cell(row=data_start_row, column=name_col_idx).value or "").strip()
            fam_val = str(ws.cell(row=data_start_row, column=fam_idx).value or "").strip()
            vor_val = str(ws.cell(row=data_start_row, column=vor_idx).value or "").strip()
            if name_val == f"{fam_val} {vor_val}".strip():
                name_is_composite = True
                name_order = "fam_vor"
            elif name_val == f"{vor_val} {fam_val}".strip():
                name_is_composite = True
                name_order = "vor_fam"

        sheet_count = 0
        for row_idx in range(data_start_row, ws.max_row + 1):
            for canon_key, ci in col_indices.items():
                cell = ws.cell(row=row_idx, column=ci)
                val = cell.value
                if val is not None:
                    val_str = str(val).strip()
                    if val_str:
                        cell.value = transform(key, val_str)
                        sheet_count += 1

            # NAME-Spalte aktualisieren (Original-Reihenfolge beibehalten)
            if name_col_idx and name_is_composite and fam_idx and vor_idx:
                fam_new = str(ws.cell(row=row_idx, column=fam_idx).value or "").strip()
                vor_new = str(ws.cell(row=row_idx, column=vor_idx).value or "").strip()
                if name_order == "vor_fam":
                    ws.cell(row=row_idx, column=name_col_idx).value = f"{vor_new} {fam_new}".strip()
                else:
                    ws.cell(row=row_idx, column=name_col_idx).value = f"{fam_new} {vor_new}".strip()

        total_cells += sheet_count
        cols_info = ", ".join(id_cols.values())
        if name_is_composite and name_col_name:
            cols_info += f" + {name_col_name}"
        sheets_processed.append(f"{ws.title} ({cols_info}: {sheet_count} Zellen)")
        if header_row_num > 1:
            print(f"    (Header in Zeile {header_row_num}, {header_row_num - 1} Metadaten-Zeile(n) uebersprungen)")

    wb.save(output_path)

    action = "Pseudonymisierung" if mode == "encrypt" else "De-Pseudonymisierung"
    print(f"{action} abgeschlossen.")
    print(f"  Eingabe:    {input_path}")
    print(f"  Ausgabe:    {output_path}")
    print(f"  Verfahren:  AES-256-CBC (deterministisch, PBKDF2)")
    print(f"  Sheets:     {len(sheets_processed)} verarbeitet, {total_cells} Zellen")
    for s in sheets_processed:
        print(f"    + {s}")
    if sheets_skipped:
        print(f"  Uebersprungen: {len(sheets_skipped)}")
        for s in sheets_skipped:
            print(f"    - {s}")
    if not sheets_processed:
        print("  WARNUNG: Kein Sheet mit erkennbaren Identitaetsspalten gefunden!")
        print("  Erkannte Spaltennamen: FAMILIENNAME/Familienname/Zuname/Nachname,")
        print("    VORNAME/Vorname, MATRIKELNUMMER/Matrikelnummer/Matnr (case-insensitive)")
    if mode == "encrypt":
        print(f"\n  Zum Zurueckfuehren:")
        print(f"  python pseudonym.py decrypt {output_path} --secret <IhrSecret>")


# ======================== MAIN ========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CSV/XLSX pseudonymisieren/de-pseudonymisieren — nur mit Secret, ohne Key-Datei"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("mode", choices=["encrypt", "decrypt"],
                        help="encrypt = pseudonymisieren, decrypt = zurueckfuehren")
    parser.add_argument("input", help="Pfad zur CSV- oder XLSX-Datei")
    parser.add_argument("--secret", required=True, help="Ihr geheimer Schluessel")
    parser.add_argument("--output", "-o",
                        help="Ausgabepfad (Standard: <name>_pseudo.<ext> bzw. <name>_restored.<ext>)")
    parser.add_argument("--sep", "-s", default=",",
                        help="CSV-Trennzeichen (Standard: Komma, wird bei XLSX ignoriert)")
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"FEHLER: Datei nicht gefunden: {inp}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out = args.output
    elif args.mode == "encrypt":
        out = str(inp.with_name(f"{inp.stem}_pseudo{inp.suffix}"))
    else:
        out = str(inp.with_name(f"{inp.stem}_restored{inp.suffix}"))

    ext = inp.suffix.lower()
    if ext == ".xlsx":
        process_xlsx(args.input, out, args.secret, args.mode)
    elif ext in (".csv", ".tsv", ".txt"):
        process_csv(args.input, out, args.secret, args.mode, args.sep)
    else:
        print(f"FEHLER: Unbekanntes Dateiformat '{ext}'. Unterstuetzt: .csv, .xlsx", file=sys.stderr)
        sys.exit(1)
