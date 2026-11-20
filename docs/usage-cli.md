# CLI Referenz

## Syntax

```
python pseudonym.py {encrypt|decrypt|anonymize} EINGABE [EINGABE ...] [--secret SECRET]
                    [--output PFAD] [--output-dir DIR] [--zip] [--sep ZEICHEN] [--extra-cols SPALTEN]
```

## Argumente

| Argument | Pflicht | Beschreibung |
|---|---|---|
| `encrypt` / `decrypt` / `anonymize` | Ja | `encrypt` = pseudonymisieren, `decrypt` = zurueckfuehren, `anonymize` = Identitaetsspalten endgueltig leeren |
| `EINGABE [EINGABE ...]` | Ja | Dateien (CSV, TSV, TXT, XLSX, XLSM, ZIP), Ordner oder Platzhalter wie `*.csv` |
| `--secret SECRET` | Nein | Geheimer Schluessel. Besser weglassen, siehe [Secret eingeben](#secret-eingeben) |
| `--output PFAD`, `-o` | Nein | Ausgabepfad. Nur moeglich, wenn genau eine Datei verarbeitet wird |
| `--output-dir DIR` | Nein | Ausgabeverzeichnis. Wird angelegt, wenn es fehlt |
| `--zip` | Nein | Alle Ergebnisdateien zusaetzlich in ein ZIP-Archiv buendeln (auch bei einer einzelnen Datei) |
| `--sep ZEICHEN`, `-s` | Nein | CSV-Trennzeichen, z.B. `;` oder `\t` fuer Tab. Standard: automatische Erkennung |
| `--extra-cols SPALTEN` | Nein | Zusaetzliche Spalten verarbeiten (kommagetrennt) |
| `--version` | Nein | Versionsnummer anzeigen und melden, falls ein Python-Paket fehlt |
| `--help`, `-h` | Nein | Hilfe anzeigen |

Ohne `--output` und `--output-dir` liegt das Ergebnis neben der Eingabedatei: `<name>_pseudo.<ext>`, `<name>_restored.<ext>` oder `<name>_anonym.<ext>`.


## Secret eingeben

Lassen Sie `--secret` weg. Das Programm fragt dann verdeckt nach dem Secret:

```bash
python pseudonym.py encrypt studenten.csv
Secret:
Secret wiederholen:
```

Beim Verschluesseln fragt das Programm zweimal, damit ein Tippfehler auffaellt. Ein Tippfehler wuerde die Datei mit einem Secret verschluesseln, das niemand kennt.

Weitere Wege:

- **Umgebungsvariable `PSEUDONYM_SECRET`:** fuer Skripte. Das Programm fragt dann nicht nach.
- **`--secret "..."`:** funktioniert weiter. Das Secret steht dann aber im Verlauf der Konsole (bash, PowerShell) und waehrend des Laufs in der Prozessliste. Nur verwenden, wenn das unbedenklich ist.

Die Beispiele auf dieser Seite lassen `--secret` weg.


## Beispiele

### Verschluesseln

```bash
python pseudonym.py encrypt studenten.csv
python pseudonym.py encrypt zuteilung.xlsx
```
Erzeugt `studenten_pseudo.csv` und `zuteilung_pseudo.xlsx`. In Excel-Dateien werden alle Blaetter mit erkannten Spalten verarbeitet. Die Formatierung bleibt erhalten.

### Entschluesseln

```bash
python pseudonym.py decrypt studenten_pseudo.csv
```
Erzeugt `studenten_pseudo_restored.csv`.

### Eigener Ausgabepfad

```bash
python pseudonym.py encrypt eingabe.csv --output /pfad/zu/ausgabe.csv
```

### Roundtrip pruefen

```bash
python pseudonym.py encrypt original.csv
python pseudonym.py decrypt original_pseudo.csv
diff original.csv original_pseudo_restored.csv
# Keine Ausgabe = byte-identisch
```

Unter Windows vergleicht `fc.exe /b original.csv original_pseudo_restored.csv` die beiden Dateien. Erwartet ist "Keine Unterschiede gefunden".

Die Ausnahmen stehen unter [CSV-Formaterhaltung](#csv-formaterhaltung). Meldet das Programm beim Entschluesseln "Ausgabe als UTF-8 mit BOM", beginnt die Datei mit drei zusaetzlichen Bytes (`EF BB BF`). Ein Byte-Vergleich listet dann fast jede Stelle auf, weil alles um drei Bytes verschoben ist. Der Text ist trotzdem gleich.


## Anonymisieren

```bash
python pseudonym.py anonymize studenten.csv
python pseudonym.py anonymize zuteilung.xlsx --extra-cols "Kommentar"
```

Erzeugt `studenten_anonym.csv`. Der Modus leert alle Zellen der erkannten Spalten und der Zusatzspalten. Die Kopfzeile und alle anderen Spalten bleiben. Es gibt kein Secret und keinen Weg zurueck.

Das Werkzeug entfernt nur, was es erkennt. Bitte pruefen Sie vor der Weitergabe:

- **Uebrige Spalten:** Freitext, Gruppe, Termin und Punkte koennen in kleinen Gruppen eine Person erkennbar machen.
- **Zeilen vor der Kopfzeile:** Sie bleiben unveraendert, auch wenn dort ein Name steht. Das Programm warnt in diesem Fall.
- **Zeilenfolge:** Existiert die Originaldatei mit gleicher Zeilenfolge, laesst sich jede Zeile ueber ihre Position zuordnen.
- **Dateiname:** Ein Name im Dateinamen bleibt.

In Excel-Dateien ersetzt der Modus zusaetzlich die Dateieigenschaften "Autor" und "Zuletzt geaendert von" und entfernt Kommentare an geleerten Zellen.


## Batch-Modus

Mehrere Dateien koennen in einem Aufruf verarbeitet werden. Eine feste Obergrenze gibt es nicht. Getestet sind 500 Dateien in einem Lauf (rund 15 Sekunden, 65 MB Arbeitsspeicher). Die Dateien werden nacheinander verarbeitet. Der Speicherbedarf richtet sich deshalb nach der groessten Datei, nicht nach der Anzahl.

### Mehrere Dateien

```bash
python pseudonym.py encrypt datei1.csv datei2.xlsx
```

### Ordner

```bash
python pseudonym.py encrypt exporte/ --output-dir pseudonymisiert/
```

Verarbeitet alle CSV-, TSV-, XLSX- und XLSM-Dateien im Ordner (ohne Unterordner). Versteckte Dateien, Excel-Sperrdateien (`~$...`) und `.txt` zaehlen nicht mit.

### Platzhalter

```bash
python pseudonym.py encrypt "*.csv" --output-dir pseudonymisiert/
```

Das Programm loest Platzhalter selbst auf. Das funktioniert deshalb auch in der Windows-Eingabeaufforderung und in PowerShell.

Bei Ordnern und Platzhaltern ueberspringt das Programm Ergebnisse frueherer Laeufe (`..._pseudo`, `..._restored`, `..._anonym`), damit nichts doppelt verschluesselt wird. Beim Entschluesseln ueberspringt es nur `..._restored` und `..._anonym`. Ausdruecklich genannte Dateien werden immer verarbeitet.

### ZIP-Eingabe

```bash
python pseudonym.py encrypt archiv.zip
```

Entpackt die enthaltenen CSV-, TSV-, XLSX- und XLSM-Dateien in einen temporaeren Ordner und verarbeitet sie. Der temporaere Ordner wird am Ende geloescht, auch nach einem Fehler. Die Ergebnisse liegen neben dem ZIP (bzw. in `--output-dir`).

### ZIP-Ausgabe

```bash
python pseudonym.py encrypt exporte/ --zip
```

Buendelt die Ergebnisse zusaetzlich in ein ZIP-Archiv. Name des Archivs:

- Alle Dateien stammen aus einem ZIP: `<ZIP-Name>_pseudo.zip` (bzw. `_restored.zip`, `_anonym.zip`)
- Sonst: gemeinsamer Anfang der Dateinamen, Modus, Anzahl und Datum, z.B. `Teilnehmerliste_pseudo_9Dateien_2026-10-06.zip` (ohne gemeinsamen Anfang: `Batch_pseudo_...`)

### Gleiche Dateinamen

Heissen zwei Eingabedateien gleich (z.B. `x/liste.csv` und `y/liste.csv` mit `--output-dir`), bekommt die zweite Ausgabe eine Nummer: `liste_pseudo.csv` und `liste_pseudo_1.csv`.

### Fehler in einzelnen Dateien

Ein Fehler in einer Datei bricht den Lauf nicht ab. Das Programm verarbeitet die uebrigen Dateien und nennt am Ende jede fehlgeschlagene Datei mit Grund:

```
==================================================
Batch abgeschlossen: 500 erfolgreich, 3 fehlgeschlagen
  FEHLER: fach.csv: Keine Spalten mit Personendaten erkannt. Es wurde keine Datei geschrieben. ...
==================================================
```

Der Rueckgabecode ist 0, wenn alle Dateien verarbeitet wurden, sonst 1.


## Zusaetzliche Spalten

Neben den automatisch erkannten Identitaetsspalten koennen weitere Spalten angegeben werden:

```bash
python pseudonym.py encrypt datei.csv --extra-cols "Kommentar,Notiz"
```

- Gross-/Kleinschreibung spielt keine Rolle
- Fehlt eine angegebene Spalte in einer Datei, nennt das Programm sie in einer Warnung
- Bereits automatisch erkannte Spalten werden nicht doppelt verschluesselt
- **Beim Entschluesseln dieselben Spalten wieder angeben.** Sonst bleiben sie verschluesselt


## Was das Programm erkennt und prueft

- **Fehlende Python-Pakete:** Fehlt `cryptography` oder `openpyxl`, bricht das Programm vor der Secret-Abfrage ab und nennt den Installationsbefehl. `anonymize` braucht `cryptography` nicht, CSV-Dateien brauchen `openpyxl` nicht.
- **Trennzeichen:** Semikolon, Komma oder Tab. Das Programm waehlt das Trennzeichen, mit dem die Kopfzeile die meisten erkannten Spalten hat. `--sep` legt es fest.
- **Kopfzeile:** Unter den ersten 20 Zeilen gilt die Zeile mit den meisten erkannten Spalten als Kopfzeile. Zeilen davor (z.B. in MLW-Exporten) bleiben unveraendert.
- **Mehrere Spalten je Typ:** `Telefon` und `Handy` oder `Vorname.x` und `Vorname.y` werden alle verarbeitet.
- **Keine erkannte Spalte:** Das Programm schreibt keine Datei und nennt die vorhandenen Spaltennamen.
- **Falsches Secret:** Laesst sich kein Wert entschluesseln, schreibt das Programm keine Datei und meldet das. Die Pruefung ist exakt, weil jedes Pseudonym einen Pruefwert enthaelt.
- **Gemischte Dateien:** Zellen ohne gueltiges Pseudonym (z.B. nachgetragene Klartextzeilen) bleiben beim Entschluesseln unveraendert. Das Programm nennt ihre Anzahl.
- **Schon verschluesselt:** Sind Zellen bereits mit demselben Secret pseudonymisiert, warnt das Programm.
- **Verrutschte Spalten:** Hat eine Zeile mehr Zellen als die Kopfzeile, warnt das Programm. Dort kann ein Wert in einer falschen Spalte stehen.


## Unterstuetzte Dateiformate

| Endung | Format |
|---|---|
| `.csv`, `.tsv`, `.txt` | Text mit Trennzeichen. Kodierung: UTF-8 (mit/ohne BOM), UTF-16 LE/BE (mit/ohne BOM), Windows-1252 |
| `.xlsx` | Excel-Datei |
| `.xlsm` | Excel-Datei mit Makros (Makros bleiben erhalten) |
| `.zip` | Archiv mit den obigen Formaten (ohne `.txt`) |

Das alte Format `.xls` und kennwortgeschuetzte Excel-Dateien werden nicht gelesen. Bitte in Excel ohne Kennwort als `.xlsx` speichern.


## Ausgabeformat

### CSV-Formaterhaltung

Das Programm ersetzt nur den Inhalt der betroffenen Zellen. Alles andere bleibt Zeichen fuer Zeichen erhalten:

- Kodierung und BOM
- Zeilenenden (CRLF oder LF), auch ein fehlendes Zeilenende am Dateischluss
- Anfuehrungszeichen, auch wenn nur einzelne Zellen welche haben
- Leerzeichen am Rand einer Zelle (sie stehen ausserhalb des Pseudonyms)
- Zeilen vor der Kopfzeile, Leerzeilen, zu kurze und zu lange Zeilen, doppelte und leere Spaltennamen

Ein Encrypt-Decrypt-Roundtrip liefert deshalb eine **byte-identische** Datei. Zwei Ausnahmen:

1. **Pseudonym-Datei ohne Umlaute:** Standen alle Umlaute in verschluesselten Spalten, besteht die Pseudonym-Datei nur aus ASCII-Zeichen. Die urspruengliche Kodierung ist dann nicht mehr erkennbar. Die zurueckgefuehrte Datei ist UTF-8 mit BOM, damit Excel die Umlaute richtig zeigt. Der Text ist gleich, die Bytes koennen abweichen.
2. **Zeichen passt nicht in die Kodierung:** Enthaelt ein zurueckgefuehrter Wert ein Zeichen, das die Kodierung der Datei nicht kennt (z.B. `Č` in Windows-1252), ist die Ausgabe UTF-8 mit BOM. Das Programm warnt.

### XLSX-Formaterhaltung

- Zellformatierung, bedingte Formatierung, Zahlenformate und Formeln bleiben erhalten
- Alle Blaetter bleiben in der Datei. Blaetter ohne erkannte Spalten bleiben unveraendert; das Programm nennt sie
- Makros in `.xlsm` bleiben erhalten

Zahlen und Datumswerte in Identitaetsspalten:

- Verschluesselt wird die Textform des Werts: die Zahl `1234567` als `1234567`, ein Datum als `2000-01-31 00:00:00`.
- Zurueckgefuehrte Zellen sind Text. Aus der Zahl `1234567` wird der Text `1234567`.
- Zeigt Excel eine Zahl nur durch ein Zahlenformat mit fuehrender Null an (`01234567`), wird trotzdem `1234567` verschluesselt. Das Pseudonym unterscheidet sich dann von dem des Textes `01234567` aus einer CSV-Datei. Fuer gleiche Pseudonyme ueber Dateien hinweg die Spalte in Excel als Text fuehren.


## Konsolenausgabe

```
Pseudonymisierung abgeschlossen.
  Eingabe:    studenten.csv
  Ausgabe:    studenten_pseudo.csv
  Zeilen:     150
  Spalten:    Familienname, Vorname, Name, Matrikelnummer, E-Mail
  Kodierung:  UTF-8 (BOM), Trennzeichen ';'
  Metadaten:  2 Zeile(n) vor der Kopfzeile (unveraendert)
  Zellen:     750 verarbeitet (AES-256-CBC, deterministisch, PBKDF2)

  Zum Zurueckfuehren:
  python pseudonym.py decrypt "studenten_pseudo.csv"
```

Bei Excel-Dateien pro Blatt:

```
  Blaetter:
    + Teilnehmer (Matrikelnummer, Familienname, Vorname: 450 Zellen)
    + Pruefer (Examiner: 12 Zellen)
    - Legende (keine Spalten mit Personendaten erkannt: Kuerzel, Bedeutung)
  Zellen:     462 verarbeitet (AES-256-CBC, deterministisch, PBKDF2)
  WARNUNG: Nicht verarbeitete Blaetter bleiben unveraendert in der Datei: Legende (...)
```


## Naechste Schritte

- [Spalten-Referenz](column-reference.md) — welche Spalten erkannt werden
- [Troubleshooting](troubleshooting.md) — bei Problemen
