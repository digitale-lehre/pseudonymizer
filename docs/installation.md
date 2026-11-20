# Installation

## Browser-GUI (kein Install noetig)

Die Browser-GUI (`pseudonym_gui.html`) benoetigt **keine Installation**. Einfach die HTML-Datei im Browser oeffnen:

1. `pseudonym_gui.html` doppelklicken
2. Die Datei oeffnet sich im Standardbrowser
3. Fertig — das Tool ist einsatzbereit

**Voraussetzungen:** Ein moderner Browser (Chrome, Firefox, Edge, Safari). Alle gaengigen Versionen der letzten Jahre werden unterstuetzt.

**Hinweis:** Die GUI braucht keine Internetverbindung. Die beiden JavaScript-Bibliotheken SheetJS 0.20.3 und JSZip 3.10.2 sind in die Datei eingebaut. Ihre Daten bleiben auf dem Rechner: Die Seite baut keine Verbindung ins Netz auf.


## Python CLI

### Voraussetzungen

- **Python 3.8** oder neuer
- **pip** (wird mit Python mitgeliefert)

### Python installieren

**Windows:**
1. [python.org/downloads](https://www.python.org/downloads/) besuchen
2. Neueste Version herunterladen und installieren
3. **Wichtig:** Haken bei "Add Python to PATH" setzen

Sind unter Windows mehrere Python-Versionen installiert, zeigt `py -0p` alle an. `python` startet eine davon; die Pakete muessen in genau dieser Version installiert sein. Mit `py -3.10 pseudonym.py ...` laesst sich eine bestimmte Version waehlen.

**macOS:**
```bash
brew install python
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install python3 python3-pip
```

### Abhaengigkeiten installieren

```bash
pip install cryptography openpyxl
```

Oder mit den Versionen, mit denen das Tool getestet ist:

```bash
pip install -r requirements.txt
```

| Paket | Zweck |
|---|---|
| `cryptography` | AES-256-CBC Verschluesselung und PBKDF2 Schluesselableitung |
| `openpyxl` | XLSX/XLSM-Dateien lesen und schreiben (Formatierung erhalten, bei XLSM auch Makros) |

### Installation pruefen

```bash
python pseudonym.py --version
```

Erwartete Ausgabe: `pseudonym.py 0.7.1` (aktuelle Version: v0.7.1)

Fehlt ein Paket, steht darunter eine Zeile `ACHTUNG: Python-Paket ... fehlt` mit dem passenden Installationsbefehl. Das passiert auch, wenn mehrere Python-Versionen installiert sind und die Pakete in einer anderen liegen.

### Optionale virtuelle Umgebung

Falls Sie die Pakete nicht global installieren moechten:

```bash
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows
pip install cryptography openpyxl
```


## Naechste Schritte

- [CLI Referenz](usage-cli.md) — Befehle und Optionen
- [Browser-GUI Anleitung](usage-gui.md) — GUI-Funktionen im Detail
