# pseudonymizer

AES-256-CBC Pseudonymisierung und Anonymisierung fuer CSV-, TSV-, XLSX- und XLSM-Dateien.

Ersetzt personenbezogene Spalten (Name, Matrikelnummer, E-Mail, Pruefer, SV-Nummer, Geburtsdatum, Telefon, Valuatic Examiner/Candidate) durch verschluesselte Pseudonyme. Gleicher Secret = gleiche Pseudonyme, umkehrbar mit demselben Secret. Ein dritter Modus leert die Spalten endgueltig (Anonymisieren).

> **Detaillierte Dokumentation:** [docs/index.md](docs/index.md) | **Schritt-fuer-Schritt-Anleitung:** [ANLEITUNG_pseudonym.md](ANLEITUNG_pseudonym.md)

## Zwei Varianten

|  | **Browser-GUI** | **Python CLI** |
|---|---|---|
| Datei | `pseudonym_gui.html` | `pseudonym.py` |
| Benoetigt | Nur einen Browser | Python 3.8+ |
| Start | Doppelklick auf HTML | `python pseudonym.py ...` |
| Formate | CSV, TSV, TXT, XLSX, XLSM, ZIP | CSV, TSV, TXT, XLSX, XLSM, ZIP |
| Batch-Modus | Multi-Select, Drag & Drop, ZIP | Mehrere Dateien, Ordner, Platzhalter, ZIP, `--output-dir`, `--zip` |
| Anonymisieren | Schaltflaeche "Anonymisieren" | `python pseudonym.py anonymize ...` |
| Eigene Spalten | Spaltenueberschriften anklicken | `--extra-cols "Spalte1,Spalte2"` |

Beide Varianten sind **kryptografisch kompatibel** — eine mit Python verschluesselte Datei kann in der GUI entschluesselt werden und umgekehrt. CSV-Ausgaben sind byte-gleich. Automatische Tests vergleichen beide Varianten.

> **Excel-Hinweis:** Die Python CLI erhaelt in `.xlsx`- und `.xlsm`-Dateien die Formatierung und bei `.xlsm` die Makros (`keep_vba=True`). Die Browser-GUI erhaelt Werte, Zahlenformate, Formeln und Spaltenbreiten, verwirft aber Farben, Schriften, Rahmen und Makros.

## Schnellstart

### Browser-GUI (kein Install)

`pseudonym_gui.html` doppelklicken — fertig. Alles laeuft lokal im Browser, keine Daten verlassen den Rechner.

Mehr dazu: [Browser-GUI Anleitung](docs/usage-gui.md)

### Python CLI

```bash
pip install cryptography openpyxl

# Verschluesseln (das Programm fragt verdeckt nach dem Secret)
python pseudonym.py encrypt datei.csv
python pseudonym.py encrypt datei.xlsx

# Entschluesseln
python pseudonym.py decrypt datei_pseudo.csv

# Anonymisieren: Identitaetsspalten endgueltig leeren (kein Secret)
python pseudonym.py anonymize datei.csv
```

Fehlt ein Paket, nennt das Programm den passenden Installationsbefehl. `python pseudonym.py --version` prueft die Installation.

Das Secret laesst sich auch mit `--secret "..."` oder der Umgebungsvariable `PSEUDONYM_SECRET` uebergeben. Mit `--secret` steht es aber im Verlauf der Konsole. Die verdeckte Eingabe ist deshalb der empfohlene Weg.

Mehr dazu: [CLI Referenz](docs/usage-cli.md)

## Batch-Modus

Beide Varianten unterstuetzen die Verarbeitung mehrerer Dateien in einem Durchgang:

**Browser-GUI:** Mehrere Dateien per Drag & Drop oder Mehrfachauswahl laden, oder eine ZIP-Datei hochladen. Ergebnis wird als ZIP heruntergeladen.

**Python CLI:**

```bash
# Mehrere Dateien
python pseudonym.py encrypt datei1.csv datei2.xlsx

# Ganzer Ordner oder ZIP als Eingabe
python pseudonym.py encrypt exporte/
python pseudonym.py encrypt archiv.zip

# Ergebnis als ZIP buendeln
python pseudonym.py encrypt "*.csv" --zip

# Ausgabe in Verzeichnis (wird angelegt)
python pseudonym.py encrypt "*.csv" --output-dir ./encrypted/
```

Eine feste Obergrenze fuer die Zahl der Dateien gibt es nicht. Getestet sind 500 Dateien in einem Lauf, in der CLI und in der GUI. Ein Fehler in einer Datei bricht den Lauf nicht ab.

Mehr dazu: [CLI Batch-Modus](docs/usage-cli.md#batch-modus) | [GUI Batch-Modus](docs/usage-gui.md#batch-modus)

## Zusaetzliche Spalten

Neben den automatisch erkannten Identitaetsspalten koennen **beliebig viele weitere Spalten** zur Verschluesselung markiert werden:

**Browser-GUI:** In der Dateivorschau auf eine Spaltenueberschrift klicken — sie wird hervorgehoben und beim Verschluesseln mitverarbeitet. Nochmal klicken oder × entfernt die Auswahl. Mehrere Spalten gleichzeitig auswaehlbar.

**Python CLI:**

```bash
python pseudonym.py encrypt datei.csv --extra-cols "Kommentar,Notiz,Bemerkung"
```

Kommagetrennte Liste beliebiger Spaltennamen. Bereits automatisch erkannte Spalten werden nicht doppelt verschluesselt. Beim Entschluesseln dieselben Spalten wieder angeben.

Mehr dazu: [CLI Referenz](docs/usage-cli.md#zusaetzliche-spalten) | [GUI Anleitung](docs/usage-gui.md#zusaetzliche-spalten) | [Schritt-fuer-Schritt](ANLEITUNG_pseudonym.md#zusaetzliche-spalten-verschluesseln)

## Erkannte Spalten

Das Tool erkennt automatisch diese Spaltennamen. Gross-/Kleinschreibung spielt keine Rolle (`FAMILIENNAME`, `Familienname` und `familienname` sind gleich). Alle passenden Spalten werden verarbeitet, auch mehrere je Typ (z.B. `Telefon` und `Handy`):

| Spaltentyp | Erkannte Spaltennamen |
|---|---|
| **Familienname** | Familienname, Zuname, Nachname, Last Name, LastName, Surname, Family Name, Family_Name, FAMILY_NAME_OF_STUDENT, Familienname oder Nachname, Familien- oder Nachname |
| **Vorname** | Vorname, First Name, FirstName, Given Name, GivenName, Rufname, FIRST_NAME_OF_STUDENT |
| **Matrikelnummer** | Matrikelnummer, Matnr, MatrNr, Matrikel, Matrikelnr, Matrikelnr., Mat.Nr., Mat.Nr, Mat-Nr., Mat-Nr, Mat. Nr., StudentID, Student_ID, Student ID, REGISTRATION_NUMBER, Registration Number, ID number, ID-Nummer, Kennnummer |
| **E-Mail** | EMAIL_ADDRESS, E-Mail, Email, Mail, E_MAIL, EmailAddress, E-Mail-Adresse, E-Mail Adresse, Emailadresse, Mailadresse, Email address, E-Mail des Teilnehmers, Attendee Email |
| **Pruefer/Examiner** | Examiner, Prüfer, Pruefer, Prufer, Prüfer/in, PrüferIn, Prüfer:in |
| **Anzeigename** | Anzeigename, Display Name, DisplayName, Full Name, FullName, Student Name |
| **SV-Nummer** | Sozialversicherungsnummer, SVNr, SV-Nr, SV-Nr., SV-Nummer, SV Nummer, Versicherungsnummer, Social Security Number, SSN |
| **Geburtsdatum** | Geburtsdatum, Geburtstag, Geb.Datum, Geb.-Datum, GebDatum, Geb. Datum, Birthday, Date of Birth, DateOfBirth, DOB, Birth Date, BirthDate |
| **Telefon** | Telefon, Telefonnummer, Tel, Tel., Tel.Nr., TelNr, Phone, Phone Number, PhoneNumber, Handy, Handynummer, Mobilnummer, Mobile, Mobiltelefon, Cell, Cell Phone |
| **Name** | Name — je Zeile aus Familienname + Vorname zusammengesetzt; sonst wird der ganze Wert als ein Token verschluesselt |
| **Examiner ID (Valuatic)** | examiner_id |
| **Examiner Nachname (Valuatic)** | examiner_last_name |
| **Examiner Vorname (Valuatic)** | examiner_first_name |
| **Candidate ID (Valuatic)** | candidate_id |
| **Candidate Nachname (Valuatic)** | candidate_last_name |
| **Candidate Vorname (Valuatic)** | candidate_first_name |

Die Valuatic-Spalten verwenden eigene Schluessel, da Pruefer- und Kandidatendaten in derselben Datei vorkommen und unabhaengig verschluesselt werden muessen.

**Suffix-Stripping:** Eine Endung nach dem letzten Punkt (`.x`, `.y`, `.1`, `.2` aus R-Merge-Operationen) wird vor dem Abgleich entfernt. Z.B. wird `Vorname.x` als `Vorname` erkannt und `Name.y` als `Name`.

Vollstaendige Liste: [Spalten-Referenz](docs/column-reference.md)

## Sicherheit

- **AES-256-CBC** mit PBKDF2-Schluesselableitung (100.000 Iterationen)
- **Deterministisch:** gleicher Input + gleicher Secret = gleiches Pseudonym
- **Lokal:** alle Verarbeitung geschieht auf dem eigenen Rechner. Die Browser-GUI kann technisch keine Daten senden (Content Security Policy) und laedt ihre zwei Bibliotheken nur mit passender Pruefsumme
- **Secret sicher aufbewahren** — ohne Secret keine Wiederherstellung moeglich
- **Falsches Secret wird erkannt:** Laesst sich kein Wert entschluesseln, entsteht keine Ausgabedatei
- **Keine erkannte Spalte, keine Ausgabe:** Eine Datei ohne erkannte Spalten wird nicht unveraendert als `_pseudo` ausgegeben
- **Anonymisieren ist keine Garantie:** Das Tool leert nur erkannte Spalten. Die uebrigen Spalten koennen Personen weiter erkennbar machen

Details: [Kryptographie-Spezifikation](docs/cryptography.md)

## Dokumentation

| Seite | Beschreibung |
|---|---|
| [Uebersicht](docs/index.md) | Wiki-Startseite mit allen Links |
| [Installation](docs/installation.md) | Installationsanleitung fuer Python und Browser |
| [CLI Referenz](docs/usage-cli.md) | Alle Python-CLI-Befehle und Optionen |
| [Browser-GUI](docs/usage-gui.md) | Anleitung fuer die HTML-Oberflaeche |
| [Kryptographie](docs/cryptography.md) | Technische Spezifikation der Verschluesselung |
| [Spalten-Referenz](docs/column-reference.md) | Alle erkannten Spalten und Aliase |
| [Troubleshooting](docs/troubleshooting.md) | Haeufige Probleme und Loesungen |
| [Entwicklung](docs/development.md) | Beitragen, Testen, Architektur |
