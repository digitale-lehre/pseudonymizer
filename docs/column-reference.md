# Spalten-Referenz

## Uebersicht

Der pseudonymizer erkennt Identitaetsspalten automatisch anhand ihrer Spaltennamen. Die Erkennung ist **case-insensitive** — Gross-/Kleinschreibung spielt keine Rolle.

Nur erkannte Identitaetsspalten werden verschluesselt. Alle anderen Spalten bleiben unveraendert.

**Suffix-Stripping:** Vor dem Abgleich werden Suffixe wie `.x`, `.y`, `.1`, `.2` (aus R-Merge-Operationen) automatisch von Spaltennamen entfernt. Z.B. wird `Vorname.x` als `Vorname` erkannt, `MATRIKELNUMMER.1` als `MATRIKELNUMMER`.


## Erkannte Spaltentypen

### Familienname

| Alias | Herkunft |
|---|---|
| `FAMILIENNAME` | MedCampus-Export |
| `Familienname` | Allgemein |
| `familienname` | Kleinschreibung |
| `Zuname` | Oesterreichisch |
| `zuname`, `ZUNAME` | Varianten |
| `Nachname` | Deutsch |
| `nachname`, `NACHNAME` | Varianten |
| `Surname` | Englisch |
| `surname` | Kleinschreibung |
| `Family Name` | Englisch (mit Leerzeichen) |
| `Family_Name` | Englisch (Underscore) |
| `Last Name` | Englisch (mit Leerzeichen) |
| `LastName` | Englisch (CamelCase) |
| `Last name` | Englisch (Satzform) |
| `Lastname` | Englisch (zusammen) |
| `FAMILY_NAME_OF_STUDENT` | SAP/MedCampus |
| `Family_Name_of_Student` | Mixed Case |
| `Familienname oder Nachname` | MLW-Export (Medizinische Lehre Wien) |
| `Familien- oder Nachname` | MLW-Export (Medizinische Lehre Wien), Kurzform |

### Vorname

| Alias | Herkunft |
|---|---|
| `VORNAME` | MedCampus-Export |
| `Vorname` | Allgemein |
| `vorname` | Kleinschreibung |
| `First Name` | Englisch (mit Leerzeichen) |
| `First name` | Englisch (Satzform) |
| `FirstName` | Englisch (CamelCase) |
| `Firstname` | Englisch |
| `Given Name` | Englisch (formell) |
| `GivenName` | Englisch (CamelCase) |
| `Given name` | Englisch (Satzform) |
| `Rufname` | Deutsch (Amtsdeutsch) |
| `FIRST_NAME_OF_STUDENT` | SAP/MedCampus |
| `First_Name_of_Student` | Mixed Case |

### Matrikelnummer

| Alias | Herkunft |
|---|---|
| `MATRIKELNUMMER` | MedCampus-Export |
| `Matrikelnummer` | Allgemein |
| `matrikelnummer` | Kleinschreibung |
| `Matnr` | Kurzform |
| `matnr`, `MATNR` | Varianten |
| `Matrikelnr` | Kurzform |
| `Matrikelnr.` | Kurzform (mit Punkt) |
| `MatrNr` | CamelCase-Kurzform |
| `Matrikel` | Kurzform |
| `matrikel`, `MATRIKEL` | Varianten |
| `Student ID` | Englisch (mit Leerzeichen) |
| `StudentID` | Englisch (CamelCase) |
| `Student_ID` | Englisch (Underscore) |
| `Kennnummer` | Deutsch (allgemein) |
| `REGISTRATION_NUMBER` | SAP/MedCampus |
| `Registration_Number` | Mixed Case |
| `Registration Number` | Englisch (mit Leerzeichen) |
| `ID number` | Englisch (allgemein) |
| `ID Number` | Englisch (Title Case) |
| `ID-Nummer` | Deutsch |

### E-Mail

| Alias | Herkunft |
|---|---|
| `EMAIL_ADDRESS` | SAP/MedCampus |
| `Email_Address` | Mixed Case |
| `E-Mail` | Deutsch |
| `E-MAIL` | Deutsch (Grossbuchstaben) |
| `e-mail` | Kleinschreibung |
| `E-Mail-Adresse` | Deutsch (ausfuehrlich) |
| `E-Mail Adresse` | Deutsch (mit Leerzeichen) |
| `Emailadresse` | Deutsch (zusammen) |
| `Mailadresse` | Deutsch (Kurzform) |
| `Email` | Englisch |
| `email`, `EMAIL` | Varianten |
| `Email address` | Englisch (Satzform) |
| `Email Address` | Englisch (Title Case) |
| `Mail` | Kurzform |
| `MAIL`, `mail` | Varianten |
| `E_MAIL` | Underscore-Variante |
| `EmailAddress` | CamelCase |
| `email_address` | Snake Case |
| `E-Mail des Teilnehmers` | Webex (Deutsch) |
| `Attendee Email` | Webex (Englisch) |

### Pruefer / Examiner

| Alias | Herkunft |
|---|---|
| `Examiner` | Englisch |
| `EXAMINER`, `examiner` | Varianten |
| `Pruefer` | Deutsch (ASCII-kompatibel) |
| `PRUEFER`, `pruefer` | Varianten |
| `Prufer` | Ohne Umlaut |
| `PRUFER` | Variante |
| `Prüfer/in` | Deutsch (Gender-Schraegstrich) |
| `PrüferIn` | Deutsch (Binnen-I) |
| `Prüfer:in` | Deutsch (Gender-Doppelpunkt) |


### Anzeigename / Display Name

| Alias | Herkunft |
|---|---|
| `Anzeigename` | Webex (Deutsch) |
| `ANZEIGENAME` | Variante |
| `anzeigename` | Kleinschreibung |
| `Display Name` | Webex (Englisch) |
| `DisplayName` | CamelCase |
| `DISPLAY NAME` | Variante |
| `display name` | Kleinschreibung |
| `Full Name` | Englisch |
| `FullName` | CamelCase |
| `Student Name` | Englisch (Studentenlisten) |

> **Hinweis:** Im Gegensatz zur `NAME`-Spalte wird `Anzeigename` / `Display Name` als eigenstaendige Identitaetsspalte verschluesselt, nicht als Zusammensetzung. Dies ist notwendig, da der Anzeigename in Webex-Exports nicht immer mit Vorname + Nachname uebereinstimmt (z.B. bei Gaesten, Titel, oder wenn Vorname/Nachname "N/A" ist).


### Sozialversicherungsnummer (SV-Nummer)

| Alias | Herkunft |
|---|---|
| `Sozialversicherungsnummer` | Deutsch (ausfuehrlich) |
| `SVNr` | Kurzform |
| `SVNR` | Grossbuchstaben |
| `SV-Nr` | Kurzform (mit Bindestrich) |
| `SV-Nr.` | Kurzform (mit Punkt) |
| `SV-Nummer` | Deutsch |
| `SV Nummer` | Deutsch (mit Leerzeichen) |
| `Versicherungsnummer` | Deutsch (allgemein) |
| `Social Security Number` | Englisch |
| `SSN` | Englisch (Abkuerzung) |


### Geburtsdatum

| Alias | Herkunft |
|---|---|
| `Geburtsdatum` | Deutsch |
| `Geburtstag` | Deutsch (umgangssprachlich) |
| `Geb.Datum` | Kurzform |
| `Geb.-Datum` | Kurzform (mit Bindestrich) |
| `GebDatum` | CamelCase |
| `Geb. Datum` | Kurzform (mit Leerzeichen) |
| `Birthday` | Englisch |
| `Date of Birth` | Englisch (ausfuehrlich) |
| `DateOfBirth` | CamelCase |
| `DOB` | Englisch (Abkuerzung) |
| `Birth Date` | Englisch (mit Leerzeichen) |
| `BirthDate` | CamelCase |
| `Birthdate` | Englisch (zusammen) |


### Telefon

| Alias | Herkunft |
|---|---|
| `Telefon` | Deutsch |
| `Telefonnummer` | Deutsch (ausfuehrlich) |
| `Tel` | Kurzform |
| `Tel.` | Kurzform (mit Punkt) |
| `Tel.Nr.` | Kurzform |
| `TelNr` | CamelCase-Kurzform |
| `Phone` | Englisch |
| `Phone Number` | Englisch (mit Leerzeichen) |
| `PhoneNumber` | CamelCase |
| `Handy` | Deutsch (Mobiltelefon) |
| `Handynummer` | Deutsch |
| `Mobilnummer` | Deutsch |
| `Mobile` | Englisch |
| `Mobiltelefon` | Deutsch (ausfuehrlich) |
| `Cell` | Englisch (Kurzform) |
| `Cell Phone` | Englisch |


## Valuatic (Pruefungssoftware)

Valuatic-Exporte enthalten Pruefer- und Kandidatendaten in derselben Datei. Damit beide unabhaengig verschluesselt werden, verwenden sie eigene kanonische Schluessel (z.B. `examiner_nachname` statt `familienname`).

### Examiner ID

| Alias | Herkunft |
|---|---|
| `examiner_id` | Valuatic (Snake Case) |
| `Examiner_ID` | Valuatic (Mixed Case) |
| `EXAMINER_ID` | Valuatic (Grossbuchstaben) |

### Examiner Nachname

| Alias | Herkunft |
|---|---|
| `examiner_last_name` | Valuatic (Snake Case) |
| `Examiner_Last_Name` | Valuatic (Mixed Case) |
| `EXAMINER_LAST_NAME` | Valuatic (Grossbuchstaben) |

### Examiner Vorname

| Alias | Herkunft |
|---|---|
| `examiner_first_name` | Valuatic (Snake Case) |
| `Examiner_First_Name` | Valuatic (Mixed Case) |
| `EXAMINER_FIRST_NAME` | Valuatic (Grossbuchstaben) |

### Candidate ID

| Alias | Herkunft |
|---|---|
| `candidate_id` | Valuatic (Snake Case) |
| `Candidate_ID` | Valuatic (Mixed Case) |
| `CANDIDATE_ID` | Valuatic (Grossbuchstaben) |

### Candidate Nachname

| Alias | Herkunft |
|---|---|
| `candidate_last_name` | Valuatic (Snake Case) |
| `Candidate_Last_Name` | Valuatic (Mixed Case) |
| `CANDIDATE_LAST_NAME` | Valuatic (Grossbuchstaben) |

### Candidate Vorname

| Alias | Herkunft |
|---|---|
| `candidate_first_name` | Valuatic (Snake Case) |
| `Candidate_First_Name` | Valuatic (Mixed Case) |
| `CANDIDATE_FIRST_NAME` | Valuatic (Grossbuchstaben) |


## NAME-Spalte (optional)

Die `NAME`-Spalte wird gesondert behandelt:

| Alias | Herkunft |
|---|---|
| `NAME` | Allgemein |
| `Name` | Allgemein |
| `name` | Kleinschreibung |

**Erkennung als Zusammensetzung:** Falls eine `NAME`-Spalte existiert und deren Inhalt in der ersten Datenzeile der Kombination aus `FAMILIENNAME VORNAME` (oder `VORNAME FAMILIENNAME`) entspricht, wird sie als zusammengesetzt erkannt.

**Verhalten:** Die `NAME`-Spalte wird nicht einzeln verschluesselt, sondern automatisch aus den verschluesselten Einzelwerten von Familienname und Vorname zusammengesetzt. Format: `<verschluesselter_Familienname> <verschluesselter_Vorname>`.


## Nicht erkannte Spalten

Spalten, die nicht als Identitaetsspalten erkannt werden, bleiben **vollstaendig unveraendert**. Beispiele:

- Adresse, PLZ, Ort
- Noten, Punkte, Bewertungen
- Fach, Kurs, Semester
- Beliebige andere Spalten

Es muessen nicht alle Spaltentypen vorhanden sein. Das Tool verschluesselt nur die Spalten, die es erkennt.


## Neuen Alias hinzufuegen

Um einen neuen Spaltennamen zu erkennen:

1. `COLUMN_ALIASES` in `pseudonym.py` erweitern
2. `COLUMN_ALIASES` in `pseudonym_gui.html` erweitern
3. Info-Popup-Tabelle in `pseudonym_gui.html` aktualisieren
4. Diese Spalten-Referenz aktualisieren
5. Tabelle in `ANLEITUNG_pseudonym.md` aktualisieren
6. Tabelle in `README.md` aktualisieren
