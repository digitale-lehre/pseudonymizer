# Anleitung: pseudonymizer

## Was macht das Tool?

Der pseudonymizer pseudonymisiert und de-pseudonymisiert personenbezogene Daten in CSV- und XLSX-Dateien. Personenbezogene Spalten (Familienname, Vorname, Matrikelnummer, E-Mail, Pruefer) werden durch verschluesselte Werte ersetzt, die nur mit dem richtigen Secret zurueckgefuehrt werden koennen.

**Verfahren:** AES-256-CBC (symmetrische Verschluesselung, deterministisch mit PBKDF2-Schluesselableitung). Es wird keine separate Key-Datei benoetigt — derselbe Secret verschluesselt und entschluesselt.

**Zwei Varianten:** Es gibt eine Python-CLI (`pseudonym.py`) und eine Browser-GUI (`pseudonym_gui.html`). Beide sind kryptografisch kompatibel.


## Variante 1: Browser-GUI (empfohlen fuer Einsteiger)

Kein Install noetig. Einfach `pseudonym_gui.html` im Browser oeffnen (Doppelklick).

1. **Datei waehlen:** CSV oder XLSX per Drag & Drop oder Dateiauswahl laden
2. **Secret eingeben:** Beliebiges Passwort (muss zum Entschluesseln identisch sein)
3. **Modus waehlen:** "Verschluesseln" oder "Entschluesseln"
4. **Starten:** Ergebnis wird zum Download angeboten

Alle Daten werden **lokal im Browser** verarbeitet — nichts wird hochgeladen oder uebertragen.

Detaillierte Anleitung: [docs/usage-gui.md](docs/usage-gui.md)


## Variante 2: Python CLI

### Voraussetzungen

Python 3.8+ und folgende Pakete:

```bash
pip install cryptography openpyxl
```

`cryptography` wird fuer die AES-Verschluesselung benoetigt, `openpyxl` fuer die XLSX-Verarbeitung.


### CSV pseudonymisieren

```bash
python pseudonym.py encrypt eingabe.csv --secret "MeinGeheimesPasswort"
```

Erzeugt `eingabe_pseudo.csv` im selben Ordner.

### CSV de-pseudonymisieren

```bash
python pseudonym.py decrypt eingabe_pseudo.csv --secret "MeinGeheimesPasswort"
```

Erzeugt `eingabe_pseudo_restored.csv`. Der Secret muss identisch sein.

### XLSX pseudonymisieren

```bash
python pseudonym.py encrypt eingabe.xlsx --secret "MeinGeheimesPasswort"
```

Erzeugt `eingabe_pseudo.xlsx`. Alle Sheets mit Identitaetsspalten werden verarbeitet. Formatierung und Styles bleiben erhalten.

### XLSX de-pseudonymisieren

```bash
python pseudonym.py decrypt eingabe_pseudo.xlsx --secret "MeinGeheimesPasswort"
```

Erzeugt `eingabe_pseudo_restored.xlsx`.

### Eigenen Ausgabepfad angeben

```bash
python pseudonym.py encrypt eingabe.csv --secret "MeinGeheimesPasswort" --output ausgabe.csv
```

### Semikolon-getrennte CSV

```bash
python pseudonym.py encrypt eingabe.csv --secret "MeinGeheimesPasswort" --sep ";"
```


## Unterstuetzte Spalten

Das Tool erkennt automatisch verschiedene Schreibweisen der Identitaetsspalten (case-insensitive):

| Spaltentyp | Erkannte Spaltennamen |
|---|---|
| Familienname | `FAMILIENNAME`, `Familienname`, `Zuname`, `Nachname`, `FAMILY_NAME_OF_STUDENT`, `Last Name`, `LastName` |
| Vorname | `VORNAME`, `Vorname`, `FirstName`, `FIRST_NAME_OF_STUDENT`, `First Name` |
| Matrikelnummer | `MATRIKELNUMMER`, `Matrikelnummer`, `Matnr`, `REGISTRATION_NUMBER`, `StudentID`, `Matrikel` |
| E-Mail | `EMAIL_ADDRESS`, `E-Mail`, `Email`, `Mail`, `E_MAIL` |
| Pruefer/Examiner | `Examiner`, `Pruefer`, `Pruefer`, `EXAMINER` |
| Name (optional) | `NAME` — wird automatisch aus Familienname + Vorname zusammengesetzt, falls erkannt |

Es muessen nicht alle Spalten vorhanden sein. Das Tool verschluesselt nur die gefundenen Identitaetsspalten. Alle anderen Spalten bleiben unveraendert.

Vollstaendige Spalten-Referenz: [docs/column-reference.md](docs/column-reference.md)


## NAME-Spalte

Falls eine Spalte `NAME` existiert und deren Inhalt der Kombination aus `FAMILIENNAME VORNAME` entspricht (oder umgekehrt), wird diese automatisch aus den verschluesselten Einzelwerten zusammengesetzt. So bleibt die Konsistenz erhalten.


## Bekannte XLSX-Probleme

Falls eine XLSX-Datei fehlerhafte Zeichnungsreferenzen enthaelt (z.B. `drawing1.xml` fehlt im Archiv), repariert das Tool diese automatisch vor der Verarbeitung. Eine entsprechende Meldung wird ausgegeben.


## Wichtige Hinweise

- **Secret sicher aufbewahren:** Ohne den exakten Secret koennen die Daten nicht zurueckgefuehrt werden. Es gibt keine Wiederherstellungsmoeglichkeit.
- **Deterministisch:** Gleicher Secret + gleiche Daten = gleiches Pseudonym. Das ermoeglicht die Zuordnung ueber mehrere Dateien hinweg, solange derselbe Secret verwendet wird.
- **CSV-Formaterhaltung:** BOM (Byte Order Mark), Quoting-Stil und Zeilenumbrueche der Originaldatei werden beibehalten. Ein Encrypt-Decrypt-Roundtrip liefert eine byte-identische Datei.
- **XLSX-Formaterhaltung:** Zellformatierung, bedingte Formatierung und Styles bleiben erhalten. Alle Sheets werden verarbeitet (Sheets ohne Identitaetsspalten werden uebersprungen).
- **Kompatibilitaet:** Python CLI und Browser-GUI erzeugen identische Pseudonyme fuer gleiche Eingaben mit gleichem Secret.


## Beispiel-Workflow (MedCampus-Export)

```bash
# 1. MedCampus-Export pseudonymisieren
python pseudonym.py encrypt L0106_26SPavelka20260216.csv --secret "SoSe2026-Geheim" --sep ";"

# 2. Pseudonymisierte Datei weitergeben / analysieren
#    (Pseudonyme sind URL-sichere Base64-Strings)

# 3. Spaeter: Original wiederherstellen
python pseudonym.py decrypt L0106_26SPavelka20260216_pseudo.csv --secret "SoSe2026-Geheim" --sep ";"
```

Fuer XLSX-Dateien (z.B. Tertial-Zuteilungen):

```bash
python pseudonym.py encrypt tp-jahr5-2026_SoSe_0.xlsx --secret "SoSe2026-Geheim"
python pseudonym.py decrypt tp-jahr5-2026_SoSe_0_pseudo.xlsx --secret "SoSe2026-Geheim"
```


## Vollstaendige Optionen

```
python pseudonym.py [-h] [--version] {encrypt,decrypt} input --secret SECRET [--output OUTPUT] [--sep SEP]

Argumente:
  {encrypt,decrypt}   encrypt = pseudonymisieren, decrypt = zurueckfuehren
  input               Pfad zur CSV- oder XLSX-Datei
  --secret SECRET     Geheimer Schluessel (beliebiger String)
  --output, -o        Ausgabepfad (Standard: <name>_pseudo.<ext> / <name>_restored.<ext>)
  --sep, -s           CSV-Trennzeichen (Standard: Komma; wird bei XLSX ignoriert)
  --version           Versionsnummer anzeigen
```
