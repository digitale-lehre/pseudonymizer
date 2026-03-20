# Spalten-Referenz

## Uebersicht

Der pseudonymizer erkennt Identitaetsspalten automatisch anhand ihrer Spaltennamen. Die Erkennung ist **case-insensitive** — Gross-/Kleinschreibung spielt keine Rolle.

Nur erkannte Identitaetsspalten werden verschluesselt. Alle anderen Spalten bleiben unveraendert.


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
| `Last Name` | Englisch (mit Leerzeichen) |
| `LastName` | Englisch (CamelCase) |
| `FAMILY_NAME_OF_STUDENT` | SAP/MedCampus |
| `Family_Name_of_Student` | Mixed Case |
| `Familienname oder Nachname` | MLW-Export (MedLearnWiki) |

### Vorname

| Alias | Herkunft |
|---|---|
| `VORNAME` | MedCampus-Export |
| `Vorname` | Allgemein |
| `vorname` | Kleinschreibung |
| `First Name` | Englisch (mit Leerzeichen) |
| `FirstName` | Englisch (CamelCase) |
| `Firstname` | Englisch |
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
| `MatrNr` | CamelCase-Kurzform |
| `Matrikel` | Kurzform |
| `matrikel`, `MATRIKEL` | Varianten |
| `StudentID` | Englisch |
| `Student_ID` | Englisch (Underscore) |
| `REGISTRATION_NUMBER` | SAP/MedCampus |
| `Registration_Number` | Mixed Case |
| `Registration Number` | Englisch (mit Leerzeichen) |

### E-Mail

| Alias | Herkunft |
|---|---|
| `EMAIL_ADDRESS` | SAP/MedCampus |
| `Email_Address` | Mixed Case |
| `E-Mail` | Deutsch |
| `E-MAIL` | Deutsch (Grossbuchstaben) |
| `e-mail` | Kleinschreibung |
| `Email` | Englisch |
| `email`, `EMAIL` | Varianten |
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

> **Hinweis:** Im Gegensatz zur `NAME`-Spalte wird `Anzeigename` / `Display Name` als eigenstaendige Identitaetsspalte verschluesselt, nicht als Zusammensetzung. Dies ist notwendig, da der Anzeigename in Webex-Exports nicht immer mit Vorname + Nachname uebereinstimmt (z.B. bei Gaesten, Titel, oder wenn Vorname/Nachname "N/A" ist).


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

- Geburtsdatum, Adresse, Telefonnummer
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
