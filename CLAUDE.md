# CLAUDE.md — pseudonymizer

## Project Overview

Tool for pseudonymizing and de-pseudonymizing personal data (names, student IDs, email addresses, examiner names) in CSV and XLSX files. Used at MedUni Wien for handling student data in tertial assignment workflows.

Two implementations exist — a Python CLI (`pseudonym.py`) and a standalone browser GUI (`pseudonym_gui.html`). Both use identical cryptography and must always produce the same output for the same input and secret.

## Architecture

```
pseudonym.py          Python CLI (requires cryptography, openpyxl)
pseudonym_gui.html    Single-file browser app (zero dependencies, uses Web Crypto API + SheetJS + PapaParse via CDN)
ANLEITUNG_pseudonym.md  German-language user documentation
README.md             Project overview
```

## Cryptographic Specification (MUST stay identical in both implementations)

- **Key derivation**: PBKDF2-HMAC-SHA256, 100,000 iterations, salt = `MedUniWien-Pseudo-Salt` (UTF-8 encoded) → 256-bit key
- **Deterministic IV**: HMAC-SHA256(key, plaintext)[:16]
- **Encryption**: AES-256-CBC with PKCS7 padding
- **Output format**: URL-safe Base64 (no trailing `=`) of `IV || ciphertext`
- **CRITICAL**: Any change to these parameters breaks compatibility between the two implementations and makes existing encrypted files unreadable. Never change salt, iteration count, IV derivation, or encoding without updating BOTH implementations and providing a migration path.

## Column Recognition (case-insensitive, must match in both implementations)

| Canonical key | Aliases |
|--------------|---------|
| familienname | FAMILIENNAME, Familienname, Zuname, Nachname, FAMILY_NAME_OF_STUDENT, Last Name, LastName |
| vorname | VORNAME, Vorname, FirstName, FIRST_NAME_OF_STUDENT, First Name |
| matnr | MATRIKELNUMMER, Matrikelnummer, Matnr, REGISTRATION_NUMBER, StudentID, Matrikel |
| email | EMAIL_ADDRESS, E-Mail, Email, Mail, EMAIL, E_MAIL, E-Mail des Teilnehmers, Attendee Email |
| pruefer | Examiner, Pruefer, Prüfer |
| anzeigename | Anzeigename, Display Name, DisplayName |

`NAME` column: auto-detected as composite of familienname + vorname (checked against first data row). Note: `Anzeigename`/`Display Name` is NOT a composite — it is encrypted independently (Webex display names may differ from Vorname + Nachname).

When adding new aliases, update `COLUMN_ALIASES` in `pseudonym.py` AND the `COLUMN_ALIASES` object in `pseudonym_gui.html`.

## Build & Test Commands

```bash
# Install Python dependencies
pip install cryptography openpyxl

# Encrypt CSV
python pseudonym.py encrypt input.csv --secret "test" --sep ","

# Encrypt XLSX
python pseudonym.py encrypt input.xlsx --secret "test"

# Decrypt
python pseudonym.py decrypt input_pseudo.csv --secret "test"

# Roundtrip verification (output should be byte-identical to input for CSV)
python pseudonym.py encrypt input.csv --secret "test"
python pseudonym.py decrypt input_pseudo.csv --secret "test"
diff input.csv input_pseudo_restored.csv
```

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

The HTML GUI must produce the same token for the same input and secret.

## Coding Conventions

### Python (pseudonym.py)
- Python 3.8+ compatible
- Comments and CLI output in German (ASCII-safe: ae/oe/ue instead of umlauts)
- Functions: `snake_case`
- CSV processing preserves original BOM, quoting style (QUOTE_ALL vs QUOTE_MINIMAL), and line endings (CRLF vs LF) for byte-identical roundtrips
- XLSX processing: uses openpyxl, preserves cell formatting. Includes `_fix_xlsx_drawings()` for repairing broken drawing references before loading

### HTML/JS (pseudonym_gui.html)
- Single self-contained HTML file — all CSS and JS inline
- External libraries via CDN only (cdnjs.cloudflare.com): PapaParse, SheetJS
- Web Crypto API for all cryptographic operations (no polyfills)
- Vanilla JS, no framework
- CSS custom properties for dark/light theming
- localStorage for dark mode preference and processing history (never for secrets)

## Security Rules

- **Never commit CSV or XLSX data files** — they contain student PII. The `.gitignore` blocks `*.csv` and `*.xlsx`.
- **Never store or log secrets** — the secret exists only in memory during processing
- **Never weaken crypto parameters** — no reducing PBKDF2 iterations, no switching to ECB mode, no removing IV
- The deterministic IV is an intentional trade-off: it enables consistent pseudonyms across files but means identical values produce identical ciphertext. This is acceptable for this use case.

## Common Tasks

### Adding a new column alias
1. Add alias to `COLUMN_ALIASES` in `pseudonym.py`
2. Add same alias to `COLUMN_ALIASES` in `pseudonym_gui.html`
3. Update the info popup table in `pseudonym_gui.html`
4. Update the table in `ANLEITUNG_pseudonym.md`
5. Update the table in `README.md`

### Adding a new identity column type
1. Add new key + aliases to `COLUMN_ALIASES` dict in both files
2. No other code changes needed — the column will be auto-detected and encrypted
3. Update all documentation files

### Modifying CSV format preservation
- `detect_quoting()`: checks if original uses QUOTE_ALL
- `detect_encoding()`: detects BOM and line endings
- Both must be preserved for byte-identical roundtrips
