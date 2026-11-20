# Browser-GUI Anleitung

## Starten

`pseudonym_gui.html` doppelklicken oder im Browser oeffnen. Keine Installation noetig.

**Voraussetzung:** Moderner Browser (Chrome, Firefox, Edge, Safari) und eine Internetverbindung beim Start. Die Seite laedt zwei Bibliotheken (SheetJS, JSZip) aus dem Netz. Erscheint oben der Hinweis "Die Programmbibliotheken konnten nicht geladen werden", fehlt die Verbindung.


## Bedienung

### 1. Datei laden

Datei per **Drag & Drop** auf die Dropzone ziehen oder ueber den Dateiauswahl-Dialog laden. Unterstuetzte Formate: CSV, TSV, TXT, XLSX, XLSM und ZIP.

Dateien, die sich nicht lesen lassen, nennt die Seite unter der Dateiliste ("Nicht geladen"). Das betrifft zum Beispiel das alte Format `.xls` und kennwortgeschuetzte Excel-Dateien.

### 2. Vorschau pruefen

Die Vorschau zeigt die ersten 20 Zeilen. Die erkannten Identitaetsspalten sind blau hervorgehoben. Bei Excel-Dateien mit mehreren Blaettern schalten Tabs zwischen den Blaettern um.

Pruefen Sie hier, ob die Kopfzeile und alle Spalten mit Personendaten erkannt sind. Fehlt eine Spalte, klicken Sie auf ihre Ueberschrift (siehe [Zusaetzliche Spalten](#zusaetzliche-spalten)).

### 3. Modus waehlen

- **Verschluesseln:** Ersetzt personenbezogene Daten durch Pseudonyme
- **Entschluesseln:** Stellt die Originaldaten aus Pseudonymen wieder her
- **Anonymisieren:** Leert die markierten Spalten endgueltig (siehe [Anonymisieren](#anonymisieren))

### 4. Secret eingeben

Ein beliebiges Passwort eingeben. Das Auge-Symbol zeigt oder verbirgt das Secret. Beim Anonymisieren gibt es kein Secret.

**Wichtig:** Das Secret wird **nicht gespeichert**. Es existiert nur im Arbeitsspeicher der Seite.

### 5. Trennzeichen (nur bei einer einzelnen CSV-Datei)

Die Seite erkennt das Trennzeichen automatisch (Semikolon, Komma oder Tab) und zeigt es an. Stimmt die Vorschau nicht, laesst es sich hier aendern. Bei mehreren Dateien erkennt die Seite das Trennzeichen fuer jede Datei einzeln.

### 6. Verarbeitung starten

Auf "Pseudonymisieren", "De-Pseudonymisieren" oder "Anonymisieren" klicken. Ein Fortschrittsbalken zeigt den Stand.

### 7. Ergebnis herunterladen

Nach Abschluss zeigt die Seite, wie viele Dateien und Zellen verarbeitet wurden, und bietet das Ergebnis zum Download an. Der Dateiname erhaelt den Zusatz `_pseudo`, `_restored` oder `_anonym`.

Dateien, die nicht verarbeitet werden konnten, stehen mit Grund in einem roten Kasten. Fuer sie gibt es keine Ausgabedatei. Haeufige Gruende:

- **Keine Spalten mit Personendaten erkannt.** Die Datei wird nicht unveraendert als `_pseudo` ausgegeben.
- **Falsches Secret.** Laesst sich beim Entschluesseln kein Wert entschluesseln, gibt es kein Ergebnis.

Sobald Sie Dateien, Modus, Zusatzspalten oder Trennzeichen aendern, verschwindet das alte Ergebnis. So passt der Download immer zur Anzeige.


## Anonymisieren

Der Modus leert alle Zellen der hervorgehobenen Spalten. Die Kopfzeile und alle anderen Spalten bleiben. Es gibt kein Secret und keinen Weg zurueck.

Die Seite entfernt nur, was sie erkennt. Bitte pruefen Sie vor der Weitergabe:

- **Uebrige Spalten:** Freitext, Gruppe, Termin und Punkte koennen in kleinen Gruppen eine Person erkennbar machen. Weitere Spalten lassen sich in der Vorschau anklicken.
- **Zeilen vor der Kopfzeile:** Sie bleiben unveraendert. Das Protokoll warnt in diesem Fall.
- **Zeilenfolge:** Existiert die Originaldatei mit gleicher Zeilenfolge, laesst sich jede Zeile ueber ihre Position zuordnen.
- **Dateiname:** Ein Name im Dateinamen bleibt.


## Batch-Modus

Die GUI verarbeitet mehrere Dateien in einem Durchgang. Eine feste Obergrenze gibt es nicht. Getestet sind 500 Dateien auf einmal (Chromium: rund 10 Sekunden, unter 100 MB Arbeitsspeicher). Die Grenze setzt der Arbeitsspeicher: Alle Dateien liegen gleichzeitig im Speicher der Seite. Fuer einzelne sehr grosse Excel-Dateien (ueber 50.000 Zeilen) ist die Python CLI die bessere Wahl.

### Mehrere Dateien laden

- **Mehrfachauswahl:** Im Dateiauswahl-Dialog mit Strg (Windows/Linux) oder Cmd (Mac) mehrere Dateien auswaehlen
- **Drag & Drop:** Mehrere Dateien gleichzeitig auf die Dropzone ziehen
- **ZIP-Upload:** Eine ZIP-Datei laden. Die enthaltenen CSV-, TSV-, XLSX- und XLSM-Dateien werden uebernommen. Versteckte Dateien, macOS-Hilfsdateien (`__MACOSX`) und `.txt` werden uebersprungen

### Dateiliste

Unter der Dropzone steht die Liste aller geladenen Dateien. Bei mehr als 8 Dateien ist die Liste eingeklappt.

### ZIP-Download

Bei mehreren Ergebnisdateien buendelt die Seite alle Ergebnisse in ein ZIP-Archiv:

- Dateien aus einer geladenen ZIP-Datei: `<ZIP-Name>_pseudo.zip` (bzw. `_restored.zip`, `_anonym.zip`)
- Sonst: gemeinsamer Anfang der Dateinamen, Modus, Anzahl und Datum, z.B. `Teilnehmerliste_pseudo_9Dateien_2026-10-06.zip` (ohne gemeinsamen Anfang: `Batch_pseudo_...`)

Heissen zwei Dateien gleich, bekommt die zweite eine Nummer (`liste_pseudo_1.csv`). Es geht keine Datei verloren.

### Dateiauswahl fuer Vorschau

- **Bei bis zu 8 Dateien:** Tabs zum Umschalten zwischen den Dateien
- **Bei mehr als 8 Dateien:** Auswahlliste mit Vor/Zurueck-Navigation


## Zusaetzliche Spalten

In der Vorschau koennen weitere Spalten ausgewaehlt werden:

1. **Spalte hinzufuegen:** Auf eine nicht hervorgehobene Spaltenueberschrift klicken. Sie wird blau hinterlegt
2. **Spalte entfernen:** Auf das × neben dem Spaltennamen klicken
3. **Mehrere Spalten:** Beliebig viele Spalten koennen gleichzeitig ausgewaehlt sein

Die Auswahl gilt fuer alle geladenen Dateien, in denen die Spalte vorkommt. Automatisch erkannte Spalten lassen sich nicht abwaehlen.

**Beim Entschluesseln dieselben Spalten wieder auswaehlen.** Sonst bleiben sie verschluesselt.


## Funktionen

### Vorher/Nachher-Vergleich

Nach der Verarbeitung zeigt die Seite die ersten 20 Zeilen vor und nach der Verarbeitung. Die Tabs heissen "Original" und "Pseudonymisiert" (bzw. "Wiederhergestellt", "Anonymisiert"). Geaenderte Zellen sind im Original farbig hinterlegt.

### Protokoll

Das Protokoll zeigt je Datei die verarbeiteten Spalten, die Zahl der Zellen, Warnungen und Fehler. Warnungen betreffen zum Beispiel:

- Zellen ohne gueltiges Pseudonym beim Entschluesseln (sie bleiben unveraendert)
- Zellen, die schon mit demselben Secret pseudonymisiert waren
- Zeilen mit mehr Zellen als die Kopfzeile (ein Wert kann in einer falschen Spalte stehen)
- Blaetter ohne erkannte Spalten (sie bleiben unveraendert in der Datei)

### Verlauf

Die Seite merkt sich die letzten 10 Verarbeitungen (nur Dateiname, Modus und Zeit, **nie** das Secret) im localStorage des Browsers. "Verlauf loeschen" entfernt die Eintraege.

### Dark Mode

Der Schalter oben rechts wechselt zwischen hellem und dunklem Design. Die Einstellung wird im Browser gespeichert.

### Info (?)

Das Fragezeichen neben den Modus-Schaltflaechen listet alle Spaltennamen, die die Seite erkennt. Die Liste entsteht aus dem Programmcode und ist deshalb immer vollstaendig.


## Datenschutz

- **Alle Daten bleiben lokal.** Nichts wird hochgeladen oder an Server gesendet
- Die Seite kann technisch keine Daten senden: Eine Sicherheitsrichtlinie (Content Security Policy) verbietet ihr alle Netzverbindungen, Formulare und fremde Bilder
- Die einzigen Zugriffe ins Netz sind die beiden Bibliotheken beim Start. Der Browser laedt sie nur, wenn ihre Pruefsumme stimmt (SheetJS 0.20.3 von cdn.sheetjs.com, JSZip 3.10.1 von cdnjs.cloudflare.com)
- Das Secret existiert nur im Arbeitsspeicher. Der Verlauf speichert keine Secrets und keine Dateiinhalte


## Formaterhaltung

**CSV:** Wie die Python CLI ersetzt die Seite nur den Inhalt der betroffenen Zellen. Kodierung, BOM, Zeilenenden, Anfuehrungszeichen und Leerzeichen bleiben erhalten. Die Ausgabe ist byte-gleich zur Ausgabe der CLI. Die Ausnahmen stehen in der [CLI Referenz](usage-cli.md#csv-formaterhaltung).

**Excel:** Die Seite erhaelt Werte, Zahlen, Datumswerte mit Zahlenformat, Formeln, verbundene Zellen und Spaltenbreiten. **Farben, Schriften, Rahmen und Makros gehen verloren.** Wenn die Formatierung erhalten bleiben soll, die Python CLI verwenden. Die Zellwerte sind in beiden Varianten gleich.


## Kompatibilitaet mit Python CLI

Browser-GUI und Python CLI erzeugen **identische Pseudonyme** fuer gleiche Eingaben mit gleichem Secret. Eine in der GUI verschluesselte Datei kann mit der CLI entschluesselt werden und umgekehrt. Automatische Tests vergleichen beide Varianten (siehe [Entwicklung](development.md#testen)).


## Naechste Schritte

- [Spalten-Referenz](column-reference.md) — welche Spalten erkannt werden
- [Troubleshooting](troubleshooting.md) — bei Problemen
