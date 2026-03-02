# Browser-GUI Anleitung

## Starten

`pseudonym_gui.html` doppelklicken oder im Browser oeffnen. Keine Installation noetig.

**Voraussetzung:** Moderner Browser (Chrome, Firefox, Edge, Safari). Internetverbindung beim ersten Start fuer CDN-Bibliotheken.


## Bedienung

### 1. Datei laden

Datei per **Drag & Drop** auf die Dropzone ziehen oder ueber den Dateiauswahl-Dialog laden. Unterstuetzte Formate: CSV und XLSX.

Bei XLSX-Dateien mit mehreren Sheets werden alle Sheets angezeigt und verarbeitet.

### 2. Vorschau pruefen

Nach dem Laden zeigt die GUI eine Vorschau der ersten 20 Zeilen. Identitaetsspalten werden farblich hervorgehoben. Bei Multi-Sheet-XLSX koennen einzelne Sheets per Tab umgeschaltet werden.

### 3. Secret eingeben

Ein beliebiges Passwort eingeben. Das Auge-Symbol rechts neben dem Eingabefeld zeigt/verbirgt das Secret.

**Wichtig:** Das Secret wird **nicht gespeichert** — nur im Arbeitsspeicher waehrend der Verarbeitung.

### 4. Modus waehlen

- **Verschluesseln:** Ersetzt personenbezogene Daten durch Pseudonyme
- **Entschluesseln:** Stellt die Originaldaten aus Pseudonymen wieder her

### 5. Optionale Einstellungen

- **CSV-Trennzeichen:** Standard ist Komma. Fuer Semikolon-CSV auf `;` aendern.

### 6. Verarbeitung starten

"Verschluesseln" oder "Entschluesseln" klicken. Ein Fortschrittsbalken zeigt den Verarbeitungsstand.

### 7. Ergebnis herunterladen

Nach Abschluss wird die Ergebnisdatei zum Download angeboten. Der Dateiname erhaelt automatisch das Suffix `_pseudo` (Verschluesselung) oder `_restored` (Entschluesselung).


## Funktionen

### Vorher/Nachher-Vergleich

Nach der Verarbeitung zeigt die GUI einen Vergleich der Daten vor und nach der Verschluesselung. Ueber Tabs koennen "Vorher" und "Nachher" umgeschaltet werden.

### Verarbeitungsprotokoll

Ein ausklappbares Protokoll zeigt jeden Verarbeitungsschritt:
- Schluesselableitung
- Sheet-Erkennung
- Spalten-Erkennung
- Anzahl verarbeiteter Zellen
- Fehlermeldungen (falls vorhanden)

### Verlauf

Die GUI speichert die letzten 10 Verarbeitungen (nur Dateiname, Modus und Zeitstempel — **nie** das Secret). Der Verlauf wird im localStorage des Browsers gespeichert.

### Dark Mode

Ueber den Schalter oben rechts kann zwischen hellem und dunklem Design umgeschaltet werden. Die Einstellung wird im Browser gespeichert.


## Datenschutz

- **Alle Daten bleiben lokal** — nichts wird hochgeladen oder an Server gesendet
- Das Secret existiert nur im Arbeitsspeicher waehrend der Verarbeitung
- Der Verlauf speichert keine Secrets oder Dateiinhalte
- Die einzigen externen Verbindungen sind CDN-Downloads (PapaParse, SheetJS) beim ersten Start


## CSV-Formaterhaltung

Wie die Python CLI erhaelt auch die Browser-GUI das Originalformat:

- BOM (Byte Order Mark)
- Quoting-Stil (QUOTE_ALL oder QUOTE_MINIMAL)
- Zeilenumbrueche (CRLF oder LF)


## Kompatibilitaet mit Python CLI

Browser-GUI und Python CLI erzeugen **identische Pseudonyme** fuer gleiche Eingaben mit gleichem Secret. Eine in der GUI verschluesselte Datei kann mit der CLI entschluesselt werden und umgekehrt.


## Naechste Schritte

- [Spalten-Referenz](column-reference.md) — welche Spalten erkannt werden
- [Troubleshooting](troubleshooting.md) — bei Problemen
