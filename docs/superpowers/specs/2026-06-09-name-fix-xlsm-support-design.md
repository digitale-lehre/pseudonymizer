# Design: "Name"-Spalten-Fix + `.xlsm`-Support

**Datum:** 2026-06-09
**Status:** Genehmigt (bereit für Implementierungsplan)
**Betrifft:** `pseudonym.py`, `pseudonym_gui.html`, `tests/test_batch.py`, `.gitignore`, Doku

## Problem / Motivation

Zwei voneinander unabhängige Anliegen:

1. **Bug:** Eine Spalte mit dem Header `Name` wird in beiden Implementierungen
   **nur dann** pseudonymisiert, wenn sie als *Composite* aus separaten
   `Vorname`- **und** `Familienname`-Spalten erkannt wird (der Zellwert der
   ersten Datenzeile muss exakt `"Vor Fam"` oder `"Fam Vor"` sein). Fehlt eine
   dieser beiden Spalten oder scheitert der Composite-Abgleich (Titel, zweiter
   Vorname, `"Mueller, Hans"`, leere erste Zeile …), wird die `Name`-Spalte zwar
   von `find_name_col` gefunden, aber **nie verschlüsselt** — PII leakt.
   `find_name_col` ist zudem komplett getrennt von `find_identity_cols`, sodass
   eine alleinstehende `Name`-Spalte nie in die Verschlüsselungsschleife
   gelangt.

   **Konkreter Fall des Nutzers:** Datei hat `Name` (faktisch der Nachname) +
   `Vorname`, aber keine als `Familienname`/`Nachname` benannte Spalte. `Name`
   ist kein `familienname`-Alias → Composite-Check scheitert → `Name` bleibt im
   Klartext. Der Fix muss **robust** für alle Varianten sein.

2. **Feature:** `.xlsm` (makro-aktiviertes Excel) wird aktuell abgelehnt
   (`Unbekanntes Dateiformat`). Es soll als Eingabe-/Ausgabeformat unterstützt
   werden.

## Entscheidungen (vom Nutzer bestätigt)

- **Name-Fix:** Wenn `Name` **nicht** als Composite erkannt wird, wird der
  **ganze Zellwert als ein Token** verschlüsselt (wie eine `Nachname`-Spalte).
  Begründung: Die Krypto ist deterministisch auf dem Klartext, nicht auf der
  Spalte — `transform("Mueller")` liefert immer denselben Token, egal in
  welcher Spalte. Damit bleibt das Ergebnis konsistent **und** reversibel, und
  alle drei Fälle (Einzelname, Nachname+Vorname, echtes Composite) werden
  robust abgedeckt. Das echte Composite-Verhalten bleibt unverändert.
- **`.xlsm`:** Variante **"Beide Tools, Makros egal"**. CLI und GUI akzeptieren
  `.xlsm`. Python erhält Makros + Formatierung automatisch (`keep_vba`). Die
  Browser-GUI verarbeitet nur die Daten und verliert Formatierung/Makros (wie
  schon heute bei `.xlsx`) — bewusst akzeptiert. Ausgabe behält die
  `.xlsm`-Endung.

## Nicht-Ziele (YAGNI)

- Keine VBA-Makro-Erhaltung in der GUI (kein `vbaraw`-Carry-over).
- Keine Formatierungs-Erhaltung in der GUI (Status quo bleibt).
- `Name` wird **nicht** als neuer Alias in `COLUMN_ALIASES` aufgenommen
  (würde das Composite-Verhalten brechen und Vollnamen falsch klassifizieren).
- Keine Heuristik zum Aufsplitten freier Namensfelder in Vor-/Nachname.

## Kryptografie

**Unverändert.** Keine Änderung an Salt, Iterationen, IV-Ableitung, AES-Modus
oder Encoding. Für denselben Klartextwert erzeugen CLI und GUI denselben Token —
Parität bleibt erhalten. `.xlsm` ändert nur die Datei-I/O, nicht die Krypto.

## Komponente 1 — Name-Fix

### Gemeinsame Regel (alle drei Stellen identisch)
1. `Name`-Spalte ermitteln (`find_name_col` / `findNameCol`) — unverändert.
2. Composite-Erkennung (`Vorname`+`Familienname` vorhanden und Wert passt) —
   unverändert.
3. **Neu:** Ist eine `Name`-Spalte vorhanden, aber **nicht** Composite, und ihr
   Spaltenindex/-name ist **nicht** bereits durch eine andere Identitätsspalte
   belegt → die `Name`-Spalte als reguläre Identitätsspalte (synthetischer Key
   `_name`) zur Verschlüsselungsschleife hinzufügen. Der ganze Zellwert wird
   über `transform` verschlüsselt.
4. Composite-Fall: bestehendes Rekomponieren aus verschlüsselten Teilen bleibt.

Der Guard "Index nicht bereits belegt" verhindert Doppelverschlüsselung, falls
eine andere Spalte denselben Index hätte (defensive Absicherung).

### 1a. `pseudonym.py` · `process_csv` (~Z. 278–321)
Nach der Composite-Bestimmung (`name_is_composite`): wenn `name_col` gesetzt,
`not name_is_composite` und `name_col not in id_cols.values()` →
`id_cols["_name"] = name_col`. Die bestehende Schleife (Z. 310–313)
verschlüsselt es dann automatisch; der Composite-Block (Z. 314–320) wird
übersprungen, weil `name_is_composite` False ist. `cols_info` (Z. 329) listet es
automatisch mit (iteriert über `id_cols.values()`).

### 1b. `pseudonym.py` · `process_xlsx` (~Z. 477–511)
Analog. Da die Verschlüsselungsschleife über `col_indices` läuft und das Reporting
über `id_cols`, bei nicht-Composite **beides** ergänzen:
`id_cols["_name"] = name_col_name` **und** `col_indices["_name"] = name_col_idx`.
Composite-Block (Z. 505–511) wird übersprungen.

### 1c. `pseudonym_gui.html` (~Z. 828–852)
Analog. Nach `nameIsComposite`-Bestimmung: wenn `nameColIdx >= 0`,
`!nameIsComposite` und `nameColIdx` nicht in `Object.values(colIndices)` →
`colIndices["_name"] = nameColIdx`. Die bestehende Schleife (Z. 845–848)
verschlüsselt es; `colInfo` (Z. 839) ggf. anpassen, damit die Spalte im Log
erscheint.

## Komponente 2 — `.xlsm`-Support

### 2a. `pseudonym.py`
- **Dispatch** (`process_file`, Z. 611): `if ext == ".xlsx":` →
  `if ext in (".xlsx", ".xlsm"):`.
- **Laden** (`process_xlsx`, Z. 415): `is_xlsm = Path(input_path).suffix.lower()
  == ".xlsm"`; `wb = load_workbook(fixed_path, keep_vba=is_xlsm)`. `keep_vba`
  nur bei `.xlsm`, um `.xlsx`-Verhalten nicht zu verändern.
- **Temp-Suffix** (`_fix_xlsx_drawings`, Z. 386):
  `tempfile.mkstemp(suffix=Path(input_path).suffix)` statt fix `".xlsx"`, damit
  openpyxl den Container-Typ korrekt erkennt. (Die Reparatur re-zippt ohnehin
  alle Member inkl. `vbaProject.bin`, Makros bleiben erhalten.)
- **Batch/ZIP** (`collect_input_files`, Z. 552–553): `.xlsm` zu `SUPPORTED`
  **und** `ZIP_EXTRACT` hinzufügen.
- **Fehlermeldung** (Z. 616) + **Help-/Beschreibungstexte** (Z. 4, 629, 638,
  660): `.xlsm` als unterstütztes Format ergänzen.

### 2b. `pseudonym_gui.html`
- **`accept`-Attribut** (Z. 222): `.xlsm` ergänzen.
- **Dateityp-Erkennung** (Z. 543 ZIP-Member, Z. 555 Direktupload):
  `file.name.match(/\.xlsx$/i)` → `/\.(xlsx|xlsm)$/i`, beide → Typ `'xlsx'`.
  (Sonst fällt `.xlsm` fälschlich in den CSV-Zweig.)
- **Schreiben** (Z. 868–873): `bookType` und Ausgabe-Endung aus der
  Eingabe-Endung ableiten:
  ```js
  const isXlsm = /\.xlsm$/i.test(fq.name);
  const wbout = XLSX.write(wb, { bookType: isXlsm ? 'xlsm' : 'xlsx', type: 'array' });
  const ext = isXlsm ? '.xlsm' : '.xlsx';
  outName = fq.name.replace(/\.(xlsx|xlsm)$/i, suffix + ext);
  ```
  Blob-MIME für `.xlsm`:
  `application/vnd.ms-excel.sheet.macroEnabled.12` (für Konsistenz; Browser
  ignorieren den Typ beim Download meist).
- **Lesen** (Z. 508): `XLSX.read(fobj.raw, { type: 'array' })` — unverändert,
  erkennt `.xlsm` automatisch. Kein `bookVBA` (Makros egal).

## Komponente 3 — Sicherheit (`.gitignore`)
`*.xlsm` ergänzen. `*.xls` matcht `.xlsm` **nicht** (exakte Endung), daher würden
sonst `.xlsm`-Daten mit PII committet werden können.

## Komponente 4 — Tests (`tests/test_batch.py`)

Neue pytest-Tests (CLI-Seite):
1. **Standalone `Name`:** CSV mit Spalten `Name` + `Vorname` (kein
   `Familienname`). Nach `encrypt` ist `Name` ≠ Klartext und verschlüsselt;
   `decrypt`-Roundtrip stellt den Originalwert exakt wieder her.
2. **`Name` neben getrennten Spalten, Composite scheitert:** `Vorname` +
   `Familienname` + `Name`, wobei `Name` z. B. einen Titel enthält → `Name` wird
   trotzdem (als Ganzwert) verschlüsselt; Roundtrip korrekt.
3. **Echtes Composite bleibt:** Regressionstest, dass der Composite-Fall
   unverändert rekomponiert.
4. **`.xlsm`-Roundtrip:** `.xlsm` mit Identitätsspalten + einer einfachen
   VBA-Komponente; nach `encrypt`/`decrypt` sind die Werte korrekt **und** die
   Makros (`vbaProject.bin`) sind im Output noch vorhanden (`keep_vba`).
5. **`.xlsm` im Dispatch/Batch:** `process_file` akzeptiert `.xlsm`;
   `collect_input_files` sammelt `.xlsm` (auch aus ZIP).

GUI: manuelle Browser-Verifikation (kein Test-Harness) — `.xlsm` hochladen,
verschlüsseln, herunterladen, in Excel öffnen; `Name`-Spalte prüfen.

## Komponente 5 — Cross-Implementation-Verifikation
Nach Implementierung bestätigen, dass CLI und GUI für denselben `Name`-Wert
denselben Token erzeugen (gemäß CLAUDE.md). Bekannter Vektor:
`encrypt_value(derive_key("testSecret123"), "Mueller") ==
"a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc"`.

## Komponente 6 — Doku
- `README.md`: `.xlsm` als unterstütztes Format; `Name`-Verhalten präzisieren.
- `ANLEITUNG_pseudonym.md`: dito.
- `docs/column-reference.md`: `Name`-Verhalten (Composite **oder** Ganzwert).
- `pseudonym_gui.html` Info-Popup (Z. 259): Beschreibung der `Name`-Zeile
  aktualisieren ("Composite aus Vorname+Familienname **oder** ganzer Wert").
- `CLAUDE.md`: `.xlsm` in Architektur-/Format-/Build-Abschnitten ergänzen.
- **Versions-Bump → v0.6.0** bei Finalisierung (neues Feature + Bugfix).

## Reihenfolge der Umsetzung
1. Name-Fix in `pseudonym.py` (CSV + XLSX) + Tests → verifizieren.
2. Name-Fix in `pseudonym_gui.html` → Cross-Impl-Token prüfen.
3. `.xlsm` in `pseudonym.py` (Dispatch, keep_vba, collect, Temp-Suffix, Texte) +
   Tests.
4. `.xlsm` in `pseudonym_gui.html`.
5. `.gitignore`.
6. Doku + Versions-Bump.
