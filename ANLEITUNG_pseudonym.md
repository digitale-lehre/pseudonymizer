# Anleitung: pseudonymizer

## Was macht das Tool?

Der pseudonymizer pseudonymisiert und de-pseudonymisiert personenbezogene Daten in CSV-, TSV- und XLSX-Dateien. Personenbezogene Spalten (Familienname, Vorname, Matrikelnummer, E-Mail, Pruefer, SV-Nummer, Geburtsdatum, Telefon, Valuatic Examiner/Candidate) werden durch verschluesselte Werte ersetzt, die nur mit dem richtigen Secret zurueckgefuehrt werden koennen.

**Verfahren:** AES-256-CBC (symmetrische Verschluesselung, deterministisch mit PBKDF2-Schluesselableitung). Es wird keine separate Key-Datei benoetigt — derselbe Secret verschluesselt und entschluesselt.

**Zwei Varianten:** Es gibt eine Python-CLI (`pseudonym.py`) und eine Browser-GUI (`pseudonym_gui.html`). Beide sind kryptografisch kompatibel.


## Variante 1: Browser-GUI (empfohlen fuer Einsteiger)

Kein Install noetig. Einfach `pseudonym_gui.html` im Browser oeffnen (Doppelklick).

1. **Datei waehlen:** CSV, TSV oder XLSX per Drag & Drop oder Dateiauswahl laden (auch mehrere oder ZIP)
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


## Batch-Modus (mehrere Dateien)

Beide Varianten unterstuetzen die Verarbeitung mehrerer Dateien in einem Durchgang.

### Browser-GUI

- **Mehrfachauswahl:** Im Dateiauswahl-Dialog mit Strg/Cmd mehrere Dateien auswaehlen, oder mehrere Dateien per Drag & Drop laden
- **ZIP-Upload:** Eine ZIP-Datei hochladen — enthaltene CSV/XLSX werden automatisch extrahiert
- **Ergebnis:** Bei mehreren Dateien wird ein ZIP-Archiv mit allen Ergebnissen zum Download angeboten
- **Vorschau:** Ueber Tabs (bis 8 Dateien) oder Dropdown (mehr als 8 Dateien) koennen einzelne Ergebnisse angezeigt werden

### Python CLI

Mehrere Dateien als Argumente uebergeben:

```bash
python pseudonym.py encrypt datei1.csv datei2.xlsx --secret "MeinSecret"
```

ZIP-Archiv als Eingabe (entpackt automatisch CSV/XLSX):

```bash
python pseudonym.py encrypt archiv.zip --secret "MeinSecret"
```

Alle CSVs verschluesseln und in einem Ordner ablegen:

```bash
python pseudonym.py encrypt *.csv --secret "MeinSecret" --output-dir ./encrypted/
```

Alle Ergebnisse in ein ZIP-Archiv buendeln:

```bash
python pseudonym.py encrypt *.csv --secret "MeinSecret" --zip
```

| Option | Beschreibung |
|---|---|
| `--output-dir DIR` | Ausgabeverzeichnis fuer alle Ergebnisdateien |
| `--zip` | Alle Ergebnisdateien in ein ZIP-Archiv buendeln |

**Hinweis:** `--output`/`-o` funktioniert nur bei einzelnen Dateien. Fuer Batch-Verarbeitung `--output-dir` verwenden.


## Zusaetzliche Spalten verschluesseln

Falls Ihre Datei Spalten enthaelt, die nicht automatisch erkannt werden (z.B. "Kommentar", "Notiz", "Bemerkung"), koennen Sie diese manuell zur Verschluesselung hinzufuegen.

### Browser-GUI

In der Dateivorschau auf die gewuenschte Spaltenueberschrift klicken. Die Spalte wird blau hinterlegt und beim naechsten Verschluesseln mitverarbeitet. Zum Entfernen auf das × klicken. Es koennen beliebig viele zusaetzliche Spalten gleichzeitig ausgewaehlt werden.

### Python CLI

```bash
python pseudonym.py encrypt datei.csv --secret "MeinSecret" --extra-cols "Kommentar,Notiz"
```

Mehrere Spalten werden kommagetrennt angegeben. Bereits automatisch erkannte Spalten (z.B. Vorname) muessen nicht nochmals angegeben werden.


## Unterstuetzte Spalten

Das Tool erkennt automatisch verschiedene Schreibweisen der Identitaetsspalten (case-insensitive):

| Spaltentyp | Erkannte Spaltennamen |
|---|---|
| Familienname | `FAMILIENNAME`, `Familienname`, `Zuname`, `Nachname`, `Surname`, `Family Name`, `FAMILY_NAME_OF_STUDENT`, `Last Name`, `LastName`, `Familienname oder Nachname`, `Familien- oder Nachname` |
| Vorname | `VORNAME`, `Vorname`, `FirstName`, `FIRST_NAME_OF_STUDENT`, `First Name`, `Given Name`, `GivenName`, `Rufname` |
| Matrikelnummer | `MATRIKELNUMMER`, `Matrikelnummer`, `Matnr`, `Matrikelnr`, `Matrikelnr.`, `REGISTRATION_NUMBER`, `StudentID`, `Student ID`, `Matrikel`, `Kennnummer` |
| E-Mail | `EMAIL_ADDRESS`, `E-Mail`, `Email`, `Mail`, `E_MAIL`, `E-Mail Adresse`, `Emailadresse`, `Mailadresse`, `Attendee Email`, `E-Mail-Adresse` |
| Pruefer/Examiner | `Examiner`, `Pruefer`, `Pruefer`, `Pruefer/in`, `PrueferIn`, `Pruefer:in`, `EXAMINER` |
| Anzeigename | `Anzeigename`, `Display Name`, `DisplayName`, `Full Name`, `FullName`, `Student Name` |
| SV-Nummer | `Sozialversicherungsnummer`, `SVNr`, `SVNR`, `SV-Nr`, `SV-Nr.`, `SV-Nummer`, `Versicherungsnummer`, `SSN` |
| Geburtsdatum | `Geburtsdatum`, `Geburtstag`, `Geb.Datum`, `Geb.-Datum`, `Birthday`, `Date of Birth`, `DOB`, `Birth Date` |
| Telefon | `Telefon`, `Telefonnummer`, `Tel`, `Tel.`, `Phone`, `Phone Number`, `Handy`, `Handynummer`, `Mobilnummer`, `Mobile`, `Cell Phone` |
| Name (optional) | `NAME` — wird automatisch aus Familienname + Vorname zusammengesetzt, falls erkannt |
| Examiner ID (Valuatic) | `examiner_id`, `Examiner_ID`, `EXAMINER_ID` |
| Examiner Nachname (Valuatic) | `examiner_last_name`, `Examiner_Last_Name`, `EXAMINER_LAST_NAME` |
| Examiner Vorname (Valuatic) | `examiner_first_name`, `Examiner_First_Name`, `EXAMINER_FIRST_NAME` |
| Candidate ID (Valuatic) | `candidate_id`, `Candidate_ID`, `CANDIDATE_ID` |
| Candidate Nachname (Valuatic) | `candidate_last_name`, `Candidate_Last_Name`, `CANDIDATE_LAST_NAME` |
| Candidate Vorname (Valuatic) | `candidate_first_name`, `Candidate_First_Name`, `CANDIDATE_FIRST_NAME` |

Die Valuatic-Spalten verwenden eigene Schluessel (`examiner_nachname` statt `familienname` etc.), da Pruefer- und Kandidatendaten in derselben Datei vorkommen und unabhaengig voneinander verschluesselt werden muessen.

**Suffix-Stripping:** Suffixe wie `.x`, `.y`, `.1`, `.2` (aus R-Merge-Operationen) werden vor dem Abgleich automatisch entfernt. Z.B. wird `Vorname.x` als `Vorname` erkannt.

Es muessen nicht alle Spalten vorhanden sein. Das Tool verschluesselt nur die gefundenen Identitaetsspalten. Alle anderen Spalten bleiben unveraendert.

Vollstaendige Spalten-Referenz: [docs/column-reference.md](docs/column-reference.md)


## NAME-Spalte

Falls eine Spalte `NAME` existiert und deren Inhalt der Kombination aus `FAMILIENNAME VORNAME` entspricht (oder umgekehrt), wird diese automatisch aus den verschluesselten Einzelwerten zusammengesetzt. So bleibt die Konsistenz erhalten.


## Bekannte XLSX-Probleme

Falls eine XLSX-Datei fehlerhafte Zeichnungsreferenzen enthaelt (z.B. `drawing1.xml` fehlt im Archiv), repariert das Tool diese automatisch vor der Verarbeitung. Eine entsprechende Meldung wird ausgegeben.


## MLW-Exporte (MedLearnWiki)

MLW-Exporte enthalten Metadaten-Zeilen vor der eigentlichen Spalten-Kopfzeile (z.B. Modulcode, Modulname, Datum). Das Tool erkennt die Header-Zeile automatisch und behaelt die Metadaten-Zeilen unveraendert bei.


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
python pseudonym.py [-h] [--version] {encrypt,decrypt} input [input ...] --secret SECRET
                    [--output OUTPUT] [--sep SEP] [--output-dir DIR] [--zip] [--extra-cols SPALTEN]

Argumente:
  {encrypt,decrypt}   encrypt = pseudonymisieren, decrypt = zurueckfuehren
  input               Pfad(e) zu CSV-, XLSX- oder ZIP-Dateien (mehrere moeglich)
  --secret SECRET     Geheimer Schluessel (beliebiger String)
  --output, -o        Ausgabepfad (nur bei einzelner Datei)
  --sep, -s           CSV-Trennzeichen (Standard: Komma; wird bei XLSX ignoriert)
  --output-dir DIR    Ausgabeverzeichnis fuer Batch-Verarbeitung
  --zip               Alle Ergebnisdateien in ein ZIP-Archiv buendeln
  --extra-cols SPALTEN  Zusaetzliche Spalten verschluesseln (kommagetrennt)
  --version           Versionsnummer anzeigen
```
