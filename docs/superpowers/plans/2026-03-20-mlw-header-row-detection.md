# MLW Export Support: Header Row Auto-Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support MLW (Medizinische Lehre Wien) export files that have metadata rows before the actual column headers, while maintaining full backward compatibility with all existing formats.

**Architecture:** Add a `find_header_row()` function that scans rows to find the first row containing known identity column aliases. Everything before that row is treated as metadata and preserved unchanged in output. This approach is generic (works for any number of metadata rows) and backward-compatible (files where row 1 is the header are found immediately). A new column alias "Familienname oder Nachname" is also added. All changes must be mirrored in both Python CLI and HTML GUI.

**Tech Stack:** Python 3.8+ (csv, openpyxl), Vanilla JS (PapaParse, SheetJS, Web Crypto API)

---

## Context: MLW Export Format

The MLW export (screenshot `Screenshot_MLW.png`) has this structure:
- **Row 1**: Sheet title, e.g. "Teilnehmer Erreichbar"
- **Row 2**: Module metadata: module code, module name, date, capacity
- **Row 3**: Empty
- **Row 4**: Actual column headers including "Familienname oder Nachname", "Vorname", etc.
- **Row 5+**: Data rows

Currently both implementations assume row 1 (XLSX) / first line (CSV) is the header. This breaks on MLW exports because rows 1-3 are metadata, not column headers.

## File Structure

| File | Change |
|------|--------|
| `pseudonym.py` | Add `find_header_row()`, update `process_xlsx()` and `process_csv()`, add new alias |
| `pseudonym_gui.html` | Add `findHeaderRow()`, update `parseFile()` and `processFile()`, add new alias, update info popup |
| `docs/column-reference.md` | Add new alias |
| `ANLEITUNG_pseudonym.md` | Add new alias |
| `README.md` | Add new alias |
| `CLAUDE.md` | Add new alias to table |

---

### Task 1: Add `find_header_row()` and new alias to Python

**Files:**
- Modify: `pseudonym.py:39-58` (COLUMN_ALIASES + new function)

- [ ] **Step 1: Add "Familienname oder Nachname" alias to COLUMN_ALIASES**

In `pseudonym.py`, add the new alias to the `familienname` list:

```python
COLUMN_ALIASES = {
    "familienname": ["FAMILIENNAME", "Familienname", "familienname", "Zuname", "zuname",
                     "ZUNAME", "Nachname", "nachname", "NACHNAME", "Last Name", "LastName",
                     "FAMILY_NAME_OF_STUDENT", "Family_Name_of_Student",
                     "Familienname oder Nachname"],
    # ... rest unchanged
}
```

- [ ] **Step 2: Add `find_header_row()` function**

Add after `find_name_col()` (after line 131):

```python
def find_header_row(rows, max_scan=20):
    """Findet die Header-Zeile in einer Liste von Zeilen (als Listen).
    Scannt bis zu max_scan Zeilen nach bekannten Identitaetsspalten.
    Gibt den Index zurueck (0-basiert). Fallback: 0 (erste Zeile)."""
    for i, row in enumerate(rows[:max_scan]):
        # row is a list of cell values (strings)
        headers = [str(c).strip() if c is not None else "" for c in row]
        if find_identity_cols(headers):
            return i
    return 0
```

- [ ] **Step 3: Verify the function works in isolation**

Quick manual test in Python REPL:

```bash
python3 -c "
from pseudonym import find_header_row, find_identity_cols
# MLW-style rows
rows = [
    ['Teilnehmer Erreichbar', '', '', ''],
    ['MOD.01204M0', 'Artificial Intelligence (AI)', '18.04.2025', '70 :20'],
    ['', '', '', ''],
    ['', 'Familienname oder Nachname', 'Vorname', 'Titel', 'Institution'],
    ['', 'Mueller', 'Max', 'Dr.', 'Uni Wien'],
]
idx = find_header_row(rows)
print(f'Header row index: {idx}')  # Expected: 3
assert idx == 3, f'Expected 3, got {idx}'

# Standard format (header in row 0)
rows2 = [['FAMILIENNAME', 'VORNAME', 'MATRIKELNUMMER'], ['Mueller', 'Max', '12345']]
idx2 = find_header_row(rows2)
print(f'Standard header row index: {idx2}')  # Expected: 0
assert idx2 == 0, f'Expected 0, got {idx2}'

print('OK')
"
```

Expected: Both assertions pass, prints "OK".

- [ ] **Step 4: Commit**

```bash
git add pseudonym.py
git commit -m "feat: add find_header_row() and 'Familienname oder Nachname' alias"
```

---

### Task 2: Update `process_xlsx()` to use header row detection

**Files:**
- Modify: `pseudonym.py:300-415` (process_xlsx function)

- [ ] **Step 1: Refactor header detection in `process_xlsx()`**

Replace the header detection logic in the per-sheet loop. Currently (lines 325-330):

```python
        # Header aus Zeile 1 lesen
        headers = []
        for col_idx in range(1, (ws.max_column or 0) + 1):
            val = ws.cell(row=1, column=col_idx).value
            headers.append(str(val).strip() if val is not None else "")
```

Replace with:

```python
        # Alle Zeilen als Listen lesen, dann Header-Zeile finden
        all_rows = []
        for row_idx in range(1, (ws.max_row or 0) + 1):
            row_vals = []
            for col_idx in range(1, (ws.max_column or 0) + 1):
                val = ws.cell(row=row_idx, column=col_idx).value
                row_vals.append(str(val).strip() if val is not None else "")
            all_rows.append(row_vals)

        header_offset = find_header_row(all_rows)
        headers = all_rows[header_offset] if all_rows else []
        # header_row in openpyxl is 1-based: header_offset + 1
        header_row_num = header_offset + 1
```

- [ ] **Step 2: Update row iteration to start after detected header**

Replace the data iteration start. Currently (line 337-338):

```python
        if ws.max_row < 2:
            sheets_skipped.append(f"{ws.title} (nur Header, keine Daten)")
            continue
```

Replace with:

```python
        data_start_row = header_row_num + 1
        if ws.max_row < data_start_row:
            sheets_skipped.append(f"{ws.title} (nur Header, keine Daten)")
            continue
```

And update the main loop (line 369):

```python
        for row_idx in range(data_start_row, ws.max_row + 1):
```

Instead of:

```python
        for row_idx in range(2, ws.max_row + 1):
```

- [ ] **Step 3: Update NAME composite check to use correct row**

The composite check currently reads from row 2 (line 357-360). Update to use `data_start_row`:

```python
        if name_col_idx and fam_idx and vor_idx and ws.max_row >= data_start_row:
            name_val = str(ws.cell(row=data_start_row, column=name_col_idx).value or "").strip()
            fam_val = str(ws.cell(row=data_start_row, column=fam_idx).value or "").strip()
            vor_val = str(ws.cell(row=data_start_row, column=vor_idx).value or "").strip()
```

- [ ] **Step 4: Add info about detected header row to log output**

After the existing log output, add information when header is not in row 1:

```python
        if header_row_num > 1:
            print(f"    (Header in Zeile {header_row_num}, {header_row_num - 1} Metadaten-Zeile(n) uebersprungen)")
```

- [ ] **Step 5: Commit**

```bash
git add pseudonym.py
git commit -m "feat: XLSX header row auto-detection for MLW exports"
```

---

### Task 3: Update `process_csv()` to use header row detection with metadata preservation

**Files:**
- Modify: `pseudonym.py:148-238` (process_csv function)

This is the most complex change because CSV metadata rows must be preserved in the output **as raw text** (not re-serialized through `csv.writer`) to maintain byte-identical roundtrips. Quoting detection must also be based on the header row, not the first line of the file.

- [ ] **Step 1: Refactor `process_csv()` to detect header row and preserve raw metadata**

Replace the current DictReader approach. The new approach:
1. Split raw text into lines to preserve raw metadata text
2. Parse all rows as list-of-lists to find the header
3. Preserve metadata lines as raw text (not re-serialized)
4. Process data rows
5. Output: raw metadata text + header + processed data

Replace the section from `first_line = ...` through `rows = list(reader)` (lines 161-166) with:

```python
    # Alle Zeilen als Listen parsen, um Header-Zeile zu finden
    reader_raw = csv.reader(io.StringIO(text), delimiter=sep)
    all_rows = list(reader_raw)

    if not all_rows:
        print("FEHLER: Datei ist leer.", file=sys.stderr)
        sys.exit(1)

    # Header-Zeile finden (kann nach Metadaten-Zeilen liegen, z.B. MLW-Export)
    header_idx = find_header_row(all_rows)
    fieldnames = all_rows[header_idx]
    data_rows_raw = all_rows[header_idx + 1:]

    # Rohtext-Zeilen fuer Metadaten-Bewahrung und Quoting-Erkennung
    # (Einfache Zeilen ohne Newlines in Quotes — MLW-Metadaten sind sicher)
    raw_lines = text.split("\r\n") if has_crlf else text.split("\n")

    # Rohe Metadaten-Zeilen als Text bewahren (fuer byte-identische Ausgabe)
    meta_raw_text = ""
    if header_idx > 0:
        meta_raw_text = line_terminator.join(raw_lines[:header_idx]) + line_terminator

    # Quoting anhand der Header-Zeile erkennen (nicht erste Datei-Zeile!)
    header_line_raw = raw_lines[header_idx].strip() if header_idx < len(raw_lines) else ""
    quoting = csv.QUOTE_ALL if header_line_raw.startswith('"') else csv.QUOTE_MINIMAL

    # Konvertiere zu Dicts (wie DictReader)
    rows = []
    for raw_row in data_rows_raw:
        d = {}
        for i, h in enumerate(fieldnames):
            d[h] = raw_row[i] if i < len(raw_row) else ""
        rows.append(d)
```

- [ ] **Step 2: Update the check for empty fieldnames**

Replace (lines 168-171):

```python
    if not fieldnames:
        print("FEHLER: Konnte keine Spalten erkennen.", file=sys.stderr)
        sys.exit(1)
```

This stays the same but now `fieldnames` comes from the detected header row.

- [ ] **Step 3: Update the output to include raw metadata text**

Replace the output section (lines 198-224). Write raw metadata text first (byte-exact), then header + data via DictWriter:

```python
    str_out = io.StringIO()

    # Metadaten-Zeilen als Rohtext ausgeben (byte-identisch, nicht re-serialisiert)
    if meta_raw_text:
        str_out.write(meta_raw_text)

    # Header + Daten mit DictWriter
    dict_writer = csv.DictWriter(
        str_out, fieldnames=fieldnames, delimiter=sep,
        quoting=quoting, lineterminator=line_terminator
    )
    dict_writer.writeheader()
    for row in rows:
        new_row = dict(row)
        for canon_key, actual_col in id_cols.items():
            val = (row.get(actual_col) or "").strip()
            if val:
                new_row[actual_col] = transform(key, val)
        if name_col and name_is_composite:
            fam = new_row.get(fam_col, "")
            vor = new_row.get(vor_col, "")
            if name_order == "vor_fam":
                new_row[name_col] = f"{vor} {fam}".strip()
            else:
                new_row[name_col] = f"{fam} {vor}".strip()
        dict_writer.writerow(new_row)
```

- [ ] **Step 4: Add metadata info to log output**

Add after the existing log output, before the encoding line:

```python
    if header_idx > 0:
        print(f"  Metadaten:  {header_idx} Zeile(n) vor Header (unveraendert)")
```

- [ ] **Step 5: Verify backward compatibility with standard CSV**

Run encrypt/decrypt with a standard CSV (header in row 1) and verify byte-identical roundtrip:

```bash
# Create test file
echo '"FAMILIENNAME","VORNAME","MATRIKELNUMMER"
"Mueller","Max","12345"
"Schmidt","Anna","67890"' > /tmp/test_standard.csv

python pseudonym.py encrypt /tmp/test_standard.csv --secret "test123"
python pseudonym.py decrypt /tmp/test_standard_pseudo.csv --secret "test123"
diff /tmp/test_standard.csv /tmp/test_standard_pseudo_restored.csv
echo "Roundtrip OK: $?"
```

Expected: `diff` shows no differences, exit code 0.

- [ ] **Step 6: Test with MLW-style CSV (metadata rows before header)**

```bash
# Create MLW-style test file
cat > /tmp/test_mlw.csv << 'CSVEOF'
"Teilnehmer Erreichbar","","",""
"MOD.01204M0","Artificial Intelligence (AI)","18.04.2025","70 :20"
"","","",""
"","Familienname oder Nachname","Vorname","Institution","Tertiginr"
"","Mueller","Max","Uni Wien","1"
"","Schmidt","Anna","AKH","2"
CSVEOF

python pseudonym.py encrypt /tmp/test_mlw.csv --secret "test123"
cat /tmp/test_mlw_pseudo.csv
# Verify: metadata rows preserved, names encrypted, Institution unchanged

python pseudonym.py decrypt /tmp/test_mlw_pseudo.csv --secret "test123"
diff /tmp/test_mlw.csv /tmp/test_mlw_pseudo_restored.csv
echo "MLW roundtrip OK: $?"
```

Expected: Metadata rows preserved, names encrypted/decrypted, roundtrip byte-identical.

- [ ] **Step 7: Commit**

```bash
git add pseudonym.py
git commit -m "feat: CSV header row auto-detection with metadata preservation"
```

---

### Task 4: Update HTML GUI — add `findHeaderRow()`, new alias, header row detection

**Files:**
- Modify: `pseudonym_gui.html:271-308` (COLUMN_ALIASES, findIdentityCols, findNameCol)
- Modify: `pseudonym_gui.html:418-447` (parseFile)
- Modify: `pseudonym_gui.html:536-606` (processFile — processing loop)
- Modify: `pseudonym_gui.html:610-645` (processFile — output building)
- Modify: `pseudonym_gui.html:196-207` (info popup table)

- [ ] **Step 1: Add new alias to JS COLUMN_ALIASES**

In `pseudonym_gui.html`, update the `familienname` aliases array (line 272):

```javascript
  familienname: ["FAMILIENNAME","Familienname","familienname","Zuname","zuname","ZUNAME",
    "Nachname","nachname","NACHNAME","Last Name","LastName",
    "FAMILY_NAME_OF_STUDENT","Family_Name_of_Student",
    "Familienname oder Nachname"],
```

- [ ] **Step 2: Add `findHeaderRow()` function**

Add after `findNameCol()` (after line 308):

```javascript
function findHeaderRow(rows, maxScan = 20) {
  for (let i = 0; i < Math.min(rows.length, maxScan); i++) {
    const headers = rows[i].map(c => c == null ? '' : String(c).trim());
    if (Object.keys(findIdentityCols(headers)).length > 0) return i;
  }
  return 0;
}
```

- [ ] **Step 3: Update XLSX parsing in `parseFile()`**

Replace the XLSX parsing block (lines 420-426):

```javascript
    const wb = XLSX.read(fileData.raw, { type: 'array' });
    parsedData = { sheets: wb.SheetNames.map(name => {
      const ws = wb.Sheets[name];
      const json = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });
      if (json.length === 0) return { name, headers: [], rows: [], metaRows: [] };
      const allRows = json.map(r => r.map(c => c == null ? '' : String(c)));
      const headerIdx = findHeaderRow(allRows);
      return {
        name,
        headers: allRows[headerIdx],
        metaRows: allRows.slice(0, headerIdx),
        rows: allRows.slice(headerIdx + 1)
      };
    })};
```

- [ ] **Step 4: Update CSV parsing in `parseFile()`**

Replace the CSV parsedData assignment (line 442):

```javascript
    const allRows = result.data.map(r => r.map(c => c == null ? '' : String(c)));
    if (allRows.length === 0) {
      parsedData = { sheets: [{ name: 'CSV', headers: [], rows: [], metaRows: [] }] };
      return;
    }
    const headerIdx = findHeaderRow(allRows);
    parsedData = { sheets: [{
      name: fileData.name,
      headers: allRows[headerIdx],
      metaRows: allRows.slice(0, headerIdx),
      rows: allRows.slice(headerIdx + 1)
    }] };
```

- [ ] **Step 5: Update XLSX output building in `processFile()`**

Replace the XLSX output block (lines 613-618) to include metaRows:

```javascript
    const wb = XLSX.utils.book_new();
    for (const rs of resultSheets) {
      const data = [...rs.metaRows, rs.headers, ...rs.rows];
      const ws = XLSX.utils.aoa_to_sheet(data);
      XLSX.utils.book_append_sheet(wb, ws, rs.name);
    }
```

- [ ] **Step 6: Update CSV output building in `processFile()`**

Replace the CSV quoting detection and output block (lines 626-631). The quoting detection must use the header row, not the first line of the file (which may be a metadata row):

```javascript
    const rs = resultSheets[0];
    // Detect quoting from header row, not first line (metadata rows may differ)
    const rawBytes = new Uint8Array(fileData.raw);
    const origDecoded = new TextDecoder(fileData.encoding).decode(rawBytes.slice(fileData.bomLength));
    const origLines = origDecoded.includes('\r\n') ? origDecoded.split('\r\n') : origDecoded.split('\n');
    const headerLineIdx = rs.metaRows ? rs.metaRows.length : 0;
    const headerLineRaw = (origLines[headerLineIdx] || '').trim();
    const quoteAll = headerLineRaw.startsWith('"');

    // Build output: metaRows are written as raw text to preserve exact formatting
    const useCrlf = origDecoded.includes('\r\n');
    const lineEnd = useCrlf ? '\r\n' : '\n';
    let finalCsv = '';

    // Metadata rows: preserve raw text exactly
    if (headerLineIdx > 0) {
      finalCsv = origLines.slice(0, headerLineIdx).join(lineEnd) + lineEnd;
    }

    // Header + data rows via PapaParse
    const dataForPapa = [rs.headers, ...rs.rows];
    let csvStr = Papa.unparse(dataForPapa, { delimiter: sep, quotes: quoteAll });
    if (useCrlf && !csvStr.includes('\r\n')) csvStr = csvStr.replace(/\n/g, '\r\n');
    if (!useCrlf) csvStr = csvStr.replace(/\r\n/g, '\n');
    finalCsv += csvStr;
```

Then update the blob creation to use `finalCsv` directly (remove the old `finalCsv` variable and its line-ending logic, since it's now handled above).

- [ ] **Step 7: Ensure `metaRows` is preserved in resultSheets**

In the processing loop (lines 543-544), update the skip case to include metaRows:

```javascript
      resultSheets.push({ name: sheet.name, headers: [...sheet.headers], metaRows: sheet.metaRows || [], rows: sheet.rows.map(r => [...r]) });
```

And in the processed case (line 605):

```javascript
    resultSheets.push({ name: sheet.name, headers: [...sheet.headers], metaRows: sheet.metaRows || [], rows: newRows });
```

- [ ] **Step 8: Show metadata row count in preview info**

Update `renderPreview()` to show metadata info. In the `previewInfo` text (around line 454), include metadata row count:

```javascript
  const metaCount = parsedData.sheets.reduce((s, sh) => s + (sh.metaRows ? sh.metaRows.length : 0), 0);
  const metaInfo = metaCount > 0 ? `, ${metaCount} Metadaten-Zeile(n)` : '';
  document.getElementById('previewInfo').textContent = `— ${parsedData.sheets.length} Sheet(s), ${totalRows} Zeilen${metaInfo}`;
```

- [ ] **Step 9: Update info popup table**

In the info popup (line 199), add the new alias:

```html
<tr><td>Familienname</td><td>FAMILIENNAME, Zuname, Nachname, FAMILY_NAME_OF_STUDENT, Familienname oder Nachname</td></tr>
```

- [ ] **Step 10: Commit**

```bash
git add pseudonym_gui.html
git commit -m "feat: HTML GUI header row auto-detection and new alias"
```

---

### Task 5: Update documentation

**Files:**
- Modify: `docs/column-reference.md`
- Modify: `ANLEITUNG_pseudonym.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `docs/column-reference.md`**

Add new alias to the Familienname table (after the "Family_Name_of_Student" row):

```markdown
| `Familienname oder Nachname` | MLW-Export (Medizinische Lehre Wien) |
```

- [ ] **Step 2: Update `ANLEITUNG_pseudonym.md`**

Update the column table (line 90) to include new alias:

```markdown
| Familienname | `FAMILIENNAME`, `Familienname`, `Zuname`, `Nachname`, `FAMILY_NAME_OF_STUDENT`, `Last Name`, `LastName`, `Familienname oder Nachname` |
```

Add a note about MLW exports after the "Bekannte XLSX-Probleme" section:

```markdown
## MLW-Exporte (Medizinische Lehre Wien)

MLW-Exporte enthalten Metadaten-Zeilen vor der eigentlichen Spalten-Kopfzeile (z.B. Modulcode, Modulname, Datum). Das Tool erkennt die Header-Zeile automatisch und behaelt die Metadaten-Zeilen unveraendert bei.
```

- [ ] **Step 3: Update `README.md`**

Update the column table (line 49) to include new alias:

```markdown
| **Familienname** | FAMILIENNAME, Zuname, Nachname, FAMILY_NAME_OF_STUDENT, Last Name, LastName, Familienname oder Nachname |
```

- [ ] **Step 4: Update `CLAUDE.md`**

Update the Column Recognition table to include the new alias:

```markdown
| familienname | FAMILIENNAME, Familienname, Zuname, Nachname, FAMILY_NAME_OF_STUDENT, Last Name, LastName, Familienname oder Nachname |
```

Add a note about header row detection to the Architecture section or Common Tasks:

```markdown
### Header Row Auto-Detection
Both implementations scan for the header row (up to 20 rows). Files with metadata rows before the header (e.g., MLW exports) are supported. Metadata rows are preserved unchanged in output.
```

- [ ] **Step 5: Commit**

```bash
git add docs/column-reference.md ANLEITUNG_pseudonym.md README.md CLAUDE.md
git commit -m "docs: add MLW alias and header row detection documentation"
```

---

### Task 6: Cross-implementation compatibility testing

- [ ] **Step 1: Test Python with standard XLSX (header in row 1)**

```bash
# Use an existing XLSX that has headers in row 1
# Verify no behavioral change
python pseudonym.py encrypt test_standard.xlsx --secret "test123"
python pseudonym.py decrypt test_standard_pseudo.xlsx --secret "test123"
```

Expected: Works exactly as before.

- [ ] **Step 2: Test Python with MLW-style XLSX (metadata rows)**

Create or use an XLSX with metadata rows before the header. Verify:
- Metadata rows preserved
- Identity columns encrypted
- Non-identity columns unchanged
- Decrypt roundtrip restores original data

- [ ] **Step 3: Test HTML GUI with standard files**

Open `pseudonym_gui.html` in browser:
1. Load a standard CSV — verify preview shows correct headers, encryption works
2. Load a standard XLSX — verify same

- [ ] **Step 4: Test HTML GUI with MLW-style files**

1. Load an MLW CSV — verify preview shows data (not metadata as headers)
2. Load an MLW XLSX — verify same
3. Encrypt and download — verify metadata preserved in output
4. Re-load encrypted file and decrypt — verify roundtrip

- [ ] **Step 5: Cross-implementation test**

Encrypt a file with Python, decrypt with HTML GUI (and vice versa). Verify identical results.

```bash
# Python encrypt
python pseudonym.py encrypt /tmp/test_mlw.csv --secret "CrossTest"

# Then open pseudonym_gui.html, load the _pseudo.csv, enter "CrossTest", decrypt
# Verify output matches original
```

- [ ] **Step 6: Commit version bump**

```bash
# Update version in pseudonym.py and pseudonym_gui.html
# v0.2.0 -> v0.3.0
git add pseudonym.py pseudonym_gui.html
git commit -m "chore: bump version to v0.3.0 for MLW support"
```
