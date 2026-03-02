# pseudonymizer

AES-256-CBC Pseudonymisierung fuer CSV- und XLSX-Dateien.

Ersetzt personenbezogene Spalten (Name, Matrikelnummer, E-Mail, Pruefer) durch verschluesselte Pseudonyme. Gleicher Secret = gleiche Pseudonyme, umkehrbar mit demselben Secret.

## Zwei Varianten

| | **Browser-GUI** | **Python CLI** |
|---|---|---|
| Datei | `pseudonym_gui.html` | `pseudonym.py` |
| Benoetigt | Nur einen Browser | Python 3.8+ |
| Start | Doppelklick auf HTML | `python pseudonym.py ...` |
| Formate | CSV, XLSX | CSV, XLSX |

Beide Varianten sind **kryptografisch kompatibel** — eine mit Python verschluesselte Datei kann in der GUI entschluesselt werden und umgekehrt.

## Browser-GUI (kein Install)

`pseudonym_gui.html` doppelklicken — fertig. Alles laeuft lokal im Browser, keine Daten verlassen den Rechner.

## Python CLI

```bash
pip install cryptography openpyxl

# Verschluesseln
python pseudonym.py encrypt datei.csv --secret "MeinSecret"
python pseudonym.py encrypt datei.xlsx --secret "MeinSecret"

# Entschluesseln
python pseudonym.py decrypt datei_pseudo.csv --secret "MeinSecret"
```

## Erkannte Spalten (case-insensitive)

- **Familienname**: FAMILIENNAME, Zuname, Nachname, FAMILY_NAME_OF_STUDENT
- **Vorname**: VORNAME, FirstName, FIRST_NAME_OF_STUDENT
- **Matrikelnummer**: MATRIKELNUMMER, Matnr, REGISTRATION_NUMBER
- **E-Mail**: EMAIL_ADDRESS, E-Mail, Email, Mail
- **Pruefer**: Examiner, Pruefer, Prüfer

Detaillierte Anleitung: [ANLEITUNG_pseudonym.md](ANLEITUNG_pseudonym.md)

## Sicherheit

- AES-256-CBC mit PBKDF2-Schluesselableitung (100.000 Iterationen)
- Deterministisch: gleicher Input + gleicher Secret = gleiches Pseudonym
- **Secret sicher aufbewahren** — ohne Secret keine Wiederherstellung moeglich
