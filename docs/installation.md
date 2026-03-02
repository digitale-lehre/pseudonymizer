# Installation

## Browser-GUI (kein Install noetig)

Die Browser-GUI (`pseudonym_gui.html`) benoetigt **keine Installation**. Einfach die HTML-Datei im Browser oeffnen:

1. `pseudonym_gui.html` doppelklicken
2. Die Datei oeffnet sich im Standardbrowser
3. Fertig — das Tool ist einsatzbereit

**Voraussetzungen:** Ein moderner Browser (Chrome, Firefox, Edge, Safari). Alle gaengigen Versionen der letzten Jahre werden unterstuetzt.

**Hinweis:** Die GUI laedt zwei kleine JavaScript-Bibliotheken (PapaParse, SheetJS) von einem CDN. Beim ersten Start ist daher eine Internetverbindung noetig. Danach werden die Bibliotheken aus dem Browser-Cache geladen.


## Python CLI

### Voraussetzungen

- **Python 3.8** oder neuer
- **pip** (wird mit Python mitgeliefert)

### Python installieren

**Windows:**
1. [python.org/downloads](https://www.python.org/downloads/) besuchen
2. Neueste Version herunterladen und installieren
3. **Wichtig:** Haken bei "Add Python to PATH" setzen

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

| Paket | Zweck |
|---|---|
| `cryptography` | AES-256-CBC Verschluesselung und PBKDF2 Schluesselableitung |
| `openpyxl` | XLSX-Dateien lesen und schreiben (Formatierung erhalten) |

### Installation pruefen

```bash
python pseudonym.py --version
```

Erwartete Ausgabe: `pseudonym.py 0.1.0`

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
