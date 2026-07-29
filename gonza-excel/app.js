/* Sincronizador Excel — hojas JULIO y VALORES.
 * Todo en el navegador con SheetJS. Sin backend ni almacenamiento:
 * al recargar la página se pide subir los archivos de nuevo.
 *
 * Flujo:
 *  1. Se sube el maestro (VARIABLES.xlsm). Se conserva el blob VBA (macros).
 *  2. Se suben archivos nuevos. De cada uno se leen SOLO las hojas cuyo
 *     título coincida con JULIO o VALORES.
 *  3. JULIO  -> filas nuevas se agregan al final; columna ESTADO = LEÍDO.
 *     VALORES -> filas por DETALLE: actualiza valores o agrega; ESTADO = LEÍDO.
 *  4. Cada archivo leído queda anotado en la hoja CONTROL_LECTURAS con su
 *     huella (hash) y estado LEÍDO: si se vuelve a subir, se omite.
 */

const CONTROL_SHEET = 'CONTROL_LECTURAS';
const TARGET_SHEETS = ['JULIO', 'VALORES'];

let master = null;        // { wb, name }
let incoming = [];        // [{ name, wb, hash }]
let dirty = false;

const $ = (id) => document.getElementById(id);
const log = $('log');

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function msg(kind, html) {
  const d = document.createElement('div');
  d.className = 'msg ' + kind;
  d.innerHTML = html;
  log.appendChild(d);
}

function clearLog() {
  log.innerHTML = '';
  $('preview').innerHTML = '';
}

function normName(s) {
  return String(s || '').trim().toUpperCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function findSheet(wb, wanted) {
  return wb.SheetNames.find((n) => normName(n) === normName(wanted));
}

async function fileHash(buf) {
  const h = await crypto.subtle.digest('SHA-256', buf);
  return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
}

function readWb(buf) {
  return XLSX.read(buf, { type: 'array', bookVBA: true, cellDates: true, cellNF: true });
}

// ---------- carga de archivos ----------
function wireDrop(dropId, inputId, onFiles) {
  const drop = $(dropId), input = $(inputId);
  drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('over'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('over');
    onFiles([...e.dataTransfer.files]);
  });
  input.addEventListener('change', () => onFiles([...input.files]));
}

wireDrop('drop-master', 'file-master', async (files) => {
  if (!files.length) return;
  clearLog();
  const f = files[0];
  try {
    const buf = await f.arrayBuffer();
    const wb = readWb(buf);
    const missing = TARGET_SHEETS.filter((t) => !findSheet(wb, t));
    if (missing.length) {
      msg('err', `El maestro no tiene la(s) hoja(s): <b>${esc(missing.join(', '))}</b>`);
      return;
    }
    master = { wb, name: f.name };
    dirty = false;
    $('drop-master').classList.add('loaded');
    $('master-label').innerHTML = `Maestro cargado: <span class="file-tag">${esc(f.name)}</span>`;
    updateButtons();
  } catch (e) {
    msg('err', 'No se pudo leer el maestro: ' + esc(e.message));
  }
});

wireDrop('drop-in', 'file-in', async (files) => {
  if (!files.length) return;
  incoming = [];
  for (const f of files) {
    try {
      const buf = await f.arrayBuffer();
      const hash = await fileHash(buf);
      incoming.push({ name: f.name, wb: readWb(buf), hash });
    } catch (e) {
      msg('err', `No se pudo leer <b>${esc(f.name)}</b>: ${esc(e.message)}`);
    }
  }
  if (incoming.length) {
    $('drop-in').classList.add('loaded');
    $('in-label').innerHTML = `Archivos cargados: <span class="file-tag">${esc(incoming.map((i) => i.name).join(', '))}</span>`;
  }
  updateButtons();
});

function updateButtons() {
  $('btn-process').disabled = !(master && incoming.length);
  $('btn-download').disabled = !(master && dirty);
}

// ---------- hoja de control ----------
function getControlRows() {
  const ws = master.wb.Sheets[CONTROL_SHEET];
  if (!ws) return [];
  return XLSX.utils.sheet_to_json(ws, { header: 1 }).slice(1);
}

function appendControl(rows) {
  const header = ['FECHA', 'ARCHIVO', 'HUELLA', 'HOJA', 'FILAS INSERTADAS', 'ESTADO'];
  const prev = getControlRows();
  const all = [header, ...prev, ...rows];
  const ws = XLSX.utils.aoa_to_sheet(all);
  ws['!cols'] = [{ wch: 19 }, { wch: 34 }, { wch: 18 }, { wch: 10 }, { wch: 16 }, { wch: 10 }];
  if (!master.wb.Sheets[CONTROL_SHEET]) master.wb.SheetNames.push(CONTROL_SHEET);
  master.wb.Sheets[CONTROL_SHEET] = ws;
}

function alreadyRead(hash) {
  return getControlRows().some((r) => String(r[2]) === hash && String(r[5]) === 'LEÍDO');
}

// ---------- utilidades de hoja ----------
function sheetToMatrix(ws) {
  return XLSX.utils.sheet_to_json(ws, { header: 1, defval: null, raw: true });
}

function rowFingerprint(row, cols) {
  return cols.map((c) => String(row[c] ?? '').trim().toUpperCase()).join('|');
}

function lastDataRow(matrix) {
  for (let i = matrix.length - 1; i >= 0; i--) {
    if (matrix[i] && matrix[i].some((v) => v !== null && v !== '')) return i;
  }
  return 0;
}

function cellRef(r, c) {
  return XLSX.utils.encode_cell({ r, c });
}

// sheet_to_json indexa desde el inicio de !ref (p.ej. VALORES parte en A2);
// este offset convierte índice de matriz -> fila/columna absoluta de la hoja.
function refOffset(ws) {
  const s = XLSX.utils.decode_range(ws['!ref']).s;
  return { r: s.r, c: s.c };
}

function setCell(ws, r, c, v) {
  ws[cellRef(r, c)] = typeof v === 'number' ? { t: 'n', v } : { t: 's', v: String(v) };
  const range = XLSX.utils.decode_range(ws['!ref']);
  range.e.r = Math.max(range.e.r, r);
  range.e.c = Math.max(range.e.c, c);
  ws['!ref'] = XLSX.utils.encode_range(range);
}

// ---------- inserción JULIO (órdenes de trabajo) ----------
function mergeJulio(masterWs, inWs) {
  const mm = sheetToMatrix(masterWs);
  const im = sheetToMatrix(inWs);
  const off = refOffset(masterWs);
  const header = mm[0] || [];
  // columna ESTADO: primera cabecera vacía después de las columnas con nombre
  let estadoCol = header.findIndex((h, i) => i >= 8 && (h === null || h === ''));
  if (estadoCol === -1) estadoCol = header.length;
  const KEY_COLS = [0, 2, 3, 4, 5, 6]; // Cliente, OT, OC/VIN, Equipamiento, Modelo, CANT
  const seen = new Set();
  for (let i = 1; i < mm.length; i++) {
    if (mm[i] && mm[i].some((v) => v !== null && v !== '')) {
      seen.add(rowFingerprint(mm[i], KEY_COLS));
    }
  }
  setCell(masterWs, off.r, off.c + estadoCol, 'ESTADO');
  let r = lastDataRow(mm) + 1;
  const inserted = [];
  for (let i = 1; i < im.length; i++) {
    const row = im[i];
    if (!row || !(row[0] || row[2])) continue;           // sin Cliente ni OT
    const fp = rowFingerprint(row, KEY_COLS);
    if (seen.has(fp)) continue;                          // ya existe en el maestro
    seen.add(fp);
    row.forEach((v, c) => {
      if (v !== null && v !== '') setCell(masterWs, off.r + r, off.c + c, v instanceof Date ? v.toLocaleDateString('es-CL') : v);
    });
    setCell(masterWs, off.r + r, off.c + estadoCol, 'LEÍDO');
    inserted.push({ fila: off.r + r + 1, datos: row.slice(0, 8) });
    r++;
  }
  return inserted;
}

// ---------- inserción VALORES (tarifas por DETALLE) ----------
function mergeValores(masterWs, inWs) {
  const mm = sheetToMatrix(masterWs);
  const im = sheetToMatrix(inWs);
  const off = refOffset(masterWs);
  // en el maestro, DETALLE está en la columna B (índice 1); valores en C-E
  const byDetalle = new Map();
  for (let i = 0; i < mm.length; i++) {
    const d = mm[i] && mm[i][1];
    if (d) byDetalle.set(normName(d), i);
  }
  const estadoCol = 5; // columna F
  const inserted = [];
  let last = lastDataRow(mm);
  for (let i = 0; i < im.length; i++) {
    const row = im[i];
    const d = row && row[1];
    if (!d || normName(d) === 'DETALLE') continue;
    const values = [row[2], row[3], row[4]];
    if (values.every((v) => v === null || v === '')) continue;
    let r = byDetalle.get(normName(d));
    if (r === undefined) {
      r = ++last;
      setCell(masterWs, off.r + r, off.c + 1, d);
      byDetalle.set(normName(d), r);
    }
    values.forEach((v, k) => {
      if (v !== null && v !== '') setCell(masterWs, off.r + r, off.c + 2 + k, v);
    });
    setCell(masterWs, off.r + r, off.c + estadoCol, 'LEÍDO');
    inserted.push({ fila: off.r + r + 1, datos: [d, ...values] });
  }
  return inserted;
}

// ---------- proceso ----------
$('btn-process').addEventListener('click', () => {
  clearLog();
  if (!master || !incoming.length) return;
  const controlRows = [];
  const previewRows = [];
  const now = new Date().toLocaleString('es-CL');

  for (const file of incoming) {
    if (alreadyRead(file.hash)) {
      msg('warn', `<b>${esc(file.name)}</b>: ya fue leído antes (misma huella) — omitido.`);
      continue;
    }
    let any = false;
    for (const target of TARGET_SHEETS) {
      const inName = findSheet(file.wb, target);
      if (!inName) continue;
      const masterName = findSheet(master.wb, target);
      const inserted = target === 'JULIO'
        ? mergeJulio(master.wb.Sheets[masterName], file.wb.Sheets[inName])
        : mergeValores(master.wb.Sheets[masterName], file.wb.Sheets[inName]);
      any = true;
      controlRows.push([now, file.name, file.hash, target, inserted.length, 'LEÍDO']);
      if (inserted.length) {
        msg('ok', `<b>${esc(file.name)}</b> → hoja <b>${target}</b>: ${inserted.length} fila(s) insertada(s), estado LEÍDO.`);
        previewRows.push(...inserted.map((x) => ({ hoja: target, ...x })));
      } else {
        msg('warn', `<b>${esc(file.name)}</b> → hoja <b>${target}</b>: sin filas nuevas (todo ya existía).`);
      }
    }
    if (!any) {
      msg('err', `<b>${esc(file.name)}</b>: no tiene hojas llamadas JULIO ni VALORES.`);
    }
  }

  if (controlRows.length) {
    appendControl(controlRows);
    dirty = true;
  }
  renderPreview(previewRows);
  // siempre se pide volver a subir: los entrantes no se guardan
  incoming = [];
  $('drop-in').classList.remove('loaded');
  $('in-label').textContent = 'Haz clic o arrastra aquí los archivos nuevos';
  $('file-in').value = '';
  updateButtons();
});

function renderPreview(rows) {
  const el = $('preview');
  el.innerHTML = '';
  if (!rows.length) return;
  const table = document.createElement('table');
  table.innerHTML = '<tr><th>Hoja</th><th>Fila</th><th>Datos insertados</th><th>Estado</th></tr>';
  for (const r of rows.slice(0, 60)) {
    const tr = document.createElement('tr');
    const datos = r.datos.filter((v) => v !== null && v !== '').map((v) =>
      v instanceof Date ? v.toLocaleDateString('es-CL') : v).join(' · ');
    tr.innerHTML = `<td>${r.hoja}</td><td>${r.fila}</td><td></td><td class="estado">LEÍDO</td>`;
    tr.children[2].textContent = datos;
    table.appendChild(tr);
  }
  el.appendChild(table);
  if (rows.length > 60) {
    const d = document.createElement('div');
    d.className = 'msg ok';
    d.textContent = `… y ${rows.length - 60} filas más.`;
    el.appendChild(d);
  }
}

// ---------- descarga ----------
$('btn-download').addEventListener('click', () => {
  if (!master) return;
  const isXlsm = /\.xlsm$/i.test(master.name) && master.wb.vbaraw;
  const out = XLSX.write(master.wb, {
    type: 'array',
    bookType: isXlsm ? 'xlsm' : 'xlsx',
    bookVBA: !!master.wb.vbaraw,
    cellDates: true,
  });
  const blob = new Blob([out], { type: 'application/octet-stream' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const base = master.name.replace(/\.(xlsx|xlsm|xls)$/i, '');
  a.download = `${base} ACTUALIZADO.${isXlsm ? 'xlsm' : 'xlsx'}`;
  a.click();
  URL.revokeObjectURL(a.href);
});
