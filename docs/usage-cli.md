# CLI Referenz

## Syntax

```
python pseudonym.py {encrypt|decrypt} DATEI --secret SECRET [--output PFAD] [--sep ZEICHEN]
```

## Argumente

| Argument | Pflicht | Beschreibung |
|---|---|---|
| `encrypt` / `decrypt` | Ja | `encrypt` = pseudonymisieren, `decrypt` = zurueckfuehren |
| `DATEI` | Ja | Pfad zur CSV-, TSV-, TXT- oder XLSX-Datei |
| `--secret SECRET` | Ja | Geheimer Schluessel (beliebiger String) |
| `--output PFAD`, `-o` | Nein | Ausgabepfad (Standard: `<name>_pseudo.<ext>` bzw. `<name>_restored.<ext>`) |
| `--sep ZEICHEN`, `-s` | Nein | CSV-Trennzeichen (Standard: Komma). Wird bei XLSX ignoriert. |
| `--version` | Nein | Versionsnummer anzeigen |
| `--help`, `-h` | Nein | Hilfe anzeigen |


## Beispiele

### CSV verschluesseln

```bash
python pseudonym.py encrypt studenten.csv --secret "MeinSecret"
```
Erzeugt: `studenten_pseudo.csv`

### CSV entschluesseln

```bash
python pseudonym.py decrypt studenten_pseudo.csv --secret "MeinSecret"
```
Erzeugt: `studenten_pseudo_restored.csv`

### XLSX verschluesseln

```bash
python pseudonym.py encrypt zuteilung.xlsx --secret "MeinSecret"
```
Erzeugt: `zuteilung_pseudo.xlsx` — alle Sheets werden verarbeitet, Formatierung bleibt erhalten.

### XLSX entschluesseln

```bash
python pseudonym.py decrypt zuteilung_pseudo.xlsx --secret "MeinSecret"
```
Erzeugt: `zuteilung_pseudo_restored.xlsx`

### Semikolon-getrennte CSV

```bash
python pseudonym.py encrypt export.csv --secret "MeinSecret" --sep ";"
```

### Eigener Ausgabepfad

```bash
python pseudonym.py encrypt eingabe.csv --secret "MeinSecret" --output /pfad/zu/ausgabe.csv
```

### Roundtrip-Verifikation

```bash
python pseudonym.py encrypt original.csv --secret "test"
python pseudonym.py decrypt original_pseudo.csv --secret "test"
diff original.csv original_pseudo_restored.csv
# Keine Ausgabe = byte-identisch
```


## Unterstuetzte Dateiformate

| Endung | Format | Trennzeichen anpassbar |
|---|---|---|
| `.csv` | Komma-separiert (Standard) | Ja, via `--sep` |
| `.tsv` | Tab-separiert | Ja, via `--sep` |
| `.txt` | Text (beliebiges Trennzeichen) | Ja, via `--sep` |
| `.xlsx` | Excel-Datei | Nein (kein Trennzeichen noetig) |


## Ausgabeformat

### CSV-Formaterhaltung

Das Tool erhaelt das Format der Originaldatei:

- **BOM (Byte Order Mark):** UTF-8 BOM wird beibehalten, wenn vorhanden
- **Quoting-Stil:** `QUOTE_ALL` (alle Felder in Anfuehrungszeichen) oder `QUOTE_MINIMAL` wird erkannt und beibehalten
- **Zeilenumbrueche:** CRLF (Windows) oder LF (Unix) wird beibehalten

Ein Encrypt-Decrypt-Roundtrip liefert eine **byte-identische** Datei.

### XLSX-Formaterhaltung

- Zellformatierung (Schriftart, Farben, Rahmen)
- Bedingte Formatierung
- Styles und Zahlenformate
- Alle Sheets (Sheets ohne Identitaetsspalten werden uebersprungen)


## Konsolenausgabe

Nach der Verarbeitung zeigt das Tool eine Zusammenfassung:

```
Pseudonymisierung abgeschlossen.
  Eingabe:    studenten.csv (150 Zeilen)
  Ausgabe:    studenten_pseudo.csv
  Spalten:    FAMILIENNAME, VORNAME, MATRIKELNUMMER, EMAIL + NAME
  Verfahren:  AES-256-CBC (deterministisch, PBKDF2)

  Zum Zurueckfuehren:
  python pseudonym.py decrypt studenten_pseudo.csv --secret <IhrSecret>
```

Bei XLSX zusaetzlich pro Sheet:

```
  Sheets:     2 verarbeitet, 450 Zellen
    + Sheet1 (FAMILIENNAME, VORNAME, MATRIKELNUMMER: 300 Zellen)
    + Pruefer (Examiner: 150 Zellen)
  Uebersprungen: 1
    - Legende (keine Identitaetsspalten erkannt)
```


## Naechste Schritte

- [Spalten-Referenz](column-reference.md) — welche Spalten erkannt werden
- [Troubleshooting](troubleshooting.md) — bei Problemen
