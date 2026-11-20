# Anleitung: pseudonymizer

## Was macht das Tool?

Der pseudonymizer pseudonymisiert, de-pseudonymisiert und anonymisiert personenbezogene Daten in CSV-, TSV-, XLSX- und XLSM-Dateien. Personenbezogene Spalten (Familienname, Vorname, Matrikelnummer, E-Mail, Pruefer, SV-Nummer, Geburtsdatum, Telefon, Valuatic Examiner/Candidate) werden durch verschluesselte Werte ersetzt, die nur mit dem richtigen Secret zurueckgefuehrt werden koennen.

**Verfahren:** AES-256-CBC (symmetrische Verschluesselung, deterministisch mit PBKDF2-Schluesselableitung). Es wird keine separate Key-Datei benoetigt — derselbe Secret verschluesselt und entschluesselt.

**Zwei Varianten:** Es gibt eine Python-CLI (`pseudonym.py`) und eine Browser-GUI (`pseudonym_gui.html`). Beide sind kryptografisch kompatibel.


## Variante 1: Browser-GUI (empfohlen fuer Einsteiger)

Kein Install noetig. Einfach `pseudonym_gui.html` im Browser oeffnen (Doppelklick).

1. **Datei waehlen:** CSV, TSV, XLSX oder XLSM per Drag & Drop oder Dateiauswahl laden (auch mehrere oder ZIP)
2. **Vorschau pruefen:** Die erkannten Spalten sind blau. Fehlt eine Spalte, auf ihre Ueberschrift klicken
3. **Modus waehlen:** "Verschluesseln", "Entschluesseln" oder "Anonymisieren"
4. **Secret eingeben:** Beliebiges Passwort (muss zum Entschluesseln identisch sein; entfaellt beim Anonymisieren)
5. **Starten:** Ergebnis wird zum Download angeboten

Alle Daten werden **lokal im Browser** verarbeitet — nichts wird hochgeladen oder uebertragen.

Detaillierte Anleitung: [docs/usage-gui.md](docs/usage-gui.md)


## Variante 2: Python CLI

### Voraussetzungen

Python 3.8+ und folgende Pakete:

```bash
pip install cryptography openpyxl
```

`cryptography` wird fuer die AES-Verschluesselung benoetigt, `openpyxl` fuer die XLSX-Verarbeitung.

Fehlt ein Paket, bricht das Programm vor der Secret-Abfrage ab und nennt den Installationsbefehl fuer genau das Python, das gerade laeuft. Diesen Befehl kopieren und ausfuehren. Das hilft vor allem, wenn auf dem Rechner mehrere Python-Versionen installiert sind. `python pseudonym.py --version` zeigt die Version und meldet fehlende Pakete.

### Secret eingeben

Das Programm fragt verdeckt nach dem Secret, beim Verschluesseln zweimal. So steht das Secret nicht im Verlauf der Konsole, und ein Tippfehler faellt auf. Fuer Skripte gibt es die Umgebungsvariable `PSEUDONYM_SECRET`. Die Option `--secret "..."` funktioniert weiter, hinterlaesst das Secret aber im Verlauf der Konsole.


### CSV pseudonymisieren

```bash
python pseudonym.py encrypt eingabe.csv
```

Erzeugt `eingabe_pseudo.csv` im selben Ordner.

### CSV de-pseudonymisieren

```bash
python pseudonym.py decrypt eingabe_pseudo.csv
```

Erzeugt `eingabe_pseudo_restored.csv`. Der Secret muss identisch sein.

### XLSX pseudonymisieren

```bash
python pseudonym.py encrypt eingabe.xlsx
```

Erzeugt `eingabe_pseudo.xlsx`. Alle Sheets mit Identitaetsspalten werden verarbeitet. Formatierung und Styles bleiben erhalten.

### XLSX de-pseudonymisieren

```bash
python pseudonym.py decrypt eingabe_pseudo.xlsx
```

Erzeugt `eingabe_pseudo_restored.xlsx`.

### XLSM pseudonymisieren (Macro-aktivierte Arbeitsmappen)

```bash
python pseudonym.py encrypt eingabe.xlsm
```

Erzeugt `eingabe_pseudo.xlsm`. Die CLI behaelt Makros und Formatierung (`keep_vba=True`). Die Browser-GUI verarbeitet `.xlsm`-Dateien ebenfalls, verwirft dabei jedoch Makros und Formatierung.

### Eigenen Ausgabepfad angeben

```bash
python pseudonym.py encrypt eingabe.csv --output ausgabe.csv
```

### CSV-Trennzeichen

Das Programm erkennt Semikolon, Komma und Tab automatisch. Fuer ein anderes Trennzeichen:

```bash
python pseudonym.py encrypt eingabe.csv --sep "|"
```

### Anonymisieren

```bash
python pseudonym.py anonymize eingabe.csv
```

Erzeugt `eingabe_anonym.csv`. Alle Zellen der erkannten Spalten (und der Zusatzspalten) sind leer. Die Kopfzeile und alle anderen Spalten bleiben. Es gibt kein Secret und keinen Weg zurueck.

Das Tool leert nur, was es erkennt. Pruefen Sie vor der Weitergabe, ob die uebrigen Spalten (Freitext, Gruppe, Termin), die Zeilen vor der Kopfzeile oder der Dateiname eine Person erkennbar machen. Existiert die Originaldatei mit gleicher Zeilenfolge, laesst sich jede Zeile ueber ihre Position zuordnen.


## Batch-Modus (mehrere Dateien)

Beide Varianten unterstuetzen die Verarbeitung mehrerer Dateien in einem Durchgang.

### Browser-GUI

- **Mehrfachauswahl:** Im Dateiauswahl-Dialog mit Strg/Cmd mehrere Dateien auswaehlen, oder mehrere Dateien per Drag & Drop laden
- **ZIP-Upload:** Eine ZIP-Datei hochladen — enthaltene CSV/XLSX/XLSM werden automatisch extrahiert
- **Ergebnis:** Bei mehreren Dateien wird ein ZIP-Archiv mit allen Ergebnissen zum Download angeboten
- **Vorschau:** Ueber Tabs (bis 8 Dateien) oder Dropdown (mehr als 8 Dateien) koennen einzelne Ergebnisse angezeigt werden

### Python CLI

Mehrere Dateien als Argumente uebergeben:

```bash
python pseudonym.py encrypt datei1.csv datei2.xlsx
```

ZIP-Archiv als Eingabe (entpackt automatisch CSV/XLSX/XLSM):

```bash
python pseudonym.py encrypt archiv.zip
```

Ergebnisse aus einem ZIP werden neben dem ZIP abgelegt (bzw. in `--output-dir`). Mit `--zip` heisst das Archiv dann `<ZIP-Name>_pseudo.zip` bzw. `_restored.zip`.

Einen ganzen Ordner verarbeiten und die Ergebnisse in einem anderen Ordner ablegen:

```bash
python pseudonym.py encrypt exporte/ --output-dir ./encrypted/
```

Alle CSVs verschluesseln und die Ergebnisse in ein ZIP-Archiv buendeln:

```bash
python pseudonym.py encrypt "*.csv" --zip
```

Das Programm loest Platzhalter wie `*.csv` selbst auf, auch unter Windows. Bei Ordnern und Platzhaltern ueberspringt es Ergebnisse frueherer Laeufe (`_pseudo`, `_restored`, `_anonym`). Eine feste Obergrenze fuer die Zahl der Dateien gibt es nicht; getestet sind 500 Dateien in einem Lauf. Ein Fehler in einer Datei bricht den Lauf nicht ab: Am Ende nennt das Programm jede fehlgeschlagene Datei mit Grund.

| Option | Beschreibung |
|---|---|
| `--output-dir DIR` | Ausgabeverzeichnis fuer alle Ergebnisdateien (wird angelegt) |
| `--zip` | Alle Ergebnisdateien in ein ZIP-Archiv buendeln (Name siehe unten) |

**Hinweis:** `--output`/`-o` funktioniert nur bei einzelnen Dateien. Fuer Batch-Verarbeitung `--output-dir` verwenden.

Name des Archivs: gemeinsamer Anfang der Dateinamen, Modus, Anzahl und Datum, z.B. `Teilnehmerliste_pseudo_9Dateien_2026-10-06.zip` (ohne gemeinsamen Anfang: `Batch_pseudo_...`).


## Zusaetzliche Spalten verschluesseln

Falls Ihre Datei Spalten enthaelt, die nicht automatisch erkannt werden (z.B. "Kommentar", "Notiz", "Bemerkung"), koennen Sie diese manuell zur Verschluesselung hinzufuegen.

### Browser-GUI

In der Dateivorschau auf die gewuenschte Spaltenueberschrift klicken. Die Spalte wird blau hinterlegt und beim naechsten Verschluesseln mitverarbeitet. Zum Entfernen auf das × klicken. Es koennen beliebig viele zusaetzliche Spalten gleichzeitig ausgewaehlt werden.

### Python CLI

```bash
python pseudonym.py encrypt datei.csv --extra-cols "Kommentar,Notiz"
```

Mehrere Spalten werden kommagetrennt angegeben. Bereits automatisch erkannte Spalten (z.B. Vorname) muessen nicht nochmals angegeben werden. **Beim Entschluesseln dieselben Spalten wieder angeben**, sonst bleiben sie verschluesselt.


## Unterstuetzte Spalten

Das Tool erkennt automatisch diese Spaltennamen. Gross-/Kleinschreibung spielt keine Rolle (`FAMILIENNAME`, `Familienname` und `familienname` sind gleich). Alle passenden Spalten werden verarbeitet, auch mehrere je Typ (z.B. `Telefon` und `Handy`):

| Spaltentyp | Erkannte Spaltennamen |
|---|---|
| Familienname | `Familienname`, `Zuname`, `Nachname`, `Last Name`, `LastName`, `Surname`, `Family Name`, `Family_Name`, `FAMILY_NAME_OF_STUDENT`, `Familienname oder Nachname`, `Familien- oder Nachname` |
| Vorname | `Vorname`, `First Name`, `FirstName`, `Given Name`, `GivenName`, `Rufname`, `FIRST_NAME_OF_STUDENT` |
| Matrikelnummer | `Matrikelnummer`, `Matnr`, `MatrNr`, `Matrikel`, `Matrikelnr`, `Matrikelnr.`, `Mat.Nr.`, `Mat.Nr`, `Mat-Nr.`, `Mat-Nr`, `Mat. Nr.`, `StudentID`, `Student_ID`, `Student ID`, `REGISTRATION_NUMBER`, `Registration Number`, `ID number`, `ID-Nummer`, `Kennnummer` |
| E-Mail | `EMAIL_ADDRESS`, `E-Mail`, `Email`, `Mail`, `E_MAIL`, `EmailAddress`, `E-Mail-Adresse`, `E-Mail Adresse`, `Emailadresse`, `Mailadresse`, `Email address`, `E-Mail des Teilnehmers`, `Attendee Email` |
| Pruefer/Examiner | `Examiner`, `Prüfer`, `Pruefer`, `Prufer`, `Prüfer/in`, `PrüferIn`, `Prüfer:in` |
| Anzeigename | `Anzeigename`, `Display Name`, `DisplayName`, `Full Name`, `FullName`, `Student Name` |
| SV-Nummer | `Sozialversicherungsnummer`, `SVNr`, `SV-Nr`, `SV-Nr.`, `SV-Nummer`, `SV Nummer`, `Versicherungsnummer`, `Social Security Number`, `SSN` |
| Geburtsdatum | `Geburtsdatum`, `Geburtstag`, `Geb.Datum`, `Geb.-Datum`, `GebDatum`, `Geb. Datum`, `Birthday`, `Date of Birth`, `DateOfBirth`, `DOB`, `Birth Date`, `BirthDate` |
| Telefon | `Telefon`, `Telefonnummer`, `Tel`, `Tel.`, `Tel.Nr.`, `TelNr`, `Phone`, `Phone Number`, `PhoneNumber`, `Handy`, `Handynummer`, `Mobilnummer`, `Mobile`, `Mobiltelefon`, `Cell`, `Cell Phone` |
| Name | `Name` — je Zeile aus Familienname + Vorname zusammengesetzt; sonst wird der ganze Wert als ein Token verschluesselt |
| Examiner ID (Valuatic) | `examiner_id` |
| Examiner Nachname (Valuatic) | `examiner_last_name` |
| Examiner Vorname (Valuatic) | `examiner_first_name` |
| Candidate ID (Valuatic) | `candidate_id` |
| Candidate Nachname (Valuatic) | `candidate_last_name` |
| Candidate Vorname (Valuatic) | `candidate_first_name` |

Die Valuatic-Spalten verwenden eigene Schluessel (`examiner_nachname` statt `familienname` etc.), da Pruefer- und Kandidatendaten in derselben Datei vorkommen und unabhaengig voneinander verschluesselt werden muessen.

**Suffix-Stripping:** Eine Endung nach dem letzten Punkt (`.x`, `.y`, `.1`, `.2` aus R-Merge-Operationen) wird vor dem Abgleich entfernt. Z.B. wird `Vorname.x` als `Vorname` erkannt und `Name.y` als `Name`.

Es muessen nicht alle Spalten vorhanden sein. Das Tool verschluesselt nur die gefundenen Identitaetsspalten. Alle anderen Spalten bleiben unveraendert.

Vollstaendige Spalten-Referenz: [docs/column-reference.md](docs/column-reference.md)


## NAME-Spalte

Das Tool prueft die Spalte `Name` in jeder Zeile einzeln. Entspricht der Inhalt der Kombination aus Familienname und Vorname dieser Zeile (in beliebiger Reihenfolge), setzt das Tool ihn aus den beiden Pseudonymen zusammen. So bleibt die Konsistenz erhalten.

Passt der Inhalt nicht (z.B. `Dr. Eva Test` oder `Test, Eva`) oder gibt es keine separaten Vorname-/Familienname-Spalten, wird der ganze Wert als ein Pseudonym verschluesselt. In beiden Faellen kommt beim Entschluesseln der urspruengliche Inhalt zurueck. Eine Datei, deren einzige erkannte Identitaetsspalte `Name` ist, wird dennoch verarbeitet.


## Bekannte XLSX-Probleme

Falls eine XLSX-Datei fehlerhafte Zeichnungsreferenzen enthaelt (z.B. `drawing1.xml` fehlt im Archiv), entfernt das Tool die defekten Verweise vor der Verarbeitung. Vorhandene Diagramme und Bilder bleiben. Eine entsprechende Meldung wird ausgegeben.

Kennwortgeschuetzte Dateien und das alte Format `.xls` kann das Tool nicht lesen. Bitte in Excel ohne Kennwort als `.xlsx` speichern.


## MLW-Exporte (Medizinische Lehre Wien)

MLW-Exporte enthalten Metadaten-Zeilen vor der eigentlichen Spalten-Kopfzeile (z.B. Modulcode, Modulname, Datum). Das Tool erkennt die Header-Zeile automatisch (die Zeile mit den meisten erkannten Spalten unter den ersten 20 Zeilen) und behaelt die Metadaten-Zeilen unveraendert bei. Steht in diesen Zeilen ein Name, bleibt er im Klartext.


## Wichtige Hinweise

- **Secret sicher aufbewahren:** Ohne den exakten Secret koennen die Daten nicht zurueckgefuehrt werden. Es gibt keine Wiederherstellungsmoeglichkeit.
- **Deterministisch:** Gleicher Secret + gleiche Daten = gleiches Pseudonym. Das ermoeglicht die Zuordnung ueber mehrere Dateien hinweg, solange derselbe Secret verwendet wird.
- **Falsches Secret:** Laesst sich beim Entschluesseln kein Wert entschluesseln, meldet das Tool das und schreibt keine Datei.
- **Keine erkannte Spalte:** Das Tool schreibt keine Datei und nennt die vorhandenen Spaltennamen.
- **CSV-Formaterhaltung:** Das Tool ersetzt nur den Inhalt der betroffenen Zellen. Kodierung, BOM, Anfuehrungszeichen, Leerzeichen und Zeilenumbrueche bleiben erhalten. Ein Encrypt-Decrypt-Roundtrip liefert eine byte-identische Datei. Ausnahme: Besteht die Pseudonym-Datei nur aus ASCII-Zeichen (alle Umlaute standen in verschluesselten Spalten), ist die zurueckgefuehrte Datei UTF-8 mit BOM, damit Excel die Umlaute richtig zeigt.
- **XLSX-Formaterhaltung (CLI):** Zellformatierung, bedingte Formatierung, Formeln und Styles bleiben erhalten. Blaetter ohne erkannte Spalten bleiben unveraendert in der Datei. Bei `.xlsm`-Dateien bleibt der Makro-Code (`keep_vba`) erhalten. Zurueckgefuehrte Zellen der Identitaetsspalten sind Text, auch wenn sie vorher Zahl oder Datum waren.
- **XLSX in der Browser-GUI:** Werte, Zahlenformate, Formeln und Spaltenbreiten bleiben erhalten. Farben, Schriften, Rahmen und Makros gehen verloren.
- **Kompatibilitaet:** Python CLI und Browser-GUI erzeugen identische Pseudonyme fuer gleiche Eingaben mit gleichem Secret.


## Beispiel-Workflow (MedCampus-Export)

```bash
# 1. MedCampus-Export pseudonymisieren
python pseudonym.py encrypt medcampus_export.csv

# 2. Pseudonymisierte Datei weitergeben / analysieren
#    (Pseudonyme sind URL-sichere Base64-Strings)

# 3. Spaeter: Original wiederherstellen
python pseudonym.py decrypt medcampus_export_pseudo.csv
```

Fuer XLSX-Dateien (z.B. Tertial-Zuteilungen):

```bash
python pseudonym.py encrypt tp-jahr5-2026_SoSe_0.xlsx
python pseudonym.py decrypt tp-jahr5-2026_SoSe_0_pseudo.xlsx
```


## Vollstaendige Optionen

```
python pseudonym.py [-h] [--version] {encrypt,decrypt,anonymize} input [input ...] [--secret SECRET]
                    [--output OUTPUT] [--output-dir DIR] [--zip] [--sep SEP] [--extra-cols SPALTEN]

Argumente:
  {encrypt,decrypt,anonymize}
                      encrypt = pseudonymisieren, decrypt = zurueckfuehren,
                      anonymize = Identitaetsspalten endgueltig leeren
  input               Dateien (CSV, TSV, XLSX, XLSM, ZIP), Ordner oder Platzhalter wie *.csv
  --secret SECRET     Geheimer Schluessel. Besser weglassen: Dann fragt das Programm verdeckt danach
  --output, -o        Ausgabepfad (nur bei einzelner Datei)
  --output-dir DIR    Ausgabeverzeichnis (wird angelegt)
  --zip               Alle Ergebnisdateien zusaetzlich in ein ZIP-Archiv buendeln
  --sep, -s           CSV-Trennzeichen (Standard: automatische Erkennung)
  --extra-cols SPALTEN  Zusaetzliche Spalten verarbeiten (kommagetrennt)
  --version           Versionsnummer anzeigen
```
