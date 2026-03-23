# pseudonymizer

AES-256-CBC Pseudonymisierung fuer CSV- und XLSX-Dateien.

Ersetzt personenbezogene Spalten (Name, Matrikelnummer, E-Mail, Pruefer, SV-Nummer, Geburtsdatum, Telefon, Valuatic Examiner/Candidate) durch verschluesselte Pseudonyme. Gleicher Secret = gleiche Pseudonyme, umkehrbar mit demselben Secret.

> **Detaillierte Dokumentation:** [docs/index.md](docs/index.md) | **Schritt-fuer-Schritt-Anleitung:** [ANLEITUNG_pseudonym.md](ANLEITUNG_pseudonym.md)

## Zwei Varianten

|  | **Browser-GUI** | **Python CLI** |
|---|---|---|
| Datei | `pseudonym_gui.html` | `pseudonym.py` |
| Benoetigt | Nur einen Browser | Python 3.8+ |
| Start | Doppelklick auf HTML | `python pseudonym.py ...` |
| Formate | CSV, XLSX | CSV, XLSX |

Beide Varianten sind **kryptografisch kompatibel** — eine mit Python verschluesselte Datei kann in der GUI entschluesselt werden und umgekehrt.

## Schnellstart

### Browser-GUI (kein Install)

`pseudonym_gui.html` doppelklicken — fertig. Alles laeuft lokal im Browser, keine Daten verlassen den Rechner.

Mehr dazu: [Browser-GUI Anleitung](docs/usage-gui.md)

### Python CLI

```bash
pip install cryptography openpyxl

# Verschluesseln
python pseudonym.py encrypt datei.csv --secret "MeinSecret"
python pseudonym.py encrypt datei.xlsx --secret "MeinSecret"

# Entschluesseln
python pseudonym.py decrypt datei_pseudo.csv --secret "MeinSecret"
```

Mehr dazu: [CLI Referenz](docs/usage-cli.md)

## Erkannte Spalten

Das Tool erkennt automatisch verschiedene Schreibweisen (case-insensitive):

| Spaltentyp | Erkannte Spaltennamen |
|---|---|
| **Familienname** | FAMILIENNAME, Zuname, Nachname, Surname, Family Name, FAMILY_NAME_OF_STUDENT, Last Name, LastName, Familienname oder Nachname, Familien- oder Nachname |
| **Vorname** | VORNAME, FirstName, FIRST_NAME_OF_STUDENT, First Name, Given Name, GivenName, Rufname |
| **Matrikelnummer** | MATRIKELNUMMER, Matnr, Matrikelnr, Matrikelnr., REGISTRATION_NUMBER, StudentID, Student ID, Matrikel, Kennnummer |
| **E-Mail** | EMAIL_ADDRESS, E-Mail, Email, Mail, E_MAIL, E-Mail Adresse, Emailadresse, Mailadresse, Attendee Email |
| **Pruefer** | Examiner, Pruefer, Pruefer, Pruefer/in, PrueferIn, Pruefer:in |
| **Anzeigename** | Anzeigename, Display Name, DisplayName, Full Name, FullName, Student Name |
| **SV-Nummer** | Sozialversicherungsnummer, SVNr, SVNR, SV-Nr, SV-Nr., SV-Nummer, Versicherungsnummer, SSN |
| **Geburtsdatum** | Geburtsdatum, Geburtstag, Geb.Datum, Geb.-Datum, Birthday, Date of Birth, DOB, Birth Date |
| **Telefon** | Telefon, Telefonnummer, Tel, Tel., Phone, Phone Number, Handy, Handynummer, Mobilnummer, Mobile, Cell Phone |
| **Name** *(optional)* | NAME — automatisch aus Familienname + Vorname zusammengesetzt |
| **Examiner ID** *(Valuatic)* | examiner_id, Examiner_ID, EXAMINER_ID |
| **Examiner Nachname** *(Valuatic)* | examiner_last_name, Examiner_Last_Name, EXAMINER_LAST_NAME |
| **Examiner Vorname** *(Valuatic)* | examiner_first_name, Examiner_First_Name, EXAMINER_FIRST_NAME |
| **Candidate ID** *(Valuatic)* | candidate_id, Candidate_ID, CANDIDATE_ID |
| **Candidate Nachname** *(Valuatic)* | candidate_last_name, Candidate_Last_Name, CANDIDATE_LAST_NAME |
| **Candidate Vorname** *(Valuatic)* | candidate_first_name, Candidate_First_Name, CANDIDATE_FIRST_NAME |

Die Valuatic-Spalten verwenden eigene Schluessel, da Pruefer- und Kandidatendaten in derselben Datei vorkommen und unabhaengig verschluesselt werden muessen.

**Suffix-Stripping:** Suffixe wie `.x`, `.y`, `.1`, `.2` (aus R-Merge-Operationen) werden vor dem Abgleich automatisch entfernt. Z.B. wird `Vorname.x` als `Vorname` erkannt.

Vollstaendige Liste: [Spalten-Referenz](docs/column-reference.md)

## Sicherheit

- **AES-256-CBC** mit PBKDF2-Schluesselableitung (100.000 Iterationen)
- **Deterministisch:** gleicher Input + gleicher Secret = gleiches Pseudonym
- **Lokal:** alle Verarbeitung geschieht auf dem eigenen Rechner
- **Secret sicher aufbewahren** — ohne Secret keine Wiederherstellung moeglich

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
