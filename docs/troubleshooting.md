# Troubleshooting

## Haeufige Probleme

### "Keine Identitaetsspalten gefunden"

**Symptom:** Das Tool meldet, dass keine Identitaetsspalten erkannt wurden.

**Ursachen und Loesungen:**

1. **Spaltennamen stimmen nicht ueberein:** Pruefen Sie, ob Ihre Spaltennamen in der [Spalten-Referenz](column-reference.md) aufgefuehrt sind. Die Erkennung ist case-insensitive, aber der Name muss exakt einem Alias entsprechen.

2. **Falsches CSV-Trennzeichen:** Falls die CSV-Datei Semikolons statt Kommas verwendet, wird die gesamte Zeile als eine Spalte gelesen. Loesung:
   ```bash
   python pseudonym.py encrypt datei.csv --secret "..." --sep ";"
   ```

3. **BOM-Probleme:** Manche Excel-Exporte erzeugen eine BOM am Dateianfang. Das Tool behandelt dies automatisch, aber bei ungewoehnlichen Kodierungen kann es zu Problemen kommen.


### Entschluesselung liefert unleserliche Zeichen

**Symptom:** Nach der Entschluesselung stehen immer noch Base64-Strings in den Zellen.

**Ursache:** Der Secret stimmt nicht exakt ueberein. Pruefen Sie:

- Leerzeichen am Anfang oder Ende des Secrets
- Gross-/Kleinschreibung
- Sonderzeichen (besonders in der Shell: Anfuehrungszeichen verwenden)

**Hinweis:** Das Tool gibt bei falschem Secret keinen Fehler aus — es gibt den Token stattdessen unveraendert zurueck. Dies ist beabsichtigt, um Datenverlust zu vermeiden.


### CSV-Datei sieht nach Roundtrip anders aus

**Symptom:** Encrypt → Decrypt ergibt keine byte-identische Datei.

**Moegliche Ursachen:**

1. **Anderes Trennzeichen:** Beim Encrypt und Decrypt das gleiche `--sep` verwenden.
2. **Leerzeichen in Werten:** Fuehrende/nachfolgende Leerzeichen in Identitaetsspalten werden beim Encrypt getrimmt.
3. **Leere Werte:** Leere Zellen werden nicht verschluesselt und bleiben leer.


### XLSX-Datei kann nicht geoeffnet werden

**Symptom:** openpyxl wirft einen Fehler beim Oeffnen der XLSX-Datei.

**Loesung:** Das Tool repariert automatisch fehlerhafte Drawing-Referenzen. Falls der Fehler dennoch auftritt:

1. Datei in Excel oeffnen und neu speichern
2. Erneut versuchen

Falls die Datei kennwortgeschuetzt ist: Der pseudonymizer kann keine verschluesselten XLSX-Dateien oeffnen. Entfernen Sie den Kennwortschutz in Excel vor der Verarbeitung.


### Browser-GUI zeigt keine Vorschau

**Symptom:** Die Datei wird geladen, aber keine Tabelle angezeigt.

**Moegliche Ursachen:**

1. **CDN-Bibliotheken nicht geladen:** Internetverbindung pruefen (beim ersten Start noetig)
2. **Browser zu alt:** Einen aktuellen Chrome, Firefox, Edge oder Safari verwenden
3. **Grosse Datei:** Bei sehr grossen Dateien kann das Laden einige Sekunden dauern


### Browser-GUI: Fortschrittsbalken haengt

**Symptom:** Der Fortschrittsbalken bleibt bei einem bestimmten Prozentsatz stehen.

**Loesung:** Bei grossen Dateien (> 10.000 Zeilen) kann die Verarbeitung im Browser laenger dauern. Abwarten oder fuer sehr grosse Dateien die Python CLI verwenden.


### Batch: "--output nur bei einzelner Datei moeglich"

**Symptom:** Fehlermeldung bei Verwendung von `--output` mit mehreren Dateien.

**Loesung:** `--output` / `-o` setzt einen einzelnen Ausgabepfad und funktioniert nur bei einer Datei. Fuer Batch-Verarbeitung stattdessen `--output-dir` verwenden:

```bash
python pseudonym.py encrypt *.csv --secret "..." --output-dir ./output/
```


### Batch: "Keine verarbeitbaren Dateien gefunden"

**Symptom:** ZIP-Datei wird als Eingabe akzeptiert, aber es werden keine Dateien verarbeitet.

**Ursache:** Das ZIP-Archiv enthaelt keine CSV- oder XLSX-Dateien. Nur `.csv`, `.tsv` und `.xlsx` werden aus ZIP-Archiven extrahiert (`.txt` wird in ZIPs uebersprungen, da es oft README-Dateien sind).


### Browser-GUI: ZIP-Upload funktioniert nicht

**Symptom:** ZIP-Datei wird hochgeladen, aber keine Dateien erscheinen in der Liste.

**Moegliche Ursachen:**

1. **ZIP-Datei ist beschaedigt:** Archiv pruefen (z.B. mit `unzip -t archiv.zip`)
2. **Keine CSV/XLSX im Archiv:** Nur `.csv`, `.tsv`, `.txt` und `.xlsx` Dateien werden extrahiert
3. **JSZip nicht geladen:** Internetverbindung pruefen (JSZip wird wie PapaParse und SheetJS via CDN geladen)


## Fehlermeldungen

| Meldung | Bedeutung | Loesung |
|---|---|---|
| `FEHLER: Datei nicht gefunden` | Dateipfad existiert nicht | Pfad pruefen |
| `FEHLER: Konnte keine Spalten erkennen` | CSV-Datei ist leer oder fehlerhaft | Datei pruefen |
| `FEHLER: Keine Identitaetsspalten gefunden` | Spaltennamen nicht erkannt | Siehe oben |
| `FEHLER: Unbekanntes Dateiformat` | Dateiendung nicht `.csv`, `.tsv`, `.txt` oder `.xlsx` | Datei umbenennen oder konvertieren |
| `FEHLER: --output nur bei einzelner Datei` | `--output` mit mehreren Dateien | `--output-dir` verwenden |
| `FEHLER: Keine verarbeitbaren Dateien` | ZIP enthaelt keine CSV/XLSX | ZIP-Inhalt pruefen |
| `HINWEIS: Repariere fehlende Drawing-Referenzen` | XLSX hat fehlerhafte Referenzen | Kein Handlungsbedarf, automatisch repariert |


## Hilfe erhalten

Falls Ihr Problem hier nicht gelistet ist:

1. Pruefen Sie die Konsolenausgabe des Tools auf Hinweise
2. Stellen Sie sicher, dass alle [Voraussetzungen](installation.md) erfuellt sind
3. Testen Sie mit einer kleinen Testdatei (wenige Zeilen)
