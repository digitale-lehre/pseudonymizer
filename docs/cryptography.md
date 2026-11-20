# Kryptographie-Spezifikation

## Ueberblick

Der pseudonymizer verwendet symmetrische Verschluesselung mit deterministischer IV-Ableitung. Das bedeutet: gleicher Klartext + gleicher Secret = gleiches Pseudonym. Dies ist eine bewusste Designentscheidung, um konsistente Pseudonyme ueber mehrere Dateien hinweg zu ermoeglichen.


## Schluesselableitung

| Parameter | Wert |
|---|---|
| Algorithmus | PBKDF2-HMAC-SHA256 |
| Iterationen | 100.000 |
| Salt | `MedUniWien-Pseudo-Salt` (UTF-8 kodiert) |
| Schluessellaenge | 256 Bit (32 Bytes) |

```
Key = PBKDF2(
    hash      = SHA-256,
    password  = Secret (UTF-8),
    salt      = "MedUniWien-Pseudo-Salt" (UTF-8),
    iterations = 100000,
    dkLen     = 32
)
```


## Deterministischer Initialisierungsvektor (IV)

Der IV wird deterministisch aus dem Schluessel und dem Klartext abgeleitet:

```
IV = HMAC-SHA256(Key, Plaintext)[:16]
```

Dies stellt sicher, dass gleiche Eingaben bei gleichem Secret immer dasselbe Pseudonym erzeugen.

**Trade-off:** Identische Klartext-Werte fuehren zu identischem Chiffretext. Fuer den Anwendungsfall (Pseudonymisierung von Studentendaten) ist dies akzeptabel und sogar erwuenscht, da es die Zuordnung ueber mehrere Dateien hinweg ermoeglicht.


## Verschluesselung

| Parameter | Wert |
|---|---|
| Algorithmus | AES-256-CBC |
| Padding | PKCS7 (128 Bit Blockgroesse) |
| IV-Laenge | 16 Bytes |

```
Padded    = PKCS7_Pad(Plaintext, 128)
Ciphertext = AES-CBC-Encrypt(Key, IV, Padded)
```


## Ausgabeformat

```
Output = Base64url_nopad(IV || Ciphertext)
```

- **IV und Ciphertext** werden konkateniert (IV zuerst, dann Ciphertext)
- **Base64url-Kodierung** (RFC 4648, URL-sicher: `+/` werden zu `-_`)
- **Kein Padding:** Trailing `=`-Zeichen werden entfernt

Beispiel fuer "Mueller" mit Secret "testSecret123":
```
a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc
```


## Entschluesselung

```
Raw        = Base64url_decode(Token + Padding)
IV         = Raw[:16]
Ciphertext = Raw[16:]
Padded     = AES-CBC-Decrypt(Key, IV, Ciphertext)
Plaintext  = PKCS7_Unpad(Padded)
Gueltig    = HMAC-SHA256(Key, Plaintext)[:16] == IV
```

**Pruefung:** Der IV im Token ist ein Pruefwert. Nach dem Entschluesseln berechnen beide Implementierungen den IV aus dem Klartext neu und vergleichen ihn mit dem IV im Token. Stimmt er nicht, gilt der Wert als "kein Pseudonym fuer dieses Secret". Die Pruefung ist exakt und braucht keine Aenderung am Format: Sie gilt auch fuer alle Tokens aelterer Versionen.

Ohne diese Pruefung liefert AES-CBC mit einem falschen Schluessel in etwa 1 von 256 Faellen ein formal gueltiges Padding und damit Zeichensalat statt eines Fehlers.

Ein Wert, der kein gueltiges Pseudonym ist (Klartext, beschaedigter Token, falsches Secret), bleibt unveraendert. Die Werkzeuge zaehlen diese Zellen und melden sie. Laesst sich in einer Datei kein einziger Wert entschluesseln, entsteht keine Ausgabedatei (falsches Secret).


## Was verschluesselt wird

- **Leerraum am Zellrand** gehoert nicht zum Klartext. Aus ` Max ` wird ` <Token von "Max"> `. So bekommt derselbe Name immer dasselbe Pseudonym, und der Roundtrip bleibt byte-identisch.
- **Leere Zellen** bleiben leer.
- **Excel-Zellen** werden in ihrer Textform verschluesselt: die Zahl `1234567` als `1234567`, ein ganzzahliger Gleitkommawert ohne `.0`, ein Datum als `2000-01-31 00:00:00`, eine reine Uhrzeit als `12:30:00`. Beide Implementierungen bilden diese Textform gleich.
- **Name-Spalte:** Besteht der Wert einer Zeile aus Familienname und Vorname, ist das Ergebnis `<Token> <Token>` in der urspruenglichen Reihenfolge. Sonst ist der ganze Wert ein Token.


## Implementierungen

### Python (`pseudonym.py`)

Verwendet die `cryptography`-Bibliothek:
- `hashlib.pbkdf2_hmac()` fuer Schluesselableitung
- `hmac.new()` fuer IV-Ableitung
- `Cipher(AES, CBC)` fuer Verschluesselung
- `sym_padding.PKCS7()` fuer Padding

### Browser (`pseudonym_gui.html`)

Verwendet die Web Crypto API:
- `crypto.subtle.importKey()` + `crypto.subtle.deriveBits()` fuer PBKDF2
- `crypto.subtle.sign()` fuer HMAC
- `crypto.subtle.encrypt()` / `decrypt()` fuer AES-CBC. Web Crypto fuegt das PKCS7-Padding selbst hinzu und entfernt es
- Die Schluessel werden einmal je Lauf importiert (`createCipher()`), nicht je Zelle

Beide Implementierungen erzeugen **identische Ausgaben** fuer gleiche Eingaben.


## Kompatibilitaetstest

Nach jeder Aenderung am Krypto-Code muss geprueft werden, dass beide Implementierungen identische Ergebnisse liefern:

```python
from pseudonym import derive_key, encrypt_value
key = derive_key("testSecret123")
print(encrypt_value(key, "Mueller"))
# Erwartetes Ergebnis: a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc
```

Die Browser-GUI muss fuer denselben Input und Secret denselben Token erzeugen. Beides pruefen die automatischen Tests: `tests/test_core.py` (Python) und `tests/test_gui_parity.py` (JavaScript-Teil der GUI in Node, siehe [Entwicklung](development.md#testen)). In der Browser-Konsole geht es von Hand:

```js
createCipher("testSecret123").then(c => c.encrypt("Mueller")).then(console.log)
```


## Sicherheitshinweise

- **Nie** die PBKDF2-Iterationen reduzieren (Brute-Force-Schutz)
- **Nie** den Salt aendern (bricht Kompatibilitaet mit bestehenden Dateien)
- **Nie** den Modus wechseln (z.B. ECB statt CBC)
- **Nie** die IV-Ableitung aendern (bricht Kompatibilitaet)
- Aenderungen an der Kryptographie erfordern **immer** Updates in **beiden** Implementierungen und einen Migrationspfad fuer bestehende Dateien
