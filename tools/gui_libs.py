"""Eingebettete Bibliotheken der Browser-GUI pruefen und aktualisieren.

pseudonym_gui.html enthaelt SheetJS und JSZip als unveraenderte Kopie der Herstellerdateien.
Die Seite laedt deshalb nichts aus dem Netz. Dieses Werkzeug haelt die Kopien nachpruefbar:

    python tools/gui_libs.py check     Pruefsummen gegen die Dateien der Hersteller pruefen
                                       und nach neueren Versionen suchen
    python tools/gui_libs.py update    die neueste Version einbetten

Vor jeder Veroeffentlichung "check" ausfuehren. Rueckgabecode von check:
0 = alles aktuell und unveraendert, 1 = neuere Version oder Abweichung, 2 = Pruefung nicht moeglich.

Braucht nur die Python-Standardbibliothek.
"""
import argparse
import base64
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

HTML_PATH = Path(__file__).resolve().parent.parent / "pseudonym_gui.html"

# "latest" liefert JSON mit dem Feld "version", "file" die Datei, die eingebettet wird.
LIBRARIES = {
    "lib-xlsx": {
        "name": "SheetJS",
        "latest": "https://cdn.sheetjs.com/xlsx-latest/package/package.json",
        "file": "https://cdn.sheetjs.com/xlsx-{version}/package/dist/xlsx.full.min.js",
    },
    "lib-jszip": {
        "name": "JSZip",
        "latest": "https://registry.npmjs.org/jszip/latest",
        "file": "https://cdnjs.cloudflare.com/ajax/libs/jszip/{version}/jszip.min.js",
    },
}

_BLOCK_RE = re.compile(r'<script id="(lib-[a-z]+)"([^>]*)>(.*?)</script>', re.S)


def checksum(code: str) -> str:
    """SHA-512 (Base64) des Codes. Zeilenenden zaehlen als LF: So bleibt die Pruefsumme gleich,
    wenn ein Werkzeug die HTML-Datei auf Windows-Zeilenenden umstellt."""
    data = code.replace("\r\n", "\n").encode("utf-8")
    return base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def problems(code: str) -> list:
    """Gruende, aus denen sich Code nicht unveraendert in ein <script>-Element legen laesst."""
    found = []
    if re.search(r"</script", code, re.I):
        found.append("enthaelt </script (wuerde das Element vorzeitig beenden)")
    if re.search(r"<script", code, re.I):
        found.append("enthaelt <script (das Element wuerde danach nicht mehr enden)")
    if "\r" in code:
        found.append("enthaelt Wagenruecklauf-Zeichen (die Pruefsumme waere nicht eindeutig)")
    return found


def block(key: str, version: str, code: str) -> str:
    """Das <script>-Element fuer eine Bibliothek. Zwischen den Tags steht nur der Code."""
    name = LIBRARIES[key]["name"]
    return (f'<script id="{key}" data-name="{name}" data-version="{version}" '
            f'data-sha512="{checksum(code)}">{code}</script>')


def read_embedded(html: str) -> dict:
    """Eingebettete Bibliotheken: Schluessel -> version, sha512, code."""
    libs = {}
    for key, attrs, code in _BLOCK_RE.findall(html):
        version = re.search(r'data-version="([^"]*)"', attrs)
        sha = re.search(r'data-sha512="([^"]*)"', attrs)
        libs[key] = {"version": version.group(1) if version else "",
                     "sha512": sha.group(1) if sha else "", "code": code}
    return libs


def _version_tuple(version: str) -> tuple:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def is_newer(candidate: str, current: str) -> bool:
    return _version_tuple(candidate) > _version_tuple(current)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gui-libs-check"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def latest_version(key: str, fetch=fetch) -> str:
    return json.loads(fetch(LIBRARIES[key]["latest"]).decode("utf-8"))["version"]


def _read(html_path) -> str:
    # newline="": Zeilenenden nicht anfassen, die Datei mischt CRLF (Seite) und LF (Bibliotheken)
    with open(html_path, encoding="utf-8", newline="") as f:
        return f.read()


def check(html_path=HTML_PATH, fetch=fetch) -> int:
    """Prueft die eingebetteten Bibliotheken. Gibt den Rueckgabecode zurueck (siehe oben)."""
    libs = read_embedded(_read(html_path))
    result = 0
    for key, spec in LIBRARIES.items():
        if key not in libs:
            print(f"{spec['name']}: nicht eingebettet.")
            result = max(result, 1)
            continue
        lib = libs[key]
        label = f"{spec['name']} {lib['version']}"
        if checksum(lib["code"]) != lib["sha512"]:
            print(f"{label}: Der Code passt nicht zur Pruefsumme im Tag. Die Datei wurde von Hand geaendert.")
            result = max(result, 1)
            continue
        try:
            original = fetch(spec["file"].format(version=lib["version"])).decode("utf-8")
            newest = latest_version(key, fetch)
        except Exception as e:  # Netz, Server oder Antwortformat
            print(f"{label}: Konnte den Hersteller nicht pruefen ({type(e).__name__}: {e}).")
            result = max(result, 2)
            continue
        if checksum(original) != lib["sha512"]:
            print(f"{label}: Der eingebettete Code weicht von der Datei des Herstellers ab.")
            result = max(result, 1)
        elif is_newer(newest, lib["version"]):
            print(f"{label}: unveraendert, aber Version {newest} ist verfuegbar. "
                  "Einbetten mit: python tools/gui_libs.py update")
            result = max(result, 1)
        else:
            print(f"{label}: unveraendert und aktuell.")
    return result


def update(html_path=HTML_PATH, fetch=fetch) -> int:
    """Bettet von jeder Bibliothek die neueste Version ein. 0 = in Ordnung, 1 = nichts geaendert wegen Fehler."""
    html = _read(html_path)
    libs = read_embedded(html)
    changed = []
    for key, spec in LIBRARIES.items():
        try:
            newest = latest_version(key, fetch)
            if key in libs and not is_newer(newest, libs[key]["version"]):
                print(f"{spec['name']} {libs[key]['version']}: ist aktuell.")
                continue
            code = fetch(spec["file"].format(version=newest)).decode("utf-8")
        except Exception as e:
            print(f"{spec['name']}: Abbruch, die neue Version liess sich nicht laden ({type(e).__name__}: {e}).")
            return 1
        found = problems(code)
        if found or key not in libs:
            reason = "; ".join(found) or "kein Platz in der HTML-Datei vorgesehen"
            print(f"{spec['name']} {newest}: Abbruch, {reason}.")
            return 1
        old = block(key, libs[key]["version"], libs[key]["code"])
        if html.count(old) != 1:
            print(f"{spec['name']}: Abbruch, der vorhandene Block ist nicht im erwarteten Format.")
            return 1
        html = html.replace(old, block(key, newest, code))
        changed.append(f"{spec['name']} {libs[key]['version']} -> {newest}")
    if changed:
        with open(html_path, "w", encoding="utf-8", newline="") as f:
            f.write(html)
        print("Eingebettet: " + ", ".join(changed))
        print("Jetzt: Versionsangaben in der Doku anpassen (python -m pytest tests nennt die Stellen),")
        print("       Tests ausfuehren und die Seite im Browser pruefen.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Eingebettete Bibliotheken der Browser-GUI pruefen oder aktualisieren.")
    parser.add_argument("command", choices=["check", "update"])
    parser.add_argument("--html", default=str(HTML_PATH), help="Pfad der HTML-Datei")
    args = parser.parse_args(argv)
    return check(args.html) if args.command == "check" else update(args.html)


if __name__ == "__main__":
    sys.exit(main())
