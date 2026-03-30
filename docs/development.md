# Entwicklung

## Architektur

Der pseudonymizer besteht aus zwei unabhaengigen Implementierungen, die identische Kryptographie verwenden:

```
pseudonym.py            Python CLI (requires cryptography, openpyxl)
pseudonym_gui.html      Browser-GUI (Web Crypto API + SheetJS + PapaParse via CDN)
```

Beide muessen **immer** die gleichen Ergebnisse fuer gleiche Eingaben liefern.


## Aufbau: Python CLI (`pseudonym.py`)

| Bereich | Funktionen |
|---|---|
| **Kryptographie** | `derive_key()`, `deterministic_iv()`, `encrypt_value()`, `decrypt_value()` |
| **Spalten-Erkennung** | `find_identity_cols()`, `find_name_col()`, `find_header_row()` |
| **CSV-Verarbeitung** | `detect_file_encoding()`, `process_csv()` |
| **XLSX-Verarbeitung** | `_fix_xlsx_drawings()`, `process_xlsx()` |
| **Batch** | `process_file()`, `collect_input_files()`, `make_output_path()`, `create_output_zip()` |
| **CLI** | `argparse`-Setup im `__main__`-Block (unterstuetzt `nargs="+"`, `--output-dir`, `--zip`) |

**Konventionen:**
- Python 3.8+ kompatibel
- Kommentare und Ausgaben auf Deutsch (ASCII-safe: ae/oe/ue)
- Funktionen: `snake_case`


## Aufbau: Browser-GUI (`pseudonym_gui.html`)

Einzelne HTML-Datei mit eingebettetem CSS und JavaScript.

| Bereich | Beschreibung |
|---|---|
| **CSS** | Custom Properties fuer Dark/Light Mode, responsives Layout |
| **Kryptographie** | Web Crypto API: `deriveKey()`, `hmacSha256()`, `encryptValue()`, `decryptValue()` |
| **Datei-Handling** | `addFiles()`, `parseOneFile()`, `renderPreview()` |
| **Dateiliste** | `renderFileList()`, `selectFile()`, `removeFile()`, `clearFiles()`, `toggleFileList()` |
| **Verarbeitung** | `processFile()` — async, Batch-Schleife ueber `fileQueue`, Fortschrittsbalken + Text |
| **Download** | `downloadResult()` — Einzeldatei direkt, Batch als ZIP via JSZip |
| **Dateiauswahl** | `renderFileSelector()` — Tabs (<=8) oder Dropdown (>8), `selectFileAndCompare()` |
| **UI** | Modus-Toggle, Dropzone, Dark Mode, Verlauf |

**Konventionen:**
- Alles in einer Datei, kein Build-Schritt
- Externe Bibliotheken nur via CDN (cdnjs.cloudflare.com): PapaParse, SheetJS, JSZip
- Vanilla JS, kein Framework
- localStorage fuer Dark Mode und Verlauf (nie fuer Secrets)


## Testen

### Automatische Tests (pytest)

```bash
python -m pytest tests/test_batch.py -v
```

Testet: `process_file()`, `make_output_path()`, `collect_input_files()`, `create_output_zip()`, Roundtrip.

### Roundtrip-Test (Python)

```bash
python pseudonym.py encrypt testdatei.csv --secret "test"
python pseudonym.py decrypt testdatei_pseudo.csv --secret "test"
diff testdatei.csv testdatei_pseudo_restored.csv
# Keine Ausgabe = byte-identisch
```

### Cross-Implementation-Test

Beide Implementierungen muessen fuer gleiche Eingaben identische Pseudonyme erzeugen:

```python
from pseudonym import derive_key, encrypt_value
key = derive_key("testSecret123")
result = encrypt_value(key, "Mueller")
assert result == "a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc"
```

Die Browser-GUI muss denselben Token fuer "Mueller" mit Secret "testSecret123" erzeugen.


## Haeufige Aenderungen

### Neuen Spalten-Alias hinzufuegen

1. `COLUMN_ALIASES` in `pseudonym.py` erweitern
2. `COLUMN_ALIASES` in `pseudonym_gui.html` erweitern
3. Info-Popup-Tabelle in `pseudonym_gui.html` aktualisieren
4. Tabelle in `docs/column-reference.md` aktualisieren
5. Tabelle in `ANLEITUNG_pseudonym.md` aktualisieren
6. Tabelle in `README.md` aktualisieren

### Neuen Spaltentyp hinzufuegen

1. Neuen Key + Aliase in `COLUMN_ALIASES` in beiden Dateien hinzufuegen
2. Kein weiterer Code noetig — die Spalte wird automatisch erkannt und verschluesselt
3. Alle Dokumentationsdateien aktualisieren

### Kryptographie aendern

**Vorsicht:** Jede Aenderung bricht die Kompatibilitaet mit bestehenden verschluesselten Dateien.

1. Aenderung in **beiden** Implementierungen durchfuehren
2. Cross-Implementation-Test durchfuehren
3. Migrationspfad fuer bestehende Dateien bereitstellen
4. Kryptographie-Dokumentation aktualisieren

Siehe [Kryptographie-Spezifikation](cryptography.md) fuer technische Details.


## Sicherheitsregeln

- **Nie** CSV- oder XLSX-Dateien committen (enthalten PII). `.gitignore` blockiert diese.
- **Nie** Secrets speichern oder loggen
- **Nie** Krypto-Parameter abschwaeen (Iterationen, Modus, IV-Ableitung)
- Die deterministische IV ist ein bewusster Trade-off fuer konsistente Pseudonyme


## Projektstruktur

```
pseudonymizer/
  pseudonym.py              Python CLI
  pseudonym_gui.html        Browser-GUI
  README.md                 Projekt-Uebersicht
  ANLEITUNG_pseudonym.md    Benutzer-Anleitung
  CLAUDE.md                 Entwickler-Kontext (fuer AI-Assistenten)
  .gitignore                Ignoriert Datendateien und Build-Artefakte
  tests/                    Automatische Tests
    test_batch.py           pytest: Batch-Funktionen (process_file, ZIP I/O etc.)
  docs/                     Wiki-Dokumentation
    index.md                Wiki-Startseite
    installation.md         Installationsanleitung
    usage-cli.md            CLI-Referenz
    usage-gui.md            GUI-Anleitung
    cryptography.md         Kryptographie-Spezifikation
    column-reference.md     Spalten-Referenz
    troubleshooting.md      Fehlerbehebung
    development.md          Diese Seite
```
