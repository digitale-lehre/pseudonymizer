# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tool for pseudonymizing, de-pseudonymizing and anonymizing personal data (names, student IDs, email addresses, examiner names, social security numbers, dates of birth, phone numbers) in CSV, XLSX, and XLSM files. Three modes: `encrypt` (replace by pseudonyms), `decrypt` (restore), `anonymize` (clear the cells for good, no secret). Used at MedUni Wien for handling student data in tertial assignment workflows.

Two implementations exist — a Python CLI (`pseudonym.py`) and a standalone browser GUI (`pseudonym_gui.html`). Both use identical cryptography and must always produce the same output for the same input and secret.

## Architecture

```
pseudonym.py            Python CLI (requires cryptography, openpyxl; see requirements.txt)
pseudonym_gui.html      Single-file browser app (Web Crypto API; SheetJS and JSZip are embedded, no network access)
ANLEITUNG_pseudonym.md  German-language user documentation
tests/                  pytest suite: test_core, test_cli, test_batch, test_consistency, test_gui_parity
tests/gui_harness.js    Runs the GUI's inline script in Node so it can be compared with the CLI
tools/gui_libs.py       Checks the embedded libraries against the vendors' files, finds newer versions, embeds them
docs/                   Wiki-style documentation (column-reference, cryptography, troubleshooting, etc.)
```

## Cryptographic Specification (MUST stay identical in both implementations)

- **Key derivation**: PBKDF2-HMAC-SHA256, 100,000 iterations, salt = `MedUniWien-Pseudo-Salt` (UTF-8 encoded) → 256-bit key
- **Deterministic IV**: HMAC-SHA256(key, plaintext)[:16]
- **Encryption**: AES-256-CBC with PKCS7 padding
- **Output format**: URL-safe Base64 (no trailing `=`) of `IV || ciphertext`
- **Verification on decrypt**: recompute `HMAC-SHA256(key, plaintext)[:16]` and compare with the IV in the token. A value that fails is "not a pseudonym for this secret" and stays unchanged. This detects a wrong secret exactly and needs no format change.
- **What is encrypted**: the cell text without surrounding whitespace (the whitespace stays outside the token). Excel cells use their text form (`cell_text()` / `cellText()`): integer-valued numbers without `.0`, dates as `2000-01-31 00:00:00`.
- **CRITICAL**: Any change to these parameters breaks compatibility between the two implementations and makes existing encrypted files unreadable. Never change salt, iteration count, IV derivation, or encoding without updating BOTH implementations and providing a migration path.

## Column Recognition (case-insensitive, must match in both implementations)

Matching ignores case, so each spelling is listed once (`FAMILIENNAME` matches `Familienname`). **All** matching columns are processed, also several per type (`Telefon` and `Handy`, `Vorname.x` and `Vorname.y`).

| Canonical key | Aliases |
|--------------|---------|
| familienname | Familienname, Zuname, Nachname, Last Name, LastName, Surname, Family Name, Family_Name, FAMILY_NAME_OF_STUDENT, Familienname oder Nachname, Familien- oder Nachname |
| vorname | Vorname, First Name, FirstName, Given Name, GivenName, Rufname, FIRST_NAME_OF_STUDENT |
| matnr | Matrikelnummer, Matnr, MatrNr, Matrikel, Matrikelnr, Matrikelnr., Mat.Nr., Mat.Nr, Mat-Nr., Mat-Nr, Mat. Nr., StudentID, Student_ID, Student ID, REGISTRATION_NUMBER, Registration Number, ID number, ID-Nummer, Kennnummer |
| email | EMAIL_ADDRESS, E-Mail, Email, Mail, E_MAIL, EmailAddress, E-Mail-Adresse, E-Mail Adresse, Emailadresse, Mailadresse, Email address, E-Mail des Teilnehmers, Attendee Email |
| pruefer | Examiner, Prüfer, Pruefer, Prufer, Prüfer/in, PrüferIn, Prüfer:in |
| anzeigename | Anzeigename, Display Name, DisplayName, Full Name, FullName, Student Name |
| svnr | Sozialversicherungsnummer, SVNr, SV-Nr, SV-Nr., SV-Nummer, SV Nummer, Versicherungsnummer, Social Security Number, SSN |
| geburtsdatum | Geburtsdatum, Geburtstag, Geb.Datum, Geb.-Datum, GebDatum, Geb. Datum, Birthday, Date of Birth, DateOfBirth, DOB, Birth Date, BirthDate |
| telefon | Telefon, Telefonnummer, Tel, Tel., Tel.Nr., TelNr, Phone, Phone Number, PhoneNumber, Handy, Handynummer, Mobilnummer, Mobile, Mobiltelefon, Cell, Cell Phone |
| examiner_id | examiner_id |
| examiner_nachname | examiner_last_name |
| examiner_vorname | examiner_first_name |
| candidate_id | candidate_id |
| candidate_nachname | candidate_last_name |
| candidate_vorname | candidate_first_name |

Valuatic exam software columns use separate canonical keys (e.g., `examiner_nachname` vs `familienname`) because examiner and candidate data appear in the same file and must be encrypted independently.

**Suffix stripping:** Before matching, one trailing `.suffix` (letters, digits, underscore) is stripped from the header, e.g. `.x`, `.y`, `.1` from R merges. `Vorname.x` matches as `Vorname`, `Name.y` as `Name`. The rule is deliberately broad (`Mail.Server` counts as email): encrypting one column too many is safer than one too few. Do not narrow it without checking real exports.

`NAME` column: checked **per row**. If the cell equals `familienname vorname` or `vorname familienname` of the same row, it becomes `<token> <token>` in the same order. Otherwise the whole value becomes one token. On decrypt, a cell of two valid tokens is restored part by part, anything else as one token. Both ways return the original text. Note: `Anzeigename`/`Display Name` is NOT a composite — it is encrypted independently (Webex display names may differ from Vorname + Nachname). A file whose only recognized column is `Name` is still processed.

When adding new aliases, update `COLUMN_ALIASES` in `pseudonym.py` AND the `COLUMN_ALIASES` object in `pseudonym_gui.html`. `tests/test_consistency.py` fails if the two differ or if an alias is missing in a doc table.

## Encoding Support

Both implementations handle multiple file encodings for CSV:
- **UTF-8** (with and without BOM)
- **UTF-16 LE** (with BOM — used by Webex exports; without BOM detected by the pattern of NUL bytes)
- **UTF-16 BE** (with or without BOM)
- **Windows-1252** (no BOM, not valid UTF-8 -- ANSI exports, e.g. from MedCampus or Excel)

Undefined Windows-1252 bytes (0x81, 0x8D, 0x8F, 0x90, 0x9D) map to the matching C1 characters, as browsers do (Python: `cp1252-c1` error handler).

Detection is via `detect_file_encoding()` (Python) / `detectEncoding()` (JS). The original encoding, BOM and trailing newline (present or absent) are preserved on output for byte-identical roundtrips.

Two exceptions, both written as **UTF-8 with BOM**: (1) a decrypted value that the input encoding cannot represent (e.g. `Č` in Windows-1252), with a warning; (2) a pure-ASCII input without BOM (e.g. a pseudonymized file whose umlauts were all in encrypted columns) whose output contains non-ASCII characters, because the original encoding cannot be determined and Excel needs the BOM to show umlauts correctly.

## Build & Test Commands

```bash
# Install Python dependencies
pip install cryptography openpyxl

# Encrypt CSV (separator is auto-detected; --sep ";" forces one)
python pseudonym.py encrypt input.csv --secret "test"

# Encrypt XLSX
python pseudonym.py encrypt input.xlsx --secret "test"

# Decrypt
python pseudonym.py decrypt input_pseudo.csv --secret "test"

# Anonymize (clears the identity cells, no secret)
python pseudonym.py anonymize input.csv

# Roundtrip verification (byte-identical for CSV; the two exceptions are listed under "Encoding Support")
python pseudonym.py encrypt input.csv --secret "test"
python pseudonym.py decrypt input_pseudo.csv --secret "test"
diff input.csv input_pseudo_restored.csv
```

```bash
# Batch encrypt: files, a folder, or a wildcard (expanded by the program, works on Windows)
python pseudonym.py encrypt file1.csv file2.csv --secret "test"
python pseudonym.py encrypt exports/ --secret "test" --output-dir out/
python pseudonym.py encrypt "*.csv" --secret "test"

# ZIP input
python pseudonym.py encrypt archive.zip --secret "test"

# ZIP output
python pseudonym.py encrypt "*.csv" --secret "test" --zip

# Encrypt with extra columns
python pseudonym.py encrypt input.csv --secret "test" --extra-cols "Kommentar,Notiz"

# Run all tests (new test files are picked up automatically). The GUI parity tests
# are skipped without Node.js; they take the libraries from the HTML file itself
python -m pytest tests -v

# Embedded GUI libraries: verify against the vendors' files and look for newer versions
python tools/gui_libs.py check
```

`--secret "test"` is fine for throwaway test data. With a real secret, omit `--secret`: the CLI then prompts without echo (twice on encrypt). `PSEUDONYM_SECRET` works for scripts.

Run tests with synthetic data only, and write test output outside the project folder.

The browser GUI requires no build step — open `pseudonym_gui.html` in any modern browser.

## Cross-Implementation Compatibility Test

After any crypto change, verify both implementations produce identical output:

```python
# Python: encrypt a known value
from pseudonym import derive_key, encrypt_value
key = derive_key("testSecret123")
print(encrypt_value(key, "Mueller"))
# Expected: a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc
```

The HTML GUI must produce the same token for the same input and secret. Check it in the browser console of the opened page:

```js
createCipher("testSecret123").then(c => c.encrypt("Mueller")).then(console.log)
```

Both checks are automated: `tests/test_core.py::test_acceptance_vector` (Python) and `tests/test_gui_parity.py` (GUI code in Node; also compares whole output files byte by byte). After any change to processing logic in one implementation, make the same change in the other and run the parity tests.

## Coding Conventions

### Python (pseudonym.py)
- Python 3.8+ compatible
- Comments and CLI output in German (ASCII-safe: ae/oe/ue instead of umlauts). This applies to prose only. Column aliases are data: write them exactly as they appear in exports (`Prüfer`, not `Pruefer`), in code and in every doc table
- User-facing errors are `PseudoError` with a sentence a non-technical user can act on. Never call `sys.exit()` inside processing functions; `main(argv)` returns the exit code and keeps a batch running after one file fails
- A missing third-party package must never end in a traceback. `cryptography` is imported in a `try` at the top, `openpyxl` only where needed; `missing_packages()` / `package_hint()` report it before the secret prompt, with the install command for the running interpreter (`sys.executable`). `anonymize` and CSV-only runs work without the package they do not need
- Functions: `snake_case`
- CSV processing never re-serializes the file. `scan_csv()` returns the text span of every field; `process_csv()` replaces only the identity cells and copies everything else verbatim (encoding, BOM, quoting per cell, whitespace, line endings, metadata rows, blank and ragged rows). Do not reintroduce `csv.reader`/`csv.writer` or dict rows: they lose duplicate headers and normalize quoting
- XLSX/XLSM processing: uses openpyxl, preserves cell formatting. Read `ws.max_row`/`ws.max_column` once per sheet, never inside a loop (openpyxl recomputes them on every access). Includes `_fix_xlsx_drawings()` for repairing broken drawing references before loading. For `.xlsm` files, `process_xlsx` loads with `keep_vba=True` to preserve macros (CLI only; the browser GUI keeps values, number formats, formulas and column widths, but drops colors, fonts, borders and macros).

### HTML/JS (pseudonym_gui.html)
- Single self-contained HTML file — all CSS and JS inline
- No network access at all. SheetJS and JSZip are embedded as unmodified copies of the vendors' files, each in its own `<script id="lib-...">` block at the end of the file with `data-version` and `data-sha512`. Never edit these blocks by hand and never add a `<script src>`: use `python tools/gui_libs.py update`. `check` compares the embedded code with the vendor's file (SheetJS from cdn.sheetjs.com, because other CDNs only carry the vulnerable version 0.18.5; JSZip from cdnjs.cloudflare.com)
- A Content-Security-Policy `<meta>` blocks foreign scripts, all network connections, forms and foreign images. It names no foreign host; keep it that way
- Everything that comes from a file (headers, sheet names, cell values, file names) goes into the page through `esc()` only
- CSV parsing uses the built-in `scanCsv()` (same algorithm as `scan_csv()` in Python), not a CSV library
- XLSX: `processXlsx()` replaces cells in the loaded workbook; it does not rebuild sheets from arrays (that turned every date and number into text)
- The info popup table is generated from `COLUMN_ALIASES`; do not hand-write it
- Web Crypto API for all cryptographic operations (no polyfills)
- Vanilla JS, no framework
- CSS custom properties for dark/light theming
- localStorage for dark mode preference and processing history (never for secrets)

## Security Rules

- **Never commit data files** — they contain student PII. The `.gitignore` blocks `*.csv`, `*.tsv`, `*.xlsx`, `*.xlsm`, `*.xls` and `*.zip`.
- **Never open `.csv`, `.xlsx`, `.xlsm` or `.png` files in the project folder** — they can hold real student data. Create synthetic test data in a temporary folder outside the project.
- **Never store or log secrets** — the secret exists only in memory during processing. The CLI prompts for it without echo; `--secret` remains for scripts but puts the secret into the shell history, so docs and examples for real data must not recommend it
- **Never weaken crypto parameters** — no reducing PBKDF2 iterations, no switching to ECB mode, no removing IV
- **Never write an output file when nothing was processed** — a file without recognized columns, or a decrypt where no value could be decrypted (wrong secret), is an error, not a `_pseudo`/`_restored` copy of the input
- **Anonymize clears recognized columns only** — metadata rows, other columns and file names stay; the tools warn, and the docs must not promise anonymity
- The deterministic IV is an intentional trade-off: it enables consistent pseudonyms across files but means identical values produce identical ciphertext. This is acceptable for this use case.

## Common Tasks

### Adding a new column alias
1. Add alias to `COLUMN_ALIASES` in `pseudonym.py` (one spelling only; matching ignores case)
2. Add same alias to `COLUMN_ALIASES` in `pseudonym_gui.html` (the info popup is generated from it)
3. Update the tables in `ANLEITUNG_pseudonym.md`, `README.md`, `docs/column-reference.md` and in this file
4. Run `python -m pytest tests` — `tests/test_consistency.py` names every place where the alias is missing

### Adding a new identity column type
1. Add new key + aliases to `COLUMN_ALIASES` dict in both files
2. No other code changes needed — the column will be auto-detected and encrypted (add a label to `KIND_LABELS` in the GUI for the info popup)
3. Update all documentation files (see alias checklist above)

### Releasing a new version
1. **Check the embedded libraries first — required for every release:** run `python tools/gui_libs.py check`. If it reports a newer version of SheetJS or JSZip, embed it with `python tools/gui_libs.py update`, adjust the versions named in the docs (the tests list every place), run all tests, open the page in a browser, and name the update in the release notes. If an update is deliberately skipped, say why in the release notes.
2. The version number lives in three places: `__version__` in `pseudonym.py`, the header line in `pseudonym_gui.html`, and `docs/installation.md`. `tests/test_consistency.py` checks that they agree.
3. Attach `pseudonym.py` and `pseudonym_gui.html` to the GitHub release.

### Header Row Auto-Detection
Both implementations take the row with the most recognized columns among the first 20 rows (identity columns, `Name` and extra columns all count; ties: more filled cells, then the earlier row). Files with metadata rows before the header (e.g., MLW exports) are supported. Metadata rows are preserved unchanged in output — also when they contain a name.

### Separator Auto-Detection
Both implementations try `;`, `,` and tab and take the one whose header row has the most recognized columns. `--sep` (CLI) or the separator select (GUI, single CSV) overrides it.

### Modifying CSV format preservation
- `detect_file_encoding()`: detects encoding (UTF-8/UTF-16 LE/BE/Windows-1252) and BOM from raw bytes
- `scan_csv()` / `scanCsv()`: field spans; `csv_field()` / `csvField()`: a replaced field keeps its quotes and gets quotes only if the new value needs them
- Roundtrips must stay byte-identical. The only exceptions are the two UTF-8-with-BOM cases under "Encoding Support"; `tests/test_core.py` and `tests/test_gui_parity.py` hold the cases
