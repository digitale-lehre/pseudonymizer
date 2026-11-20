# Entwicklung

## Architektur

Der pseudonymizer besteht aus zwei unabhaengigen Implementierungen, die identische Kryptographie verwenden:

```
pseudonym.py            Python CLI (requires cryptography, openpyxl)
pseudonym_gui.html      Browser-GUI (Web Crypto API + SheetJS + JSZip via CDN, mit Pruefsumme)
```

Beide muessen **immer** die gleichen Ergebnisse fuer gleiche Eingaben liefern.


## Aufbau: Python CLI (`pseudonym.py`)

| Bereich | Funktionen |
|---|---|
| **Kryptographie** | `derive_key()`, `deterministic_iv()`, `encrypt_value()`, `try_decrypt()`, `decrypt_value()` |
| **Spalten-Erkennung** | `column_kind()`, `ColumnPlan`, `find_header_row()`, `cell_text()`, `split_edges()` |
| **Zellen** | `_Worker` (`cell()`, `name_cell()`, `check()`): eine Stelle fuer Verschluesseln, Entschluesseln und Anonymisieren |
| **CSV-Verarbeitung** | `detect_file_encoding()`, `scan_csv()`, `field_value()`, `csv_field()`, `detect_separator()`, `process_csv()` |
| **XLSX-Verarbeitung** | `_fix_xlsx_drawings()`, `process_xlsx()` |
| **Eingabe/Ausgabe** | `collect_input_files()`, `cleanup_temp_dirs()`, `make_output_path()`, `make_zip_name()`, `create_output_zip()`, `process_file()` |
| **CLI** | `main(argv)` gibt den Rueckgabecode zurueck und ist dadurch testbar |

**CSV ohne Neuaufbau:** `scan_csv()` liefert fuer jede Zelle Anfang und Ende im Text. `process_csv()` ersetzt nur die betroffenen Zellen und laesst den uebrigen Text unberuehrt. Deshalb ist der Roundtrip byte-identisch, und Sonderfaelle (gemischte Anfuehrungszeichen, Zeilenumbruch in einer Zelle, Leerzeilen) brauchen keinen eigenen Code. Derselbe Algorithmus steht als `scanCsv()` in der GUI.

**Fehler:** Meldungen fuer Anwender:innen sind `PseudoError`. Keine Funktion beendet das Programm selbst; `main()` faengt Fehler je Datei ab, damit ein Stapel weiterlaeuft.

**Konventionen:**
- Python 3.8+ kompatibel
- Kommentare und Ausgaben auf Deutsch (ASCII-safe: ae/oe/ue)
- Funktionen: `snake_case`


## Aufbau: Browser-GUI (`pseudonym_gui.html`)

Einzelne HTML-Datei mit eingebettetem CSS und JavaScript.

| Bereich | Beschreibung |
|---|---|
| **CSS** | Custom Properties fuer Dark/Light Mode, responsives Layout |
| **Kryptographie** | Web Crypto API: `createCipher()` mit `encrypt()`, `tryDecrypt()`, `decrypt()` |
| **Spalten-Erkennung** | `columnKind()`, `columnPlan()`, `findHeaderRow()`, `cellText()`, `splitEdges()` |
| **Zellen** | `createWorker()` (`cell()`, `nameCell()`, `check()`), Gegenstueck zu `_Worker` |
| **CSV** | `detectEncoding()`, `scanCsv()`, `fieldValue()`, `csvField()`, `detectSeparator()`, `processCsv()` |
| **XLSX** | `readWorkbook()`, `processXlsx()`: ersetzt Zellen in der geladenen Arbeitsmappe |
| **Datei-Handling** | `addFiles()`, `loadOne()`, `parseOneFile()`, `sheetView()`, `renderPreview()` |
| **Dateiliste** | `renderFileList()`, `selectFile()`, `removeFile()`, `clearFiles()`, `toggleFileList()` |
| **Verarbeitung** | `processFile()` — Schleife ueber `fileQueue`, Fehler je Datei, Fortschritt; `invalidateResults()` blendet veraltete Ergebnisse aus |
| **Download** | `buildDownload()`, `downloadResult()` — Einzeldatei direkt, Batch als ZIP via JSZip |
| **Dateiauswahl** | `renderFileSelector()` — Tabs (<=8) oder Dropdown (>8), `selectFileAndCompare()` |
| **UI** | Modus-Toggle, Dropzone, Dark Mode, Verlauf |

**Konventionen:**
- Alles in einer Datei, kein Build-Schritt
- Externe Bibliotheken nur mit fester Version, `integrity` (SHA-512) und `crossorigin="anonymous"`: JSZip von cdnjs.cloudflare.com, SheetJS von cdn.sheetjs.com (cdnjs fuehrt nur die veraltete Version 0.18.5 mit bekannten Schwachstellen)
- Content Security Policy im `<head>`: keine Netzverbindungen, keine Formulare, keine fremden Bilder. Wer eine weitere Quelle braucht, muss sie dort eintragen
- Alles, was aus Dateien stammt (Spaltennamen, Blattnamen, Zellwerte, Dateinamen), geht nur ueber `esc()` in die Seite
- Vanilla JS, kein Framework
- localStorage fuer Dark Mode und Verlauf (nie fuer Secrets)


## Testen

### Automatische Tests (pytest)

```bash
pip install -r requirements.txt pytest
python -m pytest tests -v
```

| Datei | Inhalt |
|---|---|
| `tests/test_core.py` | Abnahmewert, Spaltenerkennung, CSV (byte-identische Roundtrips, alle Kodierungen), XLSX, Anonymisieren |
| `tests/test_cli.py` | Kommandozeile: Stapel, Ordner, Platzhalter, ZIP, Secret-Abfrage, Fehlermeldungen, fehlende Python-Pakete |
| `tests/test_batch.py` | Aeltere Tests zu `process_file()`, ZIP-Ein-/Ausgabe, Name-Spalte, Windows-1252 |
| `tests/test_consistency.py` | Alias-Listen in CLI und GUI gleich, jeder Alias in der Doku, Versionsnummer, `integrity` an den Skripten |
| `tests/test_gui_parity.py` | Gleichlauf: Der JavaScript-Teil der GUI laeuft in Node und muss dieselben Bytes liefern wie die CLI |

Alle Testdaten sind erfunden. Echte Exportdateien gehoeren nicht in die Tests.

### Gleichlauf-Tests der GUI

`tests/test_gui_parity.py` braucht Node.js und die beiden Bibliotheken der GUI in einem Ordner ausserhalb des Projekts. Ohne sie werden diese Tests uebersprungen.

```bash
mkdir ~/pseudo-libs && cd ~/pseudo-libs
curl -O https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js
curl -O https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js
PSEUDO_GUI_LIBS=~/pseudo-libs python -m pytest tests/test_gui_parity.py -v
```

`tests/gui_harness.js` laedt die Bibliotheken nur, wenn ihre Pruefsumme zu den `integrity`-Angaben in `pseudonym_gui.html` passt.

Die Bedienung im Browser (Klicks, Drag & Drop, Download, Sicherheitsrichtlinie) pruefen diese Tests nicht. Nach Aenderungen an der Oberflaeche die Seite im Browser oeffnen und mit einer erfundenen Datei durchgehen.

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

1. `COLUMN_ALIASES` in `pseudonym.py` erweitern (jede Schreibweise nur einmal; Gross-/Kleinschreibung ist egal)
2. `COLUMN_ALIASES` in `pseudonym_gui.html` gleich erweitern (das Info-Popup entsteht daraus von selbst)
3. Tabellen in `docs/column-reference.md`, `ANLEITUNG_pseudonym.md`, `README.md` und `CLAUDE.md` aktualisieren
4. `python -m pytest tests` ausfuehren. `tests/test_consistency.py` meldet jede Stelle, an der der Alias fehlt

### Neuen Spaltentyp hinzufuegen

1. Neuen Key + Aliase in `COLUMN_ALIASES` in beiden Dateien hinzufuegen
2. Kein weiterer Code noetig — die Spalte wird automatisch erkannt und verschluesselt. Fuer das Info-Popup der GUI eine Bezeichnung in `KIND_LABELS` ergaenzen
3. Alle Dokumentationsdateien aktualisieren

### Version erhoehen

Die Versionsnummer steht an drei Stellen: `__version__` in `pseudonym.py`, die Kopfzeile in `pseudonym_gui.html` und `docs/installation.md`. `tests/test_consistency.py` prueft, dass sie gleich sind.

### Bibliothek der GUI aktualisieren

1. Neue Datei herunterladen und die Pruefsumme berechnen: `openssl dgst -sha512 -binary datei.js | openssl base64 -A`
2. `src` und `integrity` im `<script>`-Tag aendern
3. Gleichlauf-Tests mit der neuen Datei ausfuehren und die Seite im Browser pruefen

### Kryptographie aendern

**Vorsicht:** Jede Aenderung bricht die Kompatibilitaet mit bestehenden verschluesselten Dateien.

1. Aenderung in **beiden** Implementierungen durchfuehren
2. Cross-Implementation-Test durchfuehren
3. Migrationspfad fuer bestehende Dateien bereitstellen
4. Kryptographie-Dokumentation aktualisieren

Siehe [Kryptographie-Spezifikation](cryptography.md) fuer technische Details.


## Sicherheitsregeln

- **Nie** CSV-, TSV-, XLSX-, XLSM- oder ZIP-Dateien committen (enthalten PII). `.gitignore` blockiert diese.
- **Nie** echte Exportdateien fuer Tests oeffnen oder kopieren. Testdaten erfinden und ausserhalb des Projektordners ablegen
- **Nie** Secrets speichern oder loggen. Die CLI fragt verdeckt nach dem Secret; `--secret` steht im Verlauf der Konsole
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
  requirements.txt          Python-Abhaengigkeiten (getestete Versionen)
  .github/workflows/        Automatischer Testlauf auf GitHub
  tests/                    Automatische Tests (siehe oben)
    conftest.py             Raeumt entpackte ZIP-Inhalte nach jedem Test auf
    test_core.py, test_cli.py, test_batch.py, test_consistency.py, test_gui_parity.py
    gui_harness.js          Fuehrt den JavaScript-Teil der GUI in Node aus
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
