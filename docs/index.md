# pseudonymizer — Wiki

Willkommen im Wiki des pseudonymizer-Projekts. Hier finden Sie alle Informationen zur Installation, Verwendung und Weiterentwicklung des Tools.

## Inhalt

### Fuer Anwender

- **[Installation](installation.md)** — Python-Umgebung einrichten und Browser-GUI starten
- **[CLI Referenz](usage-cli.md)** — Alle Befehle und Optionen der Python-Kommandozeile
- **[Browser-GUI Anleitung](usage-gui.md)** — Schritt-fuer-Schritt-Anleitung fuer die HTML-Oberflaeche
- **[Spalten-Referenz](column-reference.md)** — Welche Spalten erkannt und verschluesselt werden
- **[Troubleshooting](troubleshooting.md)** — Haeufige Probleme und deren Loesung

### Fuer Entwickler

- **[Kryptographie-Spezifikation](cryptography.md)** — Technische Details der Verschluesselung
- **[Entwicklung](development.md)** — Architektur, Beitragen, Testen

## Schnelleinstieg

| Ich moechte... | Siehe |
|---|---|
| Das Tool sofort nutzen (kein Install) | [Browser-GUI](usage-gui.md) |
| Das Tool per Kommandozeile nutzen | [Installation](installation.md) → [CLI Referenz](usage-cli.md) |
| Mehrere Dateien auf einmal verarbeiten | [CLI Batch-Modus](usage-cli.md#batch-modus) · [GUI Batch-Modus](usage-gui.md#batch-modus) |
| Wissen welche Spalten erkannt werden | [Spalten-Referenz](column-reference.md) |
| Ein Problem loesen | [Troubleshooting](troubleshooting.md) |
| Die Kryptographie verstehen | [Kryptographie](cryptography.md) |
| Zum Projekt beitragen | [Entwicklung](development.md) |

## Projektstruktur

```
pseudonymizer/
  pseudonym.py            Python CLI
  pseudonym_gui.html      Browser-GUI (Single-File)
  ANLEITUNG_pseudonym.md  Schritt-fuer-Schritt-Anleitung
  README.md               Projekt-Uebersicht
  CLAUDE.md               Entwickler-Kontext
  docs/                   Wiki (diese Seiten)
```
