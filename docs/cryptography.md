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
```

Fehlgeschlagene Entschluesselung (falscher Secret, kein gueltiger Token) gibt den Originalwert unveraendert zurueck — kein Fehler, kein Datenverlust.


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
- `crypto.subtle.encrypt()` / `decrypt()` fuer AES-CBC
- Manuelles PKCS7-Padding (Web Crypto fuegt eigenes Padding hinzu)

Beide Implementierungen erzeugen **identische Ausgaben** fuer gleiche Eingaben.


## Kompatibilitaetstest

Nach jeder Aenderung am Krypto-Code muss geprueft werden, dass beide Implementierungen identische Ergebnisse liefern:

```python
from pseudonym import derive_key, encrypt_value
key = derive_key("testSecret123")
print(encrypt_value(key, "Mueller"))
# Erwartetes Ergebnis: a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc
```

Die Browser-GUI muss fuer denselben Input und Secret denselben Token erzeugen.


## Sicherheitshinweise

- **Nie** die PBKDF2-Iterationen reduzieren (Brute-Force-Schutz)
- **Nie** den Salt aendern (bricht Kompatibilitaet mit bestehenden Dateien)
- **Nie** den Modus wechseln (z.B. ECB statt CBC)
- **Nie** die IV-Ableitung aendern (bricht Kompatibilitaet)
- Aenderungen an der Kryptographie erfordern **immer** Updates in **beiden** Implementierungen und einen Migrationspfad fuer bestehende Dateien
