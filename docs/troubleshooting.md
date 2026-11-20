# Troubleshooting

## Haeufige Probleme

### "Keine Spalten mit Personendaten erkannt"

**Symptom:** Das Tool schreibt keine Datei und nennt die vorhandenen Spaltennamen.

**Ursachen und Loesungen:**

1. **Spaltenname ist nicht bekannt:** Pruefen Sie, ob Ihre Spaltennamen in der [Spalten-Referenz](column-reference.md) stehen. Gross-/Kleinschreibung spielt keine Rolle, aber der Name muss einem Alias entsprechen. Andere Spalten geben Sie mit `--extra-cols "Spalte1,Spalte2"` an. In der GUI klicken Sie auf die Spaltenueberschrift.

2. **Falsches CSV-Trennzeichen:** Das Tool erkennt Semikolon, Komma und Tab automatisch. Zeigt die Meldung alle Spaltennamen als einen einzigen langen Namen, hat die Datei ein anderes Trennzeichen. Loesung:
   ```bash
   python pseudonym.py encrypt datei.csv --sep "|"
   ```

3. **Kodierung:** Erkannt werden UTF-8 (mit/ohne BOM), UTF-16 (mit/ohne BOM, z.B. Webex) und Windows-1252/ANSI (z.B. MedCampus- und Excel-CSV-Exporte).


### Eine Spalte mit Personendaten bleibt im Klartext

**Moegliche Ursachen:**

1. **Der Spaltenname ist nicht bekannt.** Das Tool verarbeitet nur erkannte Spalten. Pruefen Sie die Ausgabe: Die Zeile "Spalten:" nennt alle verarbeiteten Spalten. In der GUI sind sie in der Vorschau blau.
2. **Eine Zeile hat mehr Zellen als die Kopfzeile.** Das passiert, wenn ein Wert das Trennzeichen enthaelt und nicht in Anfuehrungszeichen steht. Die Werte dieser Zeile stehen dann in falschen Spalten. Das Tool warnt: "... Zeile(n) haben mehr Zellen als die Kopfzeile". Bitte die Datei korrigieren.
3. **Der Name steht vor der Kopfzeile.** Zeilen vor der Kopfzeile bleiben immer unveraendert.


### "Kein Wert konnte entschluesselt werden"

**Symptom:** Beim Entschluesseln schreibt das Tool keine Datei.

**Ursache:** Das Secret stimmt nicht, oder die Datei ist nicht pseudonymisiert. Pruefen Sie:

- Leerzeichen am Anfang oder Ende des Secrets
- Gross-/Kleinschreibung
- Sonderzeichen. Bei der verdeckten Eingabe gibt es damit keine Probleme. Bei `--secret` in der Shell Anfuehrungszeichen verwenden
- Zusatzspalten: Beim Entschluesseln muessen dieselben Spalten angegeben sein wie beim Verschluesseln

Das Tool erkennt ein falsches Secret sicher, weil jedes Pseudonym einen Pruefwert enthaelt.


### "... Zelle(n) enthalten kein gueltiges Pseudonym"

**Symptom:** Warnung beim Entschluesseln. Die Datei wird geschrieben.

**Ursache:** Einige Zellen der Identitaetsspalten sind kein Pseudonym dieses Secrets, zum Beispiel nachgetragene Klartextzeilen. Diese Zellen bleiben unveraendert.


### "... Zelle(n) waren bereits mit diesem Secret pseudonymisiert"

**Symptom:** Warnung beim Verschluesseln.

**Ursache:** Die Datei ist schon pseudonymisiert und wurde ein zweites Mal verschluesselt. Zweimal entschluesseln stellt das Original wieder her. Bei Ordnern und Platzhaltern ueberspringt die CLI Dateien mit dem Zusatz `_pseudo` von selbst.


### CSV-Datei sieht nach Roundtrip anders aus

**Symptom:** Encrypt → Decrypt ergibt keine byte-identische Datei.

**Moegliche Ursachen:**

1. **UTF-8 mit BOM statt der urspruenglichen Kodierung:** Bestand die Pseudonym-Datei nur aus ASCII-Zeichen (alle Umlaute standen in verschluesselten Spalten), ist die urspruengliche Kodierung nicht mehr erkennbar. Die zurueckgefuehrte Datei ist dann UTF-8 mit BOM, damit Excel die Umlaute richtig zeigt. Der Text ist gleich. Das Tool meldet den Fall ("Ausgabe als UTF-8 mit BOM"). Ein Byte-Vergleich mit `fc /b` oder `cmp` listet dann fast jede Stelle auf, weil die drei Bytes am Anfang (`EF BB BF`) alles verschieben.
2. **Zeichen passt nicht in die Kodierung:** Das Tool warnt und schreibt UTF-8 mit BOM.
3. **Anderes Trennzeichen oder andere Zusatzspalten** beim Entschluesseln als beim Verschluesseln.

Leerzeichen am Zellrand und gemischte Anfuehrungszeichen bleiben erhalten.


### Excel: Zahlen sind nach dem Zurueckfuehren Text

**Ursache:** Ein Pseudonym ist Text. Beim Zurueckfuehren kennt das Tool den urspruenglichen Zelltyp nicht mehr. Betroffen sind nur die Identitaetsspalten (z.B. eine Matrikelnummer, die als Zahl gespeichert war). Alle anderen Spalten behalten Typ und Format.


### Excel: Gleiche Matrikelnummer, anderes Pseudonym als in der CSV-Datei

**Ursache:** In der Excel-Datei ist die Matrikelnummer eine Zahl (`1234567`), die nur durch ein Zahlenformat mit fuehrender Null erscheint. In der CSV-Datei steht der Text `01234567`. Das Tool verschluesselt den gespeicherten Wert.

**Loesung:** Die Spalte in Excel als Text fuehren, oder beide Dateien aus derselben Quelle im selben Format exportieren.


### Excel-Datei kann nicht gelesen werden

**Symptom:** "Die Datei ist keine lesbare Excel-Datei (.xlsx/.xlsm)".

**Ursachen und Loesungen:**

1. **Kennwortschutz:** Den Kennwortschutz in Excel entfernen und neu speichern.
2. **Altes Format `.xls`:** In Excel als `.xlsx` speichern.
3. **Beschaedigte Datei:** In Excel oeffnen und neu speichern.

Verweise auf fehlende Zeichnungen repariert die CLI selbst. Sie entfernt nur die defekten Verweise; vorhandene Diagramme und Bilder bleiben.


### "Python-Paket 'cryptography' fehlt oder laesst sich nicht laden"

**Symptom:** Das Tool verarbeitet nichts und nennt einen Befehl mit `-m pip install`.

**Ursache:** Dem Python, das gerade laeuft, fehlt ein Paket. `cryptography` braucht das Tool zum Ver- und Entschluesseln, `openpyxl` fuer Excel-Dateien.

**Loesung:** Den Befehl aus der Meldung kopieren und ausfuehren, danach den urspruenglichen Befehl wiederholen. Der Befehl nennt den vollen Pfad des laufenden Python. Das ist wichtig, wenn mehrere Python-Versionen installiert sind: Ein einfaches `pip install` kann die Pakete in eine andere Version legen. Unter Windows zeigt `py -0p` alle installierten Versionen; `py -3.10 pseudonym.py ...` startet eine bestimmte.


### "Kein Zugriff auf ..."

**Ursache:** Die Datei ist in Excel geoeffnet oder schreibgeschuetzt. Excel schliessen und erneut versuchen.


### Browser-GUI: "Diese Datei ist unvollstaendig"

**Ursache:** Die Seite enthaelt ihre Programmbibliotheken am Ende der Datei. Fehlen sie, wurde `pseudonym_gui.html` nicht vollstaendig heruntergeladen oder beim Kopieren abgeschnitten. Die vollstaendige Datei ist rund 1,1 MB gross.

**Loesung:** Die Datei neu herunterladen. Eine Internetverbindung braucht die Seite selbst nicht.


### Browser-GUI: Datei erscheint nicht in der Liste

**Ursache:** Die Datei liess sich nicht lesen. Der Grund steht im roten Kasten "Nicht geladen" unter der Dateiliste (z.B. Format `.xls`, Kennwortschutz, beschaedigtes ZIP). Aus ZIP-Archiven uebernimmt die Seite nur `.csv`, `.tsv`, `.xlsx` und `.xlsm`.


### Browser-GUI: Verarbeitung dauert lange

**Loesung:** Die Dauer haengt von der Zahl der Zellen ab. 500 Dateien mit zusammen rund 500.000 Zellen brauchen in Chromium etwa 10 Sekunden. Ist das Browserfenster im Hintergrund, bremst der Browser die Seite; das Fenster im Vordergrund lassen. Fuer einzelne sehr grosse Excel-Dateien die Python CLI verwenden.


### Batch: "--output ist nur bei einer einzelnen Datei moeglich"

**Loesung:** `--output` / `-o` setzt einen einzelnen Ausgabepfad. Das gilt auch fuer ein ZIP mit mehreren Dateien. Stattdessen `--output-dir` verwenden:

```bash
python pseudonym.py encrypt exporte/ --output-dir ./output/
```


### Batch: "Keine verarbeitbaren Dateien gefunden"

**Ursache:** Der Ordner oder das ZIP-Archiv enthaelt keine `.csv`, `.tsv`, `.xlsx` oder `.xlsm`. `.txt` zaehlt in Ordnern und ZIP-Archiven nicht mit, weil es oft Hinweisdateien sind. Eine `.txt` mit Daten nennen Sie direkt als Eingabe. Uebersprungene Dateien nennt das Tool mit Grund ("Uebersprungen: ...").


## Fehlermeldungen

| Meldung | Bedeutung | Loesung |
|---|---|---|
| `FEHLER: Datei nicht gefunden: ...` | Pfad oder Platzhalter trifft keine Datei | Pfad pruefen |
| `Die Datei ist leer.` | Die CSV-Datei hat keinen Inhalt | Datei pruefen |
| `Keine Spalten mit Personendaten erkannt.` | Kein Spaltenname bekannt | Siehe oben |
| `Kein Wert konnte entschluesselt werden.` | Falsches Secret oder Datei nicht pseudonymisiert | Siehe oben |
| `Die Datei ist keine lesbare Excel-Datei` | Kennwortschutz, `.xls` oder beschaedigt | In Excel ohne Kennwort als `.xlsx` speichern |
| `Python-Paket '...' fehlt oder laesst sich nicht laden` | Dem laufenden Python fehlt `cryptography` oder `openpyxl` | Befehl aus der Meldung ausfuehren |
| `Unbekanntes Dateiformat` | Endung nicht `.csv`, `.tsv`, `.txt`, `.xlsx` oder `.xlsm` | Datei konvertieren |
| `--output ist nur bei einer einzelnen Datei moeglich` | `--output` mit mehreren Dateien | `--output-dir` verwenden |
| `Die beiden Eingaben stimmen nicht ueberein.` | Tippfehler bei der Wiederholung des Secrets | Erneut starten |
| `HINWEIS: Verweise auf fehlende Zeichnungen werden entfernt.` | Excel-Datei hat defekte Verweise | Kein Handlungsbedarf |


## Hilfe erhalten

Falls Ihr Problem hier nicht gelistet ist:

1. Pruefen Sie die Konsolenausgabe bzw. das Protokoll der GUI auf Hinweise
2. Stellen Sie sicher, dass alle [Voraussetzungen](installation.md) erfuellt sind
3. Testen Sie mit einer kleinen Testdatei (wenige Zeilen, erfundene Daten)
