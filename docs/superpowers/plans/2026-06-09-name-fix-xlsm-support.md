# "Name"-Spalten-Fix + .xlsm-Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix that standalone/non-composite `Name` columns are never pseudonymized, and add `.xlsm` (macro-enabled Excel) as a supported input/output format in both the Python CLI and the browser GUI.

**Architecture:** The `Name` fix adds a fallback in all three column-processing paths: when a `Name` column exists but is *not* a composite of `Vorname`+`Familienname`, encrypt the whole cell value (deterministic crypto ⇒ same token as a `Nachname` column, fully reversible). `.xlsm` reuses the existing XLSX path; the CLI adds `keep_vba=True` (openpyxl 3.1.5 copies the whole archive into `wb.vba_archive` and re-merges `xl/vba*` parts on save), the GUI accepts `.xlsm` and writes `bookType:'xlsm'` (macros/formatting dropped, as already happens for `.xlsx`).

**Tech Stack:** Python 3.8+ (`cryptography`, `openpyxl`), pytest; vanilla JS + SheetJS/PapaParse/JSZip in a single HTML file.

**Spec:** `docs/superpowers/specs/2026-06-09-name-fix-xlsm-support-design.md`

**Crypto invariant (unchanged):** `encrypt_value(derive_key("testSecret123"), "Mueller")` must equal `a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc` in both implementations.

---

## File Structure

- `pseudonym.py` — CLI. Modify `process_csv` (Name fallback), `process_xlsx` (Name fallback + `keep_vba`), `_fix_xlsx_drawings` (temp suffix), `process_file` (dispatch), `collect_input_files` (supported exts), help/docstring texts, `__version__`.
- `pseudonym_gui.html` — GUI. Modify Name logic (~828–852), info popup (259), `accept` attr (222), file-type detection (543, 555), XLSX writer (868–873), version string (207).
- `tests/test_batch.py` — add Name-fix + `.xlsm` tests (CLI side; GUI has no harness).
- `.gitignore` — add `*.xlsm`.
- `README.md`, `ANLEITUNG_pseudonym.md`, `docs/column-reference.md`, `CLAUDE.md` — doc updates.

---

## Task 1: Name fallback in `process_csv` (CLI)

**Files:**
- Modify: `pseudonym.py` (insert after the composite-check block, currently ending at line 293)
- Test: `tests/test_batch.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_batch.py`:

```python
def test_name_column_standalone_encrypted(tmp_path):
    """A 'Name' column without separate Vorname/Familienname is encrypted whole."""
    src = tmp_path / "data.csv"
    src.write_text("Name,Vorname\nMustermann,Max\n", encoding="utf-8")
    dst = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(dst), "secret", "encrypt", ",")
    content = dst.read_text(encoding="utf-8")
    assert "Mustermann" not in content      # Name encrypted
    assert "Max" not in content             # Vorname encrypted
    assert "Name" in content and "Vorname" in content  # headers intact


def test_name_column_standalone_roundtrip(tmp_path):
    """Standalone 'Name' column round-trips exactly."""
    src = tmp_path / "data.csv"
    src.write_text("Name,Vorname\nMustermann,Max\nTesterin,Eva\n", encoding="utf-8")
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret123", "encrypt", ",")
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret123", "decrypt", ",")
    restored = dec.read_text(encoding="utf-8")
    assert "Mustermann" in restored and "Max" in restored
    assert "Testerin" in restored and "Eva" in restored


def test_name_not_composite_fallback_encrypted(tmp_path):
    """Name present alongside Vorname+Familienname but composite check fails
    (title) -> Name is still encrypted as a whole value, round-trips exactly."""
    src = tmp_path / "data.csv"
    src.write_text(
        "Vorname,Familienname,Name\nMax,Mustermann,Dr. Max Mustermann\n",
        encoding="utf-8",
    )
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ",")
    content = enc.read_text(encoding="utf-8")
    assert "Dr. Max Mustermann" not in content
    assert "Mustermann" not in content and "Max" not in content
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ",")
    assert "Dr. Max Mustermann" in dec.read_text(encoding="utf-8")


def test_name_composite_still_recomposed(tmp_path):
    """Regression: a real composite Name is recomposed from encrypted parts
    (value contains a space), not encrypted as one token."""
    src = tmp_path / "data.csv"
    src.write_text(
        "Vorname,Familienname,Name\nMax,Mustermann,Mustermann Max\n",
        encoding="utf-8",
    )
    enc = tmp_path / "data_pseudo.csv"
    process_file(str(src), str(enc), "secret", "encrypt", ",")
    name_field = enc.read_text(encoding="utf-8").splitlines()[1].split(",")[2]
    assert " " in name_field  # "<encFam> <encVor>", proves recomposition path
    dec = tmp_path / "data_restored.csv"
    process_file(str(enc), str(dec), "secret", "decrypt", ",")
    assert "Mustermann Max" in dec.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python3 -m pytest tests/test_batch.py -k "name_column_standalone or name_not_composite" -v`
Expected: FAIL — `test_name_column_standalone_encrypted` finds `Mustermann` in output (Name not encrypted); `test_name_not_composite_fallback_encrypted` finds `Dr. Max Mustermann`. (`test_name_composite_still_recomposed` already passes — it's a regression guard.)

- [ ] **Step 3: Implement the fallback**

In `pseudonym.py` `process_csv`, immediately AFTER the composite-check block (the `elif name_val == f"{vor_val} {fam_val}".strip():` … branch, currently ending line 293) and BEFORE the `# Ergebnis in StringIO schreiben` comment (line 295), insert:

```python
    # NAME-Spalte, die KEIN Composite ist (alleinige Namensspalte ODER
    # Composite-Erkennung gescheitert): als regulaere Identitaetsspalte den
    # ganzen Zellwert verschluesseln (deterministisch -> gleicher Token wie
    # eine Nachname-Spalte, voll reversibel).
    if name_col and not name_is_composite and name_col not in id_cols.values():
        id_cols["_name"] = name_col
```

(The existing encrypt loop at lines 310–313 then transforms the whole value; the composite block at 314–320 is skipped because `name_is_composite` is False; `cols_info` at line 329 lists it automatically.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_batch.py -k "name" -v`
Expected: PASS (all four `name_*` tests).

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `python3 -m pytest tests/test_batch.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add pseudonym.py tests/test_batch.py
git commit -m "fix: nicht-Composite Name-Spalten in CSV als Ganzwert verschluesseln

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Name fallback in `process_xlsx` (CLI)

**Files:**
- Modify: `pseudonym.py` (insert after the XLSX composite-check block, currently ending line 491)
- Test: `tests/test_batch.py`

- [ ] **Step 1: Add the openpyxl test helpers (once) + the failing test**

At the TOP of `tests/test_batch.py`, after the existing imports (after line 6), add:

```python
import io
from openpyxl import Workbook, load_workbook


def _build_xlsx_bytes(rows):
    """rows: list of lists (first row = header). Returns .xlsx bytes."""
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_xlsm(path, rows):
    """Create an .xlsm: a normal workbook + an injected dummy xl/vbaProject.bin.
    openpyxl 3.1.5 ignores the unreferenced part on load and re-merges it on
    save when keep_vba=True."""
    xlsx_bytes = _build_xlsx_bytes(rows)
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes), "r") as src, \
         zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        for item in src.infolist():
            out.writestr(item, src.read(item.filename))
        out.writestr("xl/vbaProject.bin", b"DUMMY-VBA")
```

Append this test:

```python
def test_xlsx_name_column_standalone_encrypted(tmp_path):
    """XLSX: standalone 'Name' column (no Familienname) is encrypted + round-trips."""
    src = tmp_path / "data.xlsx"
    src.write_bytes(_build_xlsx_bytes([["Name", "Vorname"], ["Mustermann", "Max"]]))
    enc = tmp_path / "data_pseudo.xlsx"
    process_file(str(src), str(enc), "secret", "encrypt")
    ws = load_workbook(enc).active
    assert ws.cell(row=2, column=1).value != "Mustermann"  # Name encrypted
    assert ws.cell(row=2, column=2).value != "Max"          # Vorname encrypted
    dec = tmp_path / "data_restored.xlsx"
    process_file(str(enc), str(dec), "secret", "decrypt")
    ws2 = load_workbook(dec).active
    assert ws2.cell(row=2, column=1).value == "Mustermann"
    assert ws2.cell(row=2, column=2).value == "Max"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_batch.py::test_xlsx_name_column_standalone_encrypted -v`
Expected: FAIL — `ws.cell(row=2, column=1).value` still equals `"Mustermann"` (Name not encrypted).

- [ ] **Step 3: Implement the XLSX fallback**

In `pseudonym.py` `process_xlsx`, immediately AFTER the composite-check block (the `elif name_val == f"{vor_val} {fam_val}".strip():` … branch, currently ending line 491) and BEFORE `sheet_count = 0` (line 493), insert (matching the existing 8-space indentation inside the `for ws in wb.worksheets:` loop):

```python
        # NAME-Spalte ohne Composite: als regulaere Spalte ganz verschluesseln
        if (name_col_idx and not name_is_composite
                and name_col_idx not in col_indices.values()):
            id_cols["_name"] = name_col_name
            col_indices["_name"] = name_col_idx
```

(The encrypt loop at 495–502 then transforms the whole value via `col_indices`; the composite block at 505–511 is skipped; `cols_info` at line 514 lists it via `id_cols`.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_batch.py::test_xlsx_name_column_standalone_encrypted -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest tests/test_batch.py -v`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add pseudonym.py tests/test_batch.py
git commit -m "fix: nicht-Composite Name-Spalten in XLSX als Ganzwert verschluesseln

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: `.xlsm` support in the CLI

**Files:**
- Modify: `pseudonym.py` — `process_file` (611), error msg (616), `process_xlsx` load (405–419), `_fix_xlsx_drawings` (386), `collect_input_files` (552–553), docstring (4), help texts (629, 638, 660)
- Modify: `.gitignore`
- Test: `tests/test_batch.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_batch.py`:

```python
def test_make_output_path_xlsm():
    assert make_output_path(Path("/d/data.xlsm"), "encrypt") == "/d/data_pseudo.xlsm"


def test_collect_input_files_xlsm_plain(tmp_path):
    x = tmp_path / "macro.xlsm"
    x.write_bytes(b"PKdummy")  # content irrelevant: collection checks suffix only
    result = collect_input_files([str(x)])
    assert len(result) == 1 and Path(result[0]).name == "macro.xlsm"


def test_collect_input_files_xlsm_in_zip(tmp_path):
    inner = tmp_path / "macro.xlsm"
    inner.write_bytes(b"PKdummy")
    zp = tmp_path / "bundle.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(inner, "macro.xlsm")
    result = collect_input_files([str(zp)])
    assert len(result) == 1 and Path(result[0]).name == "macro.xlsm"


def test_process_file_xlsm_roundtrip(tmp_path):
    src = tmp_path / "macro.xlsm"
    _make_xlsm(src, [["Vorname", "Familienname"], ["Max", "Mustermann"]])
    enc = tmp_path / "macro_pseudo.xlsm"
    process_file(str(src), str(enc), "secret123", "encrypt")
    assert enc.exists()
    ws = load_workbook(enc).active
    assert ws.cell(row=2, column=1).value != "Max"  # encrypted
    dec = tmp_path / "macro_restored.xlsm"
    process_file(str(enc), str(dec), "secret123", "decrypt")
    ws2 = load_workbook(dec).active
    assert ws2.cell(row=2, column=1).value == "Max"
    assert ws2.cell(row=2, column=2).value == "Mustermann"


def test_process_file_xlsm_preserves_vba(tmp_path):
    src = tmp_path / "macro.xlsm"
    _make_xlsm(src, [["Vorname", "Familienname"], ["Max", "Mustermann"]])
    with zipfile.ZipFile(src) as z:
        assert "xl/vbaProject.bin" in z.namelist()
    enc = tmp_path / "macro_pseudo.xlsm"
    process_file(str(src), str(enc), "secret123", "encrypt")
    with zipfile.ZipFile(enc) as z:
        assert "xl/vbaProject.bin" in z.namelist()
        assert z.read("xl/vbaProject.bin") == b"DUMMY-VBA"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_batch.py -k "xlsm" -v`
Expected: FAIL — `test_make_output_path_xlsm` passes already (generic), but `test_collect_input_files_xlsm_*` return empty lists and `test_process_file_xlsm_*` raise `ValueError: Unbekanntes Dateiformat '.xlsm'`.

- [ ] **Step 3a: Dispatch `.xlsm` to the XLSX path**

In `pseudonym.py` `process_file` (line 611), change:

```python
    if ext == ".xlsx":
```
to:
```python
    if ext in (".xlsx", ".xlsm"):
```

And the error message (line 616), change:
```python
        raise ValueError(f"Unbekanntes Dateiformat '{ext}'. Unterstuetzt: .csv, .tsv, .txt, .xlsx")
```
to:
```python
        raise ValueError(f"Unbekanntes Dateiformat '{ext}'. Unterstuetzt: .csv, .tsv, .txt, .xlsx, .xlsm")
```

- [ ] **Step 3b: Enable `keep_vba` for `.xlsm`**

In `process_xlsx`, after `transform = encrypt_value if mode == "encrypt" else decrypt_value` (line 410), add:

```python
    is_xlsm = Path(input_path).suffix.lower() == ".xlsm"
```

Change the load call (line 415) from:
```python
        wb = load_workbook(fixed_path)
```
to:
```python
        wb = load_workbook(fixed_path, keep_vba=is_xlsm)
```

- [ ] **Step 3c: Make the drawing-repair temp file keep the input extension**

In `_fix_xlsx_drawings` (line 386), change:
```python
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
```
to:
```python
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=Path(input_path).suffix)
```

(`Path` is already imported at module level.)

- [ ] **Step 3d: Accept `.xlsm` in batch + ZIP collection**

In `collect_input_files` (lines 552–553), change:
```python
    SUPPORTED = {".csv", ".tsv", ".txt", ".xlsx"}
    ZIP_EXTRACT = {".csv", ".tsv", ".xlsx"}
```
to:
```python
    SUPPORTED = {".csv", ".tsv", ".txt", ".xlsx", ".xlsm"}
    ZIP_EXTRACT = {".csv", ".tsv", ".xlsx", ".xlsm"}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_batch.py -k "xlsm" -v`
Expected: PASS (all `xlsm` tests, including VBA preservation).

- [ ] **Step 5: Update CLI help/docstring text**

- Line 4 (module docstring): `Keine separate Key-Datei noetig. Unterstuetzt CSV und XLSX.` → `Keine separate Key-Datei noetig. Unterstuetzt CSV, XLSX und XLSM.`
- Line 629: `help="Pfad(e) zu CSV/XLSX/ZIP-Datei(en)")` → `help="Pfad(e) zu CSV/XLSX/XLSM/ZIP-Datei(en)")`
- Line 638: `help="CSV-Trennzeichen (Standard: Komma, wird bei XLSX ignoriert)")` → `help="CSV-Trennzeichen (Standard: Komma, wird bei XLSX/XLSM ignoriert)")`
- Line 660: `print("FEHLER: Keine verarbeitbaren Dateien gefunden (CSV/XLSX).", file=sys.stderr)` → `print("FEHLER: Keine verarbeitbaren Dateien gefunden (CSV/XLSX/XLSM).", file=sys.stderr)`

- [ ] **Step 6: Add `*.xlsm` to `.gitignore`**

In `.gitignore`, in the "Sensible Daten" block, after the `*.xlsx` line add:
```
*.xlsm
```

- [ ] **Step 7: Run the full suite + smoke-check the CLI banner**

Run: `python3 -m pytest tests/test_batch.py -v`
Expected: PASS (all tests).
Run: `python3 pseudonym.py --help`
Expected: usage text mentions `CSV/XLSX/XLSM`.

- [ ] **Step 8: Commit**

```bash
git add pseudonym.py tests/test_batch.py .gitignore
git commit -m "feat: .xlsm-Support in der CLI (keep_vba, Batch/ZIP, Dispatch)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Name fallback in the browser GUI

**Files:**
- Modify: `pseudonym_gui.html` — Name logic (~828–852), info popup (259)
- Verify: manual browser check + cross-implementation token

There is no JS test harness; verification is manual in the browser plus a cross-implementation token check against the CLI.

- [ ] **Step 1: Add the GUI fallback**

In `pseudonym_gui.html`, after the composite-detection block (the lines computing `nameIsComposite`/`nameOrder`, currently ending at line 837 with the `}` that closes `if (nameColIdx >= 0 && famIdx >= 0 && vorIdx >= 0 ...)`) and BEFORE `const customInSheet = ...` (line 838), insert:

```javascript
      // NAME-Spalte ohne Composite: als regulaere Spalte ganz verschluesseln
      if (nameColIdx >= 0 && !nameIsComposite && !Object.values(colIndices).includes(nameColIdx)) {
        colIndices['_name'] = nameColIdx;
      }
```

(The encrypt loop at lines 845–848 iterates `colIndices` and transforms the whole value; the composite block at 849–852 is skipped because `nameIsComposite` is false. `colInfo` at line 839 is built from `idCols` and will not list `_name` — acceptable; the log still shows the other columns.)

- [ ] **Step 2: Update the info-popup row**

In `pseudonym_gui.html` line 259, change:
```html
              <tr><td>Name</td><td>NAME — auto-composite aus Familienname + Vorname</td></tr>
```
to:
```html
              <tr><td>Name</td><td>Composite aus Familienname + Vorname — sonst wird der ganze Wert verschluesselt</td></tr>
```

- [ ] **Step 3: Cross-implementation token check (CLI baseline)**

Run: `python3 -c "from pseudonym import derive_key, encrypt_value; print(encrypt_value(derive_key('testSecret123'), 'Mueller'))"`
Expected output: `a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc`

- [ ] **Step 4: Manual browser verification**

1. Open `pseudonym_gui.html` in a browser.
2. Create a small CSV locally with content `Name,Vorname\nMueller,Hans\n` and upload it; secret `testSecret123`, mode encrypt.
3. Confirm the downloaded output: the `Name` value for `Mueller` equals `a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc` (identical to the CLI token in Step 3) and `Hans` is encrypted.
4. Re-upload the encrypted file in decrypt mode with the same secret; confirm `Mueller` and `Hans` are restored.

Expected: GUI token for `Mueller` matches the CLI token exactly; round-trip restores originals.

- [ ] **Step 5: Commit**

```bash
git add pseudonym_gui.html
git commit -m "fix: nicht-Composite Name-Spalten in der GUI als Ganzwert verschluesseln

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `.xlsm` support in the browser GUI

**Files:**
- Modify: `pseudonym_gui.html` — `accept` (222), file-type detection (543, 555), XLSX writer (868–873)
- Verify: manual browser check

- [ ] **Step 1: Accept `.xlsm` in the file picker**

Line 222, change:
```html
    <input type="file" id="fileInput" accept=".csv,.xlsx,.tsv,.txt,.zip" multiple style="display:none">
```
to:
```html
    <input type="file" id="fileInput" accept=".csv,.xlsx,.xlsm,.tsv,.txt,.zip" multiple style="display:none">
```

- [ ] **Step 2: Detect `.xlsm` as an xlsx-type file**

Line 543 (ZIP member), change:
```javascript
          const ftype = name.match(/\.xlsx$/i) ? 'xlsx' : 'csv';
```
to:
```javascript
          const ftype = name.match(/\.(xlsx|xlsm)$/i) ? 'xlsx' : 'csv';
```

Line 555 (direct upload), change:
```javascript
      const ftype = file.name.match(/\.xlsx$/i) ? 'xlsx' : 'csv';
```
to:
```javascript
      const ftype = file.name.match(/\.(xlsx|xlsm)$/i) ? 'xlsx' : 'csv';
```

- [ ] **Step 3: Write `.xlsm` output with the right bookType + a macro-loss hint**

Lines 868–873, change:
```javascript
    if (fq.type === 'xlsx') {
      const wb = XLSX.utils.book_new();
      for (const rs of resultSheets) { const data = [...(rs.metaRows||[]), rs.headers, ...rs.rows]; const ws = XLSX.utils.aoa_to_sheet(data); XLSX.utils.book_append_sheet(wb, ws, rs.name); }
      const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
      blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      outName = fq.name.replace(/\.xlsx$/i, suffix + '.xlsx');
    } else {
```
to:
```javascript
    if (fq.type === 'xlsx') {
      const wb = XLSX.utils.book_new();
      for (const rs of resultSheets) { const data = [...(rs.metaRows||[]), rs.headers, ...rs.rows]; const ws = XLSX.utils.aoa_to_sheet(data); XLSX.utils.book_append_sheet(wb, ws, rs.name); }
      const isXlsm = /\.xlsm$/i.test(fq.name);
      if (isXlsm) log('  Hinweis: .xlsm — Makros und Formatierung gehen in der Browser-Version verloren (Daten werden korrekt verschluesselt).', 'warn');
      const wbout = XLSX.write(wb, { bookType: isXlsm ? 'xlsm' : 'xlsx', type: 'array' });
      const mime = isXlsm ? 'application/vnd.ms-excel.sheet.macroEnabled.12' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
      blob = new Blob([wbout], { type: mime });
      const outExt = isXlsm ? '.xlsm' : '.xlsx';
      outName = fq.name.replace(/\.(xlsx|xlsm)$/i, suffix + outExt);
    } else {
```

- [ ] **Step 4: Manual browser verification**

1. Open `pseudonym_gui.html`. Upload an `.xlsm` containing identity columns (e.g. `Vorname`, `Familienname`); secret `test`, mode encrypt.
2. Confirm: the warning hint is logged, a `*_pseudo.xlsm` file downloads, the identity values are encrypted, and the file opens in Excel.
3. Re-upload the encrypted `.xlsm` in decrypt mode with the same secret; confirm originals are restored.

Expected: `.xlsm` is accepted, processed, downloaded as `.xlsm`, round-trips; macro-loss hint shown.

- [ ] **Step 5: Commit**

```bash
git add pseudonym_gui.html
git commit -m "feat: .xlsm-Support in der GUI (Upload, Erkennung, bookType, Hinweis)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Documentation + version bump

**Files:**
- Modify: `pseudonym.py` (36), `pseudonym_gui.html` (207), `README.md`, `ANLEITUNG_pseudonym.md`, `docs/column-reference.md`, `CLAUDE.md`

No tests. Apply each edit, then verify with grep.

- [ ] **Step 1: Bump versions**

`pseudonym.py` line 36: `__version__ = "0.5.0"` → `__version__ = "0.6.0"`

`pseudonym_gui.html` line 207: change the `v0.5.0` in the banner to `v0.6.0` (the line reading `...">v0.5.0 — MedUni Wien — AES-256-CBC, kompatibel mit pseudonym.py</div>`).

- [ ] **Step 2: README.md**

Run: `grep -n -i "xlsx\|\.xls\b\|Name\b" README.md` to locate the supported-formats list and the column table.
- In every place that enumerates supported formats (`.csv`, `.xlsx`, …), add `.xlsm`. State that the CLI preserves macros (`keep_vba`) and the browser GUI processes `.xlsm` data but drops macros/formatting.
- In the column-recognition table, update the `Name` entry to read: *"Composite aus Familienname + Vorname; ist es kein Composite, wird der ganze Wert verschlüsselt."*

- [ ] **Step 3: ANLEITUNG_pseudonym.md**

Run: `grep -n -i "xlsx\|Name" ANLEITUNG_pseudonym.md` to locate format mentions and the column table. Apply the same two changes as in Step 2 (add `.xlsm`; update the `Name` description).

- [ ] **Step 4: docs/column-reference.md**

Run: `grep -n -i "Name\|composite\|xlsx" docs/column-reference.md`. Update the `Name`/`NAME` section to document both behaviours: composite recomposition when `Vorname`+`Familienname` are present and match; otherwise whole-value encryption. If the file lists supported file types, add `.xlsm`.

- [ ] **Step 5: CLAUDE.md**

- In the Project Overview / "Encoding Support" / "Build & Test Commands" sections, change "CSV and XLSX" style mentions to include `.xlsm`, and note `process_xlsx` uses `keep_vba=True` for `.xlsm` (macros preserved in CLI; GUI drops them).
- In the "NAME column" paragraph (under Column Recognition), append: *"If a `Name` column is not a composite (no separate Vorname+Familienname, or the composite check fails), the whole value is encrypted as a single token."*

- [ ] **Step 6: Verify doc edits**

Run: `grep -rn -i "xlsm" README.md ANLEITUNG_pseudonym.md docs/column-reference.md CLAUDE.md`
Expected: each file shows at least one `.xlsm` mention.
Run: `grep -rn "0.6.0" pseudonym.py pseudonym_gui.html`
Expected: both files show `0.6.0`.

- [ ] **Step 7: Commit**

```bash
git add pseudonym.py pseudonym_gui.html README.md ANLEITUNG_pseudonym.md docs/column-reference.md CLAUDE.md
git commit -m "docs: .xlsm-Support + Name-Spalten-Verhalten dokumentieren, v0.6.0

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Final cross-implementation + full verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `python3 -m pytest tests/test_batch.py -v`
Expected: PASS (all tests, including the new Name and `.xlsm` tests).

- [ ] **Step 2: CLI roundtrip smoke test on a real `.xlsm`**

(Use any local `.xlsm` with identity columns — do NOT commit it; `.xlsm` is gitignored.)
```bash
python3 pseudonym.py encrypt /pfad/zur/datei.xlsm --secret "test"
python3 pseudonym.py decrypt /pfad/zur/datei_pseudo.xlsm --secret "test"
```
Expected: encrypt reports encrypted cells; the `_pseudo.xlsm` still contains `xl/vbaProject.bin` (check with `unzip -l`); decrypt restores values.

- [ ] **Step 3: Confirm both implementations agree on the known vector**

CLI: `python3 -c "from pseudonym import derive_key, encrypt_value; print(encrypt_value(derive_key('testSecret123'), 'Mueller'))"` → `a9hB-p5pLs7rcmnUUFNdDD2a2KN4R1bUd2LjIkYJXRc`
GUI: confirmed in Task 4 Step 4 (token for `Mueller` matches).

- [ ] **Step 4: Decide branch completion**

Invoke `superpowers:finishing-a-development-branch` to choose merge/PR/cleanup for branch `feat/name-fix-xlsm-support`.

---

## Self-Review (completed)

- **Spec coverage:** Name fix CSV (Task 1) ✓, Name fix XLSX (Task 2) ✓, Name fix GUI (Task 4) ✓, `.xlsm` CLI incl. `keep_vba`/collect/dispatch/texts (Task 3) ✓, `.xlsm` GUI (Task 5) ✓, `.gitignore` (Task 3 Step 6) ✓, tests incl. VBA preservation (Tasks 1–3) ✓, cross-impl token (Tasks 4 & 7) ✓, docs + version bump (Task 6) ✓.
- **Placeholder scan:** All code steps contain concrete code; doc steps give exact target text + grep locators (doc prose varies per file, so locate-then-edit is intentional, not a placeholder).
- **Type/name consistency:** synthetic key `_name` used identically in `process_csv` (`id_cols`), `process_xlsx` (`id_cols` + `col_indices`), and GUI (`colIndices`); `is_xlsm`/`isXlsm` local to their files; helper names `_build_xlsx_bytes`/`_make_xlsm` defined once in Task 2 Step 1 and reused in Task 3.
