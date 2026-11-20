#!/usr/bin/env python3
"""
Pseudonymisierung, De-Pseudonymisierung und Anonymisierung mit nur einem Secret.
Keine separate Key-Datei noetig. Unterstuetzt CSV, TSV, XLSX und XLSM.

Verwendet AES-Verschluesselung (deterministisch): gleicher Secret + gleiche Daten
= gleiches Pseudonym. Nur wer den Secret kennt, kann zurueckfuehren.

Verwendung:
    # Pseudonymisieren (das Secret wird verdeckt abgefragt)
    python pseudonym.py encrypt eingabe.csv

    # Zurueckfuehren (selbes Secret)
    python pseudonym.py decrypt eingabe_pseudo.csv

    # Anonymisieren: Identitaetsspalten endgueltig leeren (kein Secret noetig)
    python pseudonym.py anonymize eingabe.xlsx

    # Mehrere Dateien, Ordner, Platzhalter oder ZIP
    python pseudonym.py encrypt ordner/ "*.csv" archiv.zip --zip
"""

import argparse
import base64
import codecs
import hashlib
import hmac
import os
import re
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as sym_padding
except ImportError:  # kein Abbruch mit Traceback: missing_packages() meldet das Paket verstaendlich
    Cipher = algorithms = modes = sym_padding = None

__version__ = "0.7.0"


class PseudoError(Exception):
    """Fehler mit einer Meldung, die Anwender:innen ohne Technikwissen verstehen."""


def missing_packages(crypto: bool = True, excel: bool = True) -> list:
    """Namen der benoetigten Python-Pakete, die fehlen oder sich nicht laden lassen."""
    missing = []
    if crypto and Cipher is None:
        missing.append("cryptography")
    if excel:
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            missing.append("openpyxl")
    return missing


def package_hint(names) -> str:
    """Meldung zu fehlenden Paketen. Der Befehl nennt genau das Python, das gerade laeuft:
    Sind mehrere Python-Versionen installiert, landet das Paket sonst in der falschen."""
    python = sys.executable or "python"
    if " " in python:
        python = f'"{python}"'
    quoted = " und ".join(f"'{n}'" for n in names)
    verb = "fehlen oder lassen" if len(names) > 1 else "fehlt oder laesst"
    subject = "Python-Pakete" if len(names) > 1 else "Python-Paket"
    return (f"{subject} {quoted} {verb} sich nicht laden. "
            "Bitte einmal installieren und den Befehl danach wiederholen:\n"
            f"  {python} -m pip install cryptography openpyxl")


# Spaltennamen-Mapping: kanonischer Schluessel -> moegliche Spaltennamen.
# Der Vergleich ignoriert Gross-/Kleinschreibung, daher steht jede Schreibweise nur einmal hier.
# MUSS mit COLUMN_ALIASES in pseudonym_gui.html uebereinstimmen (tests/test_consistency.py).
COLUMN_ALIASES = {
    "familienname": ["Familienname", "Zuname", "Nachname", "Last Name", "LastName", "Surname",
                     "Family Name", "Family_Name", "FAMILY_NAME_OF_STUDENT",
                     "Familienname oder Nachname", "Familien- oder Nachname"],
    "vorname":      ["Vorname", "First Name", "FirstName", "Given Name", "GivenName", "Rufname",
                     "FIRST_NAME_OF_STUDENT"],
    "matnr":        ["Matrikelnummer", "Matnr", "MatrNr", "Matrikel", "Matrikelnr", "Matrikelnr.",
                     "Mat.Nr.", "Mat.Nr", "Mat-Nr.", "Mat-Nr", "Mat. Nr.",
                     "StudentID", "Student_ID", "Student ID",
                     "REGISTRATION_NUMBER", "Registration Number",
                     "ID number", "ID-Nummer", "Kennnummer"],
    "email":        ["EMAIL_ADDRESS", "E-Mail", "Email", "Mail", "E_MAIL", "EmailAddress",
                     "E-Mail-Adresse", "E-Mail Adresse", "Emailadresse", "Mailadresse",
                     "Email address", "E-Mail des Teilnehmers", "Attendee Email"],
    "pruefer":      ["Examiner", "Prüfer", "Pruefer", "Prufer", "Prüfer/in", "PrüferIn", "Prüfer:in"],
    "anzeigename":  ["Anzeigename", "Display Name", "DisplayName", "Full Name", "FullName",
                     "Student Name"],
    "svnr":         ["Sozialversicherungsnummer", "SVNr", "SV-Nr", "SV-Nr.", "SV-Nummer", "SV Nummer",
                     "Versicherungsnummer", "Social Security Number", "SSN"],
    "geburtsdatum": ["Geburtsdatum", "Geburtstag", "Geb.Datum", "Geb.-Datum", "GebDatum", "Geb. Datum",
                     "Birthday", "Date of Birth", "DateOfBirth", "DOB", "Birth Date", "BirthDate"],
    "telefon":      ["Telefon", "Telefonnummer", "Tel", "Tel.", "Tel.Nr.", "TelNr",
                     "Phone", "Phone Number", "PhoneNumber",
                     "Handy", "Handynummer", "Mobilnummer", "Mobile", "Mobiltelefon",
                     "Cell", "Cell Phone"],
    # Valuatic Pruefungssoftware: eigene Keys, da examiner + candidate
    # in derselben Datei vorkommen und unabhaengig verschluesselt werden muessen
    "examiner_id":        ["examiner_id"],
    "examiner_nachname":  ["examiner_last_name"],
    "examiner_vorname":   ["examiner_first_name"],
    "candidate_id":       ["candidate_id"],
    "candidate_nachname": ["candidate_last_name"],
    "candidate_vorname":  ["candidate_first_name"],
}
NAME_ALIASES = ["Name"]

_ALIAS_LOOKUP = {a.lower(): key for key, aliases in COLUMN_ALIASES.items() for a in aliases}
_NAME_LOOKUP = {a.lower() for a in NAME_ALIASES}

MODES = {
    # Modus: (Dateinamen-Zusatz, Bezeichnung in Meldungen)
    "encrypt":   ("_pseudo", "Pseudonymisierung"),
    "decrypt":   ("_restored", "De-Pseudonymisierung"),
    "anonymize": ("_anonym", "Anonymisierung"),
}


# ======================== KRYPTOGRAFIE ========================

def derive_key(secret: str) -> bytes:
    """Leitet einen 256-Bit AES-Key aus dem Secret ab (PBKDF2, 100k Runden)."""
    if Cipher is None:  # ohne das Paket gaebe es spaeter nur "kein gueltiges Pseudonym"
        raise PseudoError(package_hint(["cryptography"]))
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
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = encryptor.update(padded) + encryptor.finalize()
    return base64.urlsafe_b64encode(iv + ct).rstrip(b"=").decode("ascii")


_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43,}$")


def try_decrypt(key: bytes, token: str):
    """Entschluesselt ein Pseudonym. Gibt None zurueck, wenn token kein Pseudonym
    fuer diesen Key ist (Klartext, beschaedigter Wert oder falsches Secret).

    Die Pruefung ist exakt: Der IV im Pseudonym muss HMAC(key, Klartext)[:16] sein."""
    if not token or not _TOKEN_RE.match(token) or len(token) % 4 == 1:
        return None
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except Exception:
        return None
    if len(raw) < 32 or len(raw) % 16:
        return None
    iv, ct = raw[:16], raw[16:]
    try:
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        padded = decryptor.update(ct) + decryptor.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        plaintext = (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
    except Exception:
        return None
    if not hmac.compare_digest(deterministic_iv(key, plaintext), iv):
        return None
    return plaintext


def decrypt_value(key: bytes, token: str) -> str:
    """Entschluesselt ein Pseudonym -> Klartext. Alles andere bleibt unveraendert."""
    plaintext = try_decrypt(key, token)
    return token if plaintext is None else plaintext


# ======================== SPALTENERKENNUNG ========================

# Leerraum am Zellrand. Bewusst ausgeschrieben, damit Python und JavaScript gleich arbeiten.
_WS = "\t\n\x0b\x0c\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"
_EDGES_RE = re.compile("^([" + _WS + "]*)(.*?)([" + _WS + "]*)$", re.S)
_SUFFIX_RE = re.compile(r'\.[a-zA-Z0-9_]+$')


def split_edges(text: str) -> tuple:
    """Teilt in (Leerraum davor, Kern, Leerraum danach)."""
    m = _EDGES_RE.match(text)
    return m.group(1), m.group(2), m.group(3)


def strip_ws(text: str) -> str:
    return split_edges(text)[1]


def cell_text(value) -> str:
    """Textform eines Zellwerts. Diese Form wird verschluesselt (wie in der GUI)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e21:
        return str(int(value))
    return str(value)


def _normalize_header(h: str) -> str:
    """Entfernt eine Endung nach dem letzten Punkt (.x, .y, .1 aus R-Merges)."""
    return _SUFFIX_RE.sub('', h)


def column_kind(header, extra_lower=()):
    """Art einer Spalte: kanonischer Schluessel, '_name', '_custom' oder None."""
    h = strip_ws(cell_text(header))
    if not h:
        return None
    candidates = (h.lower(), _normalize_header(h).lower())
    for c in candidates:
        if c in _ALIAS_LOOKUP:
            return _ALIAS_LOOKUP[c]
    for c in candidates:
        if c in _NAME_LOOKUP:
            return "_name"
    return "_custom" if candidates[0] in extra_lower else None


class ColumnPlan:
    """Welche Spalten einer Kopfzeile verarbeitet werden.

    Alle passenden Spalten zaehlen, auch mehrere je Typ (Telefon und Handy)."""

    def __init__(self, headers, extra_cols=None):
        extra = [strip_ws(c).lower() for c in (extra_cols or []) if strip_ws(c)]
        self.headers = [cell_text(h) for h in headers]
        self.kinds = [column_kind(h, extra) for h in self.headers]
        self.names = [i for i, k in enumerate(self.kinds) if k == "_name"]
        self.cells = [i for i, k in enumerate(self.kinds) if k and k != "_name"]
        self.fam = [i for i, k in enumerate(self.kinds) if k == "familienname"]
        self.vor = [i for i, k in enumerate(self.kinds) if k == "vorname"]
        # (Spaltenindex, ist Name-Spalte) in Spaltenreihenfolge
        self.targets = sorted([(i, False) for i in self.cells] + [(i, True) for i in self.names])
        self.score = len(self.targets)
        present = {strip_ws(h).lower() for h in self.headers}
        self.missing_extra = [c for c in (extra_cols or [])
                              if strip_ws(c) and strip_ws(c).lower() not in present]

    def describe(self) -> str:
        return ", ".join(strip_ws(self.headers[i]) for i, _ in self.targets)


def find_identity_cols(headers: list) -> dict:
    """Erste Spalte je Typ: {kanonischer_key: tatsaechlicher_spaltenname}.
    Zur Verarbeitung dient ColumnPlan; dort zaehlen alle Spalten je Typ."""
    found = {}
    for h in headers:
        kind = column_kind(h)
        if kind and kind != "_name" and kind not in found:
            found[kind] = h
    return found


def find_name_col(headers: list):
    """Findet die erste NAME-Spalte (falls vorhanden)."""
    for h in headers:
        if column_kind(h) == "_name":
            return h
    return None


def find_header_row(rows, max_scan=20, extra_cols=None):
    """Findet die Kopfzeile: die Zeile mit den meisten erkannten Spalten unter den
    ersten max_scan Zeilen. Bei Gleichstand gewinnt die Zeile mit mehr gefuellten
    Zellen, dann die fruehere. Gibt den Index zurueck (0-basiert), ohne Treffer 0."""
    best, best_key = 0, (0, 0)
    for i, row in enumerate(rows[:max_scan]):
        headers = [cell_text(c) for c in row]
        score = ColumnPlan(headers, extra_cols).score
        key = (score, sum(1 for h in headers if strip_ws(h)))
        if score and key > best_key:
            best, best_key = i, key
    return best


# ======================== ZELLEN VERARBEITEN ========================

class _Worker:
    """Verarbeitet einzelne Zellen und zaehlt mit."""

    def __init__(self, secret, mode):
        self.mode = mode
        self.key = None if mode == "anonymize" else derive_key(secret)
        self.cells = 0     # verarbeitete Zellen
        self.failed = 0    # decrypt: Zellen ohne gueltiges Pseudonym (unveraendert)
        self.already = 0   # encrypt: Zellen, die schon ein Pseudonym dieses Secrets waren

    def cell(self, text: str) -> str:
        """Neuer Zellinhalt. Leerraum am Rand bleibt ausserhalb des Pseudonyms erhalten."""
        lead, core, trail = split_edges(text)
        if not core:
            return text
        if self.mode == "anonymize":
            self.cells += 1
            return ""
        if self.mode == "encrypt":
            if try_decrypt(self.key, core) is not None:
                self.already += 1
            self.cells += 1
            return lead + encrypt_value(self.key, core) + trail
        plain = try_decrypt(self.key, core)
        if plain is None:
            self.failed += 1
            return text
        self.cells += 1
        return lead + plain + trail

    def name_cell(self, text: str, fam_values, vor_values) -> str:
        """Name-Spalte. Besteht der Wert in DIESER Zeile aus Familienname und Vorname,
        wird er aus den beiden Pseudonymen zusammengesetzt (Reihenfolge bleibt).
        Sonst wird der ganze Wert ein Pseudonym."""
        lead, core, trail = split_edges(text)
        if not core or self.mode == "anonymize":
            return self.cell(text)
        if self.mode == "encrypt":
            for f in fam_values:
                for v in vor_values:
                    if not f or not v:
                        continue
                    parts = (f, v) if core == f + " " + v else (v, f) if core == v + " " + f else None
                    if parts:
                        self.cells += 1
                        return (lead + encrypt_value(self.key, parts[0]) + " "
                                + encrypt_value(self.key, parts[1]) + trail)
            return self.cell(text)
        parts = core.split(" ")
        if len(parts) == 2:
            a, b = try_decrypt(self.key, parts[0]), try_decrypt(self.key, parts[1])
            if a is not None and b is not None:
                self.cells += 1
                return lead + a + " " + b + trail
        return self.cell(text)

    def check(self):
        """Nach dem Durchlauf: falsches Secret erkennen."""
        if self.mode == "decrypt" and self.cells == 0 and self.failed > 0:
            raise PseudoError(
                "Kein Wert konnte entschluesselt werden. Das Secret ist vermutlich falsch, "
                "oder die Datei ist nicht pseudonymisiert. Es wurde keine Datei geschrieben.")

    def warnings(self) -> list:
        out = []
        if self.failed:
            out.append(f"{self.failed} Zelle(n) enthalten kein gueltiges Pseudonym fuer dieses "
                       "Secret und bleiben unveraendert.")
        if self.already:
            out.append(f"{self.already} Zelle(n) waren bereits mit diesem Secret pseudonymisiert "
                       "und wurden ein zweites Mal verschluesselt. Ist das die falsche Datei?")
        return out


def _no_columns_message(headers) -> str:
    shown = ", ".join(strip_ws(cell_text(h)) for h in headers if strip_ws(cell_text(h))) or "(keine)"
    return ("Keine Spalten mit Personendaten erkannt. Es wurde keine Datei geschrieben. "
            f"Vorhandene Spalten: {shown}. Weitere Spalten lassen sich mit --extra-cols angeben.")


def _print_report(mode, input_path, output_path, worker, lines, warnings):
    print(f"{MODES[mode][1]} abgeschlossen.")
    print(f"  Eingabe:    {input_path}")
    print(f"  Ausgabe:    {output_path}")
    for line in lines:
        print(f"  {line}")
    if mode == "anonymize":
        print(f"  Zellen:     {worker.cells} geleert (nicht wiederherstellbar)")
    else:
        print(f"  Zellen:     {worker.cells} verarbeitet (AES-256-CBC, deterministisch, PBKDF2)")
    for w in warnings:
        print(f"  WARNUNG: {w}")


# ======================== CSV ========================

_CP1252_UNDEFINED = (0x81, 0x8D, 0x8F, 0x90, 0x9D)
SEPARATORS = (";", ",", "\t")


def _cp1252_c1_passthrough(err):
    """In Windows-1252 undefinierte Bytes wie der Browser (WHATWG) auf die
    gleichwertigen C1-Zeichen abbilden (und beim Schreiben zurueck)."""
    if isinstance(err, UnicodeDecodeError):
        return "".join(chr(b) for b in err.object[err.start:err.end]), err.end
    if isinstance(err, UnicodeEncodeError):
        chars = err.object[err.start:err.end]
        if all(ord(c) in _CP1252_UNDEFINED for c in chars):
            return bytes(ord(c) for c in chars), err.end
    raise err


codecs.register_error("cp1252-c1", _cp1252_c1_passthrough)


def detect_file_encoding(raw: bytes) -> tuple:
    """Erkennt Encoding und BOM-Laenge aus rohen Bytes.
    Unterstuetzt UTF-8 (mit/ohne BOM), UTF-16 LE/BE (mit BOM, ohne BOM ueber die
    Verteilung der Null-Bytes) und Windows-1252 (BOM-lose Dateien, die kein
    gueltiges UTF-8 sind, z.B. ANSI-Exporte). Gibt (encoding, bom_length) zurueck."""
    if raw[:2] == b"\xff\xfe":
        return "utf-16-le", 2
    if raw[:2] == b"\xfe\xff":
        return "utf-16-be", 2
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8", 3
    sample = raw[:4096]
    if len(sample) >= 4 and len(raw) % 2 == 0:
        half = len(sample) // 2
        even, odd = sample[0:half * 2:2].count(0), sample[1:half * 2:2].count(0)
        if odd * 10 > half * 4 and even * 20 < half:
            return "utf-16-le", 0
        if even * 10 > half * 4 and odd * 20 < half:
            return "utf-16-be", 0
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return "cp1252", 0
    return "utf-8", 0


def scan_csv(text: str, sep: str, max_records=None) -> list:
    """Zerlegt CSV-Text in Zeilen aus Feldern, ohne den Text zu veraendern.
    Jedes Feld ist (Anfang, Ende, in Anfuehrungszeichen). So lassen sich einzelne
    Zellen ersetzen, waehrend alles andere Zeichen fuer Zeichen erhalten bleibt.
    Derselbe Algorithmus steht als scanCsv in pseudonym_gui.html."""
    n = len(text)
    records, fields, i = [], [], 0
    if n == 0:
        return records
    while True:
        start = i
        quoted = i < n and text[i] == '"'
        if quoted:
            i += 1
            while i < n:
                if text[i] == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
        while i < n and text[i] != sep and text[i] != "\n" and text[i] != "\r":
            i += 1
        fields.append((start, i, quoted))
        if i >= n:
            records.append(fields)
            return records
        if text[i] == sep:
            i += 1
            continue
        i += 2 if text[i] == "\r" and i + 1 < n and text[i + 1] == "\n" else 1
        records.append(fields)
        fields = []
        if i >= n or (max_records and len(records) >= max_records):
            return records


def field_value(text: str, field: tuple) -> str:
    """Inhalt eines Feldes ohne Anfuehrungszeichen."""
    start, end, quoted = field
    raw = text[start:end]
    if not quoted:
        return raw
    out, j = [], 1
    while j < len(raw):
        if raw[j] == '"':
            if j + 1 < len(raw) and raw[j + 1] == '"':
                out.append('"')
                j += 2
                continue
            j += 1
            break
        out.append(raw[j])
        j += 1
    return "".join(out) + raw[j:]


def csv_field(value: str, quoted: bool, sep: str) -> str:
    """Schreibweise eines neuen Feldinhalts. Anfuehrungszeichen bleiben, wo sie waren,
    und kommen dazu, wo der Inhalt sie braucht."""
    if quoted or sep in value or "\n" in value or "\r" in value or value[:1] == '"':
        return '"' + value.replace('"', '""') + '"'
    return value


def detect_separator(text: str, extra_cols=None) -> str:
    """Waehlt das Trennzeichen, mit dem die Kopfzeile die meisten erkannten Spalten hat."""
    best_sep, best_key = None, (0, 0)
    for sep in SEPARATORS:
        rows = [[field_value(text, f) for f in rec] for rec in scan_csv(text, sep, 20)]
        if not rows:
            continue
        header = rows[find_header_row(rows, extra_cols=extra_cols)]
        key = (ColumnPlan(header, extra_cols).score, len(header))
        if key[0] and key > best_key:
            best_sep, best_key = sep, key
    if best_sep:
        return best_sep
    # Keine Spalte erkannt: das haeufigste Trennzeichen in den ersten 20 Zeilen
    lines = [l for l in re.split(r"\r\n|\r|\n", text[:20000]) if strip_ws(l)][:20]
    best_sep, best_count = ",", 0
    for sep in SEPARATORS:
        count = sum(l.count(sep) for l in lines)
        if count > best_count:
            best_sep, best_count = sep, count
    return best_sep


def process_csv(input_path: str, output_path: str, secret: str, mode: str, sep: str = None,
                extra_cols: list = None) -> dict:
    with open(input_path, "rb") as f:
        raw = f.read()

    encoding, bom_len = detect_file_encoding(raw)
    codec_errors = "cp1252-c1" if encoding == "cp1252" else "strict"
    try:
        text = raw[bom_len:].decode(encoding, errors=codec_errors)
    except UnicodeDecodeError:
        raise PseudoError("Die Datei ist nicht lesbar. Bitte als CSV in UTF-8 speichern.")
    if not strip_ws(text):
        raise PseudoError("Die Datei ist leer.")

    if sep is None:
        sep = detect_separator(text, extra_cols)
    records = scan_csv(text, sep)

    # Kopfzeile finden (kann nach Metadaten-Zeilen liegen, z.B. MLW-Export)
    head_rows = [[field_value(text, f) for f in rec] for rec in records[:20]]
    header_idx = find_header_row(head_rows, extra_cols=extra_cols)
    plan = ColumnPlan(head_rows[header_idx], extra_cols)
    if not plan.score:
        raise PseudoError(_no_columns_message(plan.headers))

    # Nur die betroffenen Felder ersetzen. Der uebrige Text (Metadaten-Zeilen, Zeilenenden,
    # Anfuehrungszeichen, Leerzeilen, ueberzaehlige Zellen) bleibt byte-genau erhalten.
    worker = _Worker(secret, mode)
    out, pos, data_rows, long_rows, width = [], 0, 0, 0, len(plan.headers)
    for rec in records[header_idx + 1:]:
        n = len(rec)
        if n > 1 or rec[0][1] > rec[0][0]:
            data_rows += 1
        if n > width:
            long_rows += 1
        fam = vor = ()
        if plan.names:
            fam = [strip_ws(field_value(text, rec[i])) for i in plan.fam if i < n]
            vor = [strip_ws(field_value(text, rec[i])) for i in plan.vor if i < n]
        for i, is_name in plan.targets:
            if i >= n:
                break
            field = rec[i]
            old = field_value(text, field)
            new = worker.name_cell(old, fam, vor) if is_name else worker.cell(old)
            if new != old:
                out.append(text[pos:field[0]])
                out.append(csv_field(new, field[2], sep))
                pos = field[1]
    out.append(text[pos:])
    output_text = "".join(out)
    worker.check()

    warnings = worker.warnings()
    if plan.missing_extra:
        warnings.append("Zusatzspalte(n) nicht gefunden: " + ", ".join(plan.missing_extra))
    if long_rows:
        warnings.append(f"{long_rows} Zeile(n) haben mehr Zellen als die Kopfzeile. Dort koennen Werte "
                        "in einer falschen Spalte stehen und unveraendert bleiben. Bitte pruefen.")
    if header_idx > 0 and mode == "anonymize":
        warnings.append(f"{header_idx} Zeile(n) vor der Kopfzeile bleiben unveraendert. "
                        "Bitte pruefen, ob dort Namen stehen.")

    bom = raw[:bom_len]
    try:
        data = output_text.encode(encoding, errors=codec_errors)
    except UnicodeEncodeError:
        # Zurueckgefuehrter Wert passt nicht in die Kodierung der Eingabe (z.B. Windows-1252)
        bom, data, encoding = codecs.BOM_UTF8, output_text.encode("utf-8"), "utf-8"
        warnings.append("Ein Wert passt nicht in die Kodierung der Eingabe. "
                        "Die Ausgabe ist UTF-8 mit BOM.")
    # Reine ASCII-Eingabe (z.B. Pseudonym-Datei), Ausgabe mit Umlauten: Original-Kodierung
    # nicht bestimmbar -> UTF-8 mit BOM, damit Excel die Umlaute korrekt anzeigt
    if encoding == "utf-8" and bom_len == 0 and raw.isascii() and not output_text.isascii():
        bom = codecs.BOM_UTF8
    with open(output_path, "wb") as f:
        f.write(bom)
        f.write(data)

    lines = [f"Zeilen:     {data_rows}",
             f"Spalten:    {plan.describe()}",
             f"Kodierung:  {encoding.upper()}{' (BOM)' if bom else ''}, "
             f"Trennzeichen {'Tab' if sep == chr(9) else repr(sep)}"]
    if bom and bom_len == 0:
        lines.append("Hinweis:    Ausgabe als UTF-8 mit BOM, damit Excel Umlaute richtig zeigt")
    if header_idx > 0:
        lines.append(f"Metadaten:  {header_idx} Zeile(n) vor der Kopfzeile (unveraendert)")
    _print_report(mode, input_path, output_path, worker, lines, warnings)
    return {"cells": worker.cells, "failed": worker.failed, "already": worker.already,
            "warnings": warnings}


# ======================== XLSX ========================

def _fix_xlsx_drawings(input_path: str) -> str:
    """Repariert XLSX-Dateien mit Verweisen auf fehlende Zeichnungen.
    Entfernt nur die Verweise, deren Ziel fehlt; vorhandene Zeichnungen bleiben.
    Gibt den Pfad zur (ggf. reparierten Kopie der) Datei zurueck."""
    import zipfile
    import tempfile

    def target_path(target):
        if target.startswith("/"):
            return target.lstrip("/")
        return os.path.normpath("xl/worksheets/" + target).replace("\\", "/")

    with zipfile.ZipFile(input_path, "r") as zf:
        names = set(zf.namelist())

        def drop_missing(match):
            tag = match.group(0)
            target = re.search(r'Target="([^"]*)"', tag)
            if (not re.search(r'Type="[^"]*drawing[^"]*"', tag, re.I) or not target
                    or 'TargetMode="External"' in tag):
                return tag
            return tag if target_path(target.group(1)) in names else ""

        fixes = {}
        for name in names:
            if name.startswith("xl/worksheets/_rels/") and name.endswith(".rels"):
                content = zf.read(name).decode("utf-8")
                cleaned = re.sub(r'<Relationship\b[^>]*/>\s*', drop_missing, content)
                if cleaned != content:
                    fixes[name] = cleaned
        if not fixes:
            return input_path

        print("  HINWEIS: Verweise auf fehlende Zeichnungen werden entfernt.")
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=Path(input_path).suffix)
        os.close(tmp_fd)
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zf.infolist():
                data = zf.read(item.filename)
                if item.filename in fixes:
                    data = fixes[item.filename].encode("utf-8")
                zout.writestr(item, data)
        return tmp_path


def _load_workbook(input_path: str, keep_vba: bool):
    import zipfile
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise PseudoError(package_hint(["openpyxl"])) from None

    fixed_path = input_path
    try:
        fixed_path = _fix_xlsx_drawings(input_path)
        return load_workbook(fixed_path, keep_vba=keep_vba)
    except (zipfile.BadZipFile, KeyError, ValueError) as e:
        raise PseudoError(
            "Die Datei ist keine lesbare Excel-Datei (.xlsx/.xlsm). Moegliche Ursachen: "
            "Die Datei ist mit einem Kennwort geschuetzt, beschaedigt oder im alten .xls-Format. "
            f"Bitte in Excel ohne Kennwort als .xlsx speichern. (Technisch: {type(e).__name__})")
    finally:
        if fixed_path != input_path:
            os.unlink(fixed_path)


def process_xlsx(input_path: str, output_path: str, secret: str, mode: str,
                 extra_cols: list = None) -> dict:
    is_xlsm = Path(input_path).suffix.lower() == ".xlsm"
    wb = _load_workbook(input_path, keep_vba=is_xlsm)
    try:
        worker = _Worker(secret, mode)
        processed, skipped, warnings, missing_extra = [], [], [], None

        for ws in wb.worksheets:
            # Zeilen- und Spaltenzahl EINMAL lesen: openpyxl berechnet sie bei jedem Zugriff neu
            max_row, max_col = ws.max_row or 0, ws.max_column or 0
            head = [[cell_text(v) for v in row] for row in
                    ws.iter_rows(min_row=1, max_row=min(max_row, 20), max_col=max_col, values_only=True)]
            if not any(strip_ws(c) for row in head for c in row):
                skipped.append(f"{ws.title} (leer)")
                continue

            header_idx = find_header_row(head, extra_cols=extra_cols)
            plan = ColumnPlan(head[header_idx], extra_cols)
            missing = set(plan.missing_extra)
            missing_extra = missing if missing_extra is None else missing_extra & missing
            if not plan.score:
                shown = ", ".join(strip_ws(h) for h in plan.headers if strip_ws(h))
                skipped.append(f"{ws.title} (keine Spalten mit Personendaten erkannt: {shown})")
                continue

            before = worker.cells
            for row_idx in range(header_idx + 2, max_row + 1):
                fam = vor = ()
                if plan.names:
                    fam = [strip_ws(cell_text(ws.cell(row=row_idx, column=i + 1).value)) for i in plan.fam]
                    vor = [strip_ws(cell_text(ws.cell(row=row_idx, column=i + 1).value)) for i in plan.vor]
                for i, is_name in plan.targets:
                    cell = ws.cell(row=row_idx, column=i + 1)
                    if cell.value is None:
                        continue
                    old = cell_text(cell.value)
                    new = worker.name_cell(old, fam, vor) if is_name else worker.cell(old)
                    if new == old:
                        continue
                    if mode == "anonymize":
                        cell.value = None
                        cell.comment = None
                    else:
                        cell.value = new
            processed.append(f"{ws.title} ({plan.describe()}: {worker.cells - before} Zellen)")
            if header_idx > 0:
                processed.append(f"  Kopfzeile in Zeile {header_idx + 1}, "
                                 f"{header_idx} Zeile(n) davor unveraendert")
                if mode == "anonymize":
                    warnings.append(f"Blatt {ws.title}: {header_idx} Zeile(n) vor der Kopfzeile "
                                    "bleiben unveraendert. Bitte pruefen, ob dort Namen stehen.")

        if not processed:
            raise PseudoError("Keine Spalten mit Personendaten erkannt. Es wurde keine Datei "
                              "geschrieben. Geprueft: " + "; ".join(skipped))
        worker.check()
        warnings = worker.warnings() + warnings
        if missing_extra:
            warnings.append("Zusatzspalte(n) nicht gefunden: " + ", ".join(sorted(missing_extra)))
        if skipped and mode != "decrypt":
            warnings.append("Nicht verarbeitete Blaetter bleiben unveraendert in der Datei: "
                            + "; ".join(skipped))
        if mode == "anonymize":
            # Dateieigenschaften nennen sonst weiter die Person, die die Datei erstellt hat
            wb.properties.creator = "pseudonym.py"
            wb.properties.lastModifiedBy = "pseudonym.py"

        wb.save(output_path)
    finally:
        # In-Memory-VBA-Archiv schliessen (verhindert ResourceWarning beim GC)
        if is_xlsm and wb.vba_archive is not None:
            wb.vba_archive.close()

    lines = ["Blaetter:"] + [f"  + {s}" for s in processed] + [f"  - {s}" for s in skipped]
    _print_report(mode, input_path, output_path, worker, lines, warnings)
    return {"cells": worker.cells, "failed": worker.failed, "already": worker.already,
            "warnings": warnings}


# ======================== EINGABEDATEIEN ========================

SUPPORTED = {".csv", ".tsv", ".txt", ".xlsx", ".xlsm"}
# In ZIP-Archiven und Ordnern zaehlt .txt nicht mit (liesmich.txt und Aehnliches)
BULK_SUPPORTED = {".csv", ".tsv", ".xlsx", ".xlsm"}
NOT_FOUND = "nicht gefunden"

_ZIP_SOURCES = {}  # entpackte Datei (str) -> Quell-ZIP (Path)
_TEMP_DIRS = []    # Temp-Verzeichnisse mit entpacktem Klartext


def zip_source(path):
    """Gibt das Quell-ZIP einer aus einem ZIP entpackten Datei zurueck (sonst None)."""
    return _ZIP_SOURCES.get(str(path))


def cleanup_temp_dirs():
    """Loescht die aus ZIP-Archiven entpackten Klartextdateien."""
    import shutil
    while _TEMP_DIRS:
        shutil.rmtree(_TEMP_DIRS.pop(), ignore_errors=True)
    _ZIP_SOURCES.clear()


def _is_hidden(name: str) -> bool:
    return name.startswith(".") or name.startswith("~$")


def _is_own_output(path: Path, mode) -> bool:
    """Ergebnis eines frueheren Laufs? Schuetzt Ordner und Platzhalter vor Doppelverarbeitung."""
    if mode is None:
        return False
    skip = ("_restored", "_anonym") if mode == "decrypt" else ("_pseudo", "_restored", "_anonym")
    return re.sub(r"_\d+$", "", path.stem).endswith(skip)


def _extract_zip(zip_path: Path, collected: list, skipped: list):
    import zipfile
    import tempfile

    tmpdir = Path(tempfile.mkdtemp(prefix="pseudo_zip_"))
    _TEMP_DIRS.append(tmpdir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            name = Path(member).name
            if member.endswith("/") or _is_hidden(name) or member.startswith("__MACOSX/"):
                continue
            ext = Path(member).suffix.lower()
            if ext not in BULK_SUPPORTED:
                skipped.append((f"{zip_path.name}: {member}", "Format nicht unterstuetzt"))
                continue
            target = tmpdir / name
            counter = 1
            while target.exists():
                target = tmpdir / f"{Path(member).stem}_{counter}{ext}"
                counter += 1
            with open(target, "wb") as f:
                f.write(zf.read(member))
            _ZIP_SOURCES[str(target)] = zip_path
            collected.append(target)


def collect_input_files(paths: list, skipped: list = None, mode: str = None) -> list:
    """Sammelt Eingabedateien aus Dateien, Ordnern, Platzhaltern (*.csv) und ZIP-Archiven.
    ZIP-Archive werden in ein Temp-Verzeichnis entpackt (cleanup_temp_dirs raeumt auf).
    skipped erhaelt (Name, Grund) fuer alles, was nicht verarbeitet wird.
    Gibt eine Liste von Path-Objekten zurueck."""
    import glob
    import zipfile

    skipped = [] if skipped is None else skipped
    collected = []

    def add_bulk(candidates):
        for c in sorted(candidates):
            if not c.is_file() or _is_hidden(c.name) or c.suffix.lower() not in BULK_SUPPORTED:
                continue
            if _is_own_output(c, mode):
                skipped.append((str(c), "Ergebnis eines frueheren Laufs"))
            else:
                collected.append(c)

    for raw_path in paths:
        p = Path(raw_path)
        if p.is_dir():
            add_bulk(p.iterdir())
        elif not p.exists():
            # Windows-Konsolen loesen Platzhalter nicht auf, daher hier
            matches = [Path(m) for m in glob.glob(str(raw_path))] if glob.has_magic(str(raw_path)) else []
            if not matches:
                skipped.append((str(raw_path), NOT_FOUND))
            add_bulk(m for m in matches if m.suffix.lower() != ".zip")
            for m in sorted(m for m in matches if m.suffix.lower() == ".zip"):
                _extract_zip(m, collected, skipped)
        elif p.suffix.lower() == ".zip":
            try:
                _extract_zip(p, collected, skipped)
            except zipfile.BadZipFile:
                skipped.append((str(p), "kein lesbares ZIP-Archiv"))
        elif p.suffix.lower() in SUPPORTED:
            collected.append(p)
        else:
            skipped.append((str(p), "Format nicht unterstuetzt (moeglich: CSV, TSV, TXT, XLSX, XLSM, ZIP)"))

    return collected


def create_output_zip(results: list, zip_path: str):
    """Buendelt Ergebnisdateien in ein ZIP-Archiv.
    results: Liste von (input_path, output_path) Tupeln."""
    import zipfile

    used = set()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for _, output_path in results:
            zf.write(output_path, Path(_unique_path(Path(output_path).name, used)).name)
    print(f"\n  ZIP erstellt: {zip_path}")


def make_zip_name(input_files: list, mode: str) -> str:
    """ZIP-Name (wie GUI): Quell-ZIP bzw. gemeinsamer Dateinamen-Anfang + Modus + Anzahl + Datum."""
    from datetime import date

    suffix = MODES[mode][0]
    sources = {zip_source(f) for f in input_files}
    if len(sources) == 1 and None not in sources:
        return f"{sources.pop().stem}{suffix}.zip"
    stems = [Path(f).stem for f in input_files]
    # Zeichenweise gemeinsamer Anfang (os.path.commonprefix ist ab Python 3.15 veraltet)
    low, high = min(stems), max(stems)
    prefix = low[:next((i for i, ch in enumerate(low) if ch != high[i]), len(low))]
    if prefix != stems[0]:
        prefix = re.sub(r"[^_\-. ]*$", "", prefix)  # nicht mitten im Wort abschneiden
    prefix = re.sub(r"[_\-. ]+$", "", prefix)
    if len(prefix) < 3:
        prefix = "Batch"
    return f"{prefix}{suffix}_{len(input_files)}Dateien_{date.today().isoformat()}.zip"


def make_output_path(input_path, mode: str, output_dir: str = None) -> str:
    """Erzeugt Ausgabepfad: <name>_pseudo.<ext>, <name>_restored.<ext> bzw. <name>_anonym.<ext>.
    Optional in ein anderes Verzeichnis (output_dir)."""
    p = Path(input_path)
    name = f"{p.stem}{MODES[mode][0]}{p.suffix}"
    if output_dir:
        return str(Path(output_dir) / name)
    return str(p.with_name(name))


def _unique_path(path: str, used: set) -> str:
    """Haengt _1, _2, ... an, wenn der Pfad in diesem Lauf schon vergeben ist."""
    p, candidate, counter = Path(path), str(path), 1
    while candidate.lower() in used:
        candidate = str(p.with_name(f"{p.stem}_{counter}{p.suffix}"))
        counter += 1
    used.add(candidate.lower())
    return candidate


# ======================== DISPATCH ========================

def process_file(input_path: str, output_path: str, secret: str, mode: str, sep: str = None,
                 extra_cols: list = None) -> dict:
    """Verarbeitet eine einzelne CSV/XLSX/XLSM-Datei (Dispatch nach Dateityp).
    mode: encrypt, decrypt oder anonymize (dann wird kein Secret gebraucht).
    sep: CSV-Trennzeichen; None erkennt es automatisch."""
    if mode not in MODES:
        raise PseudoError(f"Unbekannter Modus '{mode}'.")
    ext = Path(input_path).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return process_xlsx(input_path, output_path, secret, mode, extra_cols=extra_cols)
    if ext in (".csv", ".tsv", ".txt"):
        return process_csv(input_path, output_path, secret, mode, sep, extra_cols=extra_cols)
    raise PseudoError(f"Unbekanntes Dateiformat '{ext}'. Unterstuetzt: .csv, .tsv, .txt, .xlsx, .xlsm")


# ======================== MAIN ========================

def _explain(error: Exception) -> str:
    """Uebersetzt bekannte Fehler in einen Satz mit Handlungshinweis."""
    if isinstance(error, PseudoError):
        return str(error)
    if isinstance(error, PermissionError):
        return (f"Kein Zugriff auf '{error.filename}'. Ist die Datei in Excel geoeffnet "
                "oder schreibgeschuetzt?")
    if isinstance(error, FileNotFoundError):
        return f"Datei oder Ordner {NOT_FOUND}: {error.filename}"
    if isinstance(error, MemoryError):
        return "Die Datei ist zu gross fuer den Arbeitsspeicher."
    return f"Unerwarteter Fehler ({type(error).__name__}): {error}"


def _read_secret(args) -> str:
    """Secret aus --secret, der Umgebungsvariable PSEUDONYM_SECRET oder verdeckter Eingabe.
    Die verdeckte Eingabe hinterlaesst nichts im Verlauf der Konsole."""
    import getpass

    if args.mode == "anonymize":
        return None
    secret = args.secret if args.secret is not None else os.environ.get("PSEUDONYM_SECRET")
    if secret is None:
        secret = getpass.getpass("Secret: ")
        if args.mode == "encrypt" and getpass.getpass("Secret wiederholen: ") != secret:
            raise PseudoError("Die beiden Eingaben stimmen nicht ueberein. Es wurde nichts verarbeitet.")
    if not secret:
        raise PseudoError("Das Secret ist leer.")
    return secret


def _parse_sep(sep):
    if sep is None or sep.lower() == "auto":
        return None
    sep = {"\\t": "\t", "tab": "\t"}.get(sep.lower(), sep)
    if len(sep) != 1:
        raise PseudoError("--sep braucht genau ein Zeichen, zum Beispiel ';' oder ',' oder '\\t' fuer Tab.")
    return sep


def _run(args) -> int:
    extra_cols = [c.strip() for c in args.extra_cols.split(",") if c.strip()] if args.extra_cols else None
    sep = _parse_sep(args.sep)

    # Dateien sammeln (Ordner, Platzhalter; ZIP-Archive werden entpackt)
    skipped = []
    all_files = collect_input_files(args.input, skipped, args.mode)
    missing = [name for name, why in skipped if why == NOT_FOUND]
    if missing:
        raise PseudoError(f"Datei {NOT_FOUND}: " + ", ".join(missing))
    for name, why in skipped:
        print(f"Uebersprungen: {name} ({why})")
    if not all_files:
        raise PseudoError("Keine verarbeitbaren Dateien gefunden (CSV/TSV/XLSX/XLSM).")
    if args.output and len(all_files) > 1:
        raise PseudoError("--output ist nur bei einer einzelnen Datei moeglich. "
                          f"Gefunden: {len(all_files)} Dateien. Bitte --output-dir verwenden.")

    # Fehlende Pakete vor der Secret-Abfrage melden, nicht bei jeder Datei einzeln
    packages = missing_packages(crypto=args.mode != "anonymize",
                                excel=any(f.suffix.lower() in (".xlsx", ".xlsm") for f in all_files))
    if packages:
        raise PseudoError(package_hint(packages))

    secret = _read_secret(args)
    if args.output_dir:
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    batch = len(all_files) > 1
    if batch:
        print(f"\nBatch-Modus: {len(all_files)} Datei(en)\n")

    results, used = [], set()
    for f in all_files:
        if args.output:
            out = args.output
        else:
            # Aus ZIP entpackte Dateien: Ausgabe neben das ZIP (Temp-Verzeichnis wird geloescht)
            src_zip = zip_source(f)
            out_dir = args.output_dir or (str(src_zip.parent) if src_zip else None)
            out = _unique_path(make_output_path(f, args.mode, out_dir), used)
        try:
            process_file(str(f), out, secret, args.mode, sep, extra_cols=extra_cols)
            results.append((str(f), out, True, None))
        except Exception as e:  # eine Datei darf den Stapel nicht abbrechen
            message = _explain(e)
            print(f"\nFEHLER bei {f.name}: {message}", file=sys.stderr)
            results.append((str(f), None, False, message))
        if batch:
            print()

    successful = [(r[0], r[1]) for r in results if r[2]]
    if args.zip and successful:
        first_input = Path(successful[0][0])
        zip_dir = args.output_dir or str((zip_source(first_input) or first_input).parent)
        create_output_zip(successful, str(Path(zip_dir) / make_zip_name([r[0] for r in successful], args.mode)))

    if batch:
        fail = len(results) - len(successful)
        print(f"{'=' * 50}")
        print(f"Batch abgeschlossen: {len(successful)} erfolgreich, {fail} fehlgeschlagen")
        for inp, _, success, err in results:
            if not success:
                print(f"  FEHLER: {Path(inp).name}: {err}")
        print(f"{'=' * 50}")
    elif successful and args.mode == "encrypt":
        print(f"\n  Zum Zurueckfuehren:\n  python pseudonym.py decrypt \"{successful[0][1]}\"")

    return 0 if len(successful) == len(results) else 1


class _VersionAction(argparse.Action):
    """--version dient als Installationspruefung und nennt fehlende Pakete.
    Eigene Aktion: argparse bricht den Text sonst um, und der Installationsbefehl zerfaellt."""

    def __call__(self, parser, namespace, values, option_string=None):
        print(f"{parser.prog} {__version__}")
        missing = missing_packages()
        if missing:
            print("ACHTUNG: " + package_hint(missing))
        parser.exit()


def main(argv=None) -> int:
    """Kommandozeile. Gibt den Rueckgabecode zurueck (0 = alles verarbeitet)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):  # Zeichen, die die Konsole nicht kennt, nicht abstuerzen lassen
            stream.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description="CSV/XLSX/XLSM pseudonymisieren, zurueckfuehren oder anonymisieren. "
                    "Nur mit Secret, ohne Key-Datei.")
    parser.add_argument("--version", action=_VersionAction, nargs=0,
                        help="Version anzeigen und pruefen, ob alle Python-Pakete installiert sind")
    parser.add_argument("mode", choices=list(MODES),
                        help="encrypt = pseudonymisieren, decrypt = zurueckfuehren, "
                             "anonymize = Identitaetsspalten endgueltig leeren")
    parser.add_argument("input", nargs="+",
                        help="Dateien (CSV/TSV/XLSX/XLSM/ZIP), Ordner oder Platzhalter wie *.csv")
    parser.add_argument("--secret",
                        help="Ihr geheimer Schluessel. Besser weglassen: Dann fragt das Programm "
                             "verdeckt danach, und das Secret steht nicht im Verlauf der Konsole. "
                             "Alternativ: Umgebungsvariable PSEUDONYM_SECRET")
    parser.add_argument("--output", "-o",
                        help="Ausgabepfad (nur bei einzelner Datei)")
    parser.add_argument("--output-dir",
                        help="Ausgabeverzeichnis (wird bei Bedarf angelegt)")
    parser.add_argument("--zip", action="store_true",
                        help="Ergebnis zusaetzlich als ZIP-Datei buendeln")
    parser.add_argument("--sep", "-s", default=None,
                        help="CSV-Trennzeichen, z.B. ';' oder '\\t' (Standard: automatisch erkennen)")
    parser.add_argument("--extra-cols",
                        help="Zusaetzliche Spalten verarbeiten (kommagetrennt, z.B. 'Kommentar,Notiz')")
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except PseudoError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 1
    finally:
        cleanup_temp_dirs()


if __name__ == "__main__":
    sys.exit(main())
