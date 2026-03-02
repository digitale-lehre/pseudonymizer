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


## Fehlermeldungen

| Meldung | Bedeutung | Loesung |
|---|---|---|
| `FEHLER: Datei nicht gefunden` | Dateipfad existiert nicht | Pfad pruefen |
| `FEHLER: Konnte keine Spalten erkennen` | CSV-Datei ist leer oder fehlerhaft | Datei pruefen |
| `FEHLER: Keine Identitaetsspalten gefunden` | Spaltennamen nicht erkannt | Siehe oben |
| `FEHLER: Unbekanntes Dateiformat` | Dateiendung nicht `.csv`, `.tsv`, `.txt` oder `.xlsx` | Datei umbenennen oder konvertieren |
| `HINWEIS: Repariere fehlende Drawing-Referenzen` | XLSX hat fehlerhafte Referenzen | Kein Handlungsbedarf, automatisch repariert |


## Hilfe erhalten

Falls Ihr Problem hier nicht gelistet ist:

1. Pruefen Sie die Konsolenausgabe des Tools auf Hinweise
2. Stellen Sie sicher, dass alle [Voraussetzungen](installation.md) erfuellt sind
3. Testen Sie mit einer kleinen Testdatei (wenige Zeilen)
