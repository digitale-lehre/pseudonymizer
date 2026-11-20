// Fuehrt den Skriptteil von pseudonym_gui.html in Node aus (mit einer Attrappe der Seite),
// damit sich die Browser-Oberflaeche ohne Browser gegen pseudonym.py pruefen laesst.
//
// Die Bibliotheken (SheetJS, JSZip) kommen aus der HTML-Datei selbst, in derselben
// Reihenfolge wie im Browser: erst der eigene Code, dann die eingebetteten Bibliotheken.
//
// Aufruf:  node gui_harness.js <pseudonym_gui.html> <auftrag.json>
//   auftrag: {"jobs": [{"files": [Pfade], "mode": "encrypt", "secret": "...",
//             "extraCols": [], "outDir": "...", "download": false, "sep": null}], "eval": [Ausdruecke]}
// Ausgabe: JSON mit einem Eintrag je Auftrag.
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

const [htmlPath, jobPath] = process.argv.slice(2);
const html = fs.readFileSync(htmlPath, 'utf8');

// ---- Attrappe der Seite ----
const els = {};
function mkEl(id) {
  const classes = new Set();
  return {
    id, value: '', textContent: '', innerHTML: '', className: '', style: {}, dataset: {}, type: 'password',
    files: [], scrollTop: 0, scrollHeight: 0, disabled: false, href: '', download: '',
    classList: {
      add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c),
      toggle: (c, on) => { const want = on === undefined ? !classes.has(c) : !!on; if (want) classes.add(c); else classes.delete(c); return want; },
    },
    addEventListener() {}, querySelectorAll() { return []; }, click() {}, remove() {}, appendChild() {},
  };
}
const store = {};
const storageWrites = [];
const alerts = [];
globalThis.document = {
  getElementById: (id) => (els[id] ||= mkEl(id)),
  documentElement: mkEl('html'),
  body: mkEl('body'),
  addEventListener() {},
  createElement: () => mkEl('new'),
};
globalThis.window = globalThis;
globalThis.addEventListener = () => {};
globalThis.matchMedia = () => ({ matches: false });
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); storageWrites.push([k, String(v)]); },
    removeItem: (k) => { delete store[k]; },
  },
});
globalThis.alert = (m) => alerts.push(m);

const script = html.match(/<script id="app">\r?\n([\s\S]*?)<\/script>/)[1];
vm.runInThisContext(script, { filename: 'pseudonym_gui.inline.js' });

// Eingebettete Bibliotheken: nur ausfuehren, wenn der Code zur Pruefsumme im Tag passt
for (const m of html.matchAll(/<script id="(lib-[a-z]+)"([^>]*)>([\s\S]*?)<\/script>/g)) {
  const code = m[3].replace(/\r\n/g, '\n');
  const expected = (m[2].match(/data-sha512="([^"]+)"/) || [])[1];
  if (crypto.createHash('sha512').update(code, 'utf8').digest('base64') !== expected) {
    console.error(`${m[1]}: Code passt nicht zur Pruefsumme in der HTML-Datei`);
    process.exit(2);
  }
  vm.runInThisContext(code, { filename: `${m[1]}.js` });
}
if (typeof XLSX === 'undefined' || typeof JSZip === 'undefined') {
  console.error('Die HTML-Datei enthaelt die Bibliotheken nicht.');
  process.exit(2);
}
const run = (code) => vm.runInThisContext(code);

function asFile(p) {
  const bytes = fs.readFileSync(p);
  const name = path.basename(p);
  const u = new Uint8Array(bytes);
  return { name, arrayBuffer: async () => u.buffer.slice(u.byteOffset, u.byteOffset + u.byteLength) };
}

async function runJob(job) {
  run('fileQueue = []; customCols.clear(); activeFileIdx = 0; activeSheet = 0; invalidateResults();');
  for (const c of job.extraCols || []) run(`customCols.add(${JSON.stringify(c)})`);
  const started = Date.now();
  await globalThis.addFiles(job.files.map(asFile));
  if (job.sep) {
    run(`fileQueue.forEach(f => { if (f.type === 'csv') { f.sep = ${JSON.stringify(job.sep)}; f.sepManual = true; parseOneFile(f); } })`);
  }
  const loadMs = Date.now() - started;
  globalThis.setMode(job.mode);
  document.getElementById('secretInput').value = job.secret || '';
  const t1 = Date.now();
  await globalThis.processFile();
  const processMs = Date.now() - t1;

  const results = [];
  for (const r of run('batchResults')) {
    const entry = { ok: r.ok, name: r.name, source: r.source.name, error: r.error || null, cells: r.cells, failed: r.failed };
    if (r.ok && job.outDir) fs.writeFileSync(path.join(job.outDir, r.name), Buffer.from(await r.blob.arrayBuffer()));
    results.push(entry);
  }
  let download = null;
  if (job.download) {
    const dl = await globalThis.buildDownload();
    if (dl) {
      download = { name: dl.name, size: dl.blob.size };
      if (job.outDir) fs.writeFileSync(path.join(job.outDir, dl.name), Buffer.from(await dl.blob.arrayBuffer()));
    }
  }
  return {
    results, download, loadMs, processMs,
    notices: run('loadNotices').slice(),
    queue: run('fileQueue').map((f) => ({ name: f.name, type: f.type, encoding: f.encoding, sep: f.sep || null })),
    log: document.getElementById('logArea').innerHTML.replace(/<[^>]+>/g, ''),
    resultCardHidden: document.getElementById('resultCard').classList.contains('hidden'),
    alerts: alerts.splice(0),
    storageWrites: storageWrites.splice(0),
    heapMb: Math.round(process.memoryUsage().heapUsed / 1048576),
  };
}

(async () => {
  const spec = JSON.parse(fs.readFileSync(jobPath, 'utf8'));
  const out = { jobs: [], eval: [] };
  for (const job of spec.jobs || []) out.jobs.push(await runJob(job));
  for (const code of spec.eval || []) out.eval.push(await run(code));
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
