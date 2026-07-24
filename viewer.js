import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import * as BufferGeometryUtils from 'three/addons/utils/BufferGeometryUtils.js';

// Weld duplicated vertices and smooth normals (30° crease) so the tubes
// render like the CAD drawings instead of showing tessellation facets.
function smoothGeometry(geometry) {
  let g = BufferGeometryUtils.mergeVertices(geometry, 1e-4);
  g = BufferGeometryUtils.toCreasedNormals(g, Math.PI / 6);
  return g;
}

const MODELS = {
  barrera_armada: {
    label: 'Barrera antivuelco — armada',
    file: 'models/barrera_armada.obj',
    assembled: true,
  },
  enganche_armado: {
    label: 'Enganche Hilux — armado',
    file: 'models/enganche_armado.obj',
    assembled: true,
  },
  barra_ext_6m: { label: 'Barra exterior 6M — piezas', file: 'models/barra_ext_6m.obj' },
  barra_int_hilux: { label: 'Barra interior Hilux — piezas', file: 'models/barra_int_hilux.obj' },
  barra_int_l200: { label: 'Barra interior L200 — piezas', file: 'models/barra_int_l200.obj' },
  barra_int_colorado: { label: 'Barra interior Colorado — piezas', file: 'models/barra_int_colorado.obj' },
  barra_int_poer: { label: 'Barra interior POER — piezas', file: 'models/barra_int_poer.obj' },
  enganche_hilux: { label: 'Enganche Hilux — piezas', file: 'models/enganche_hilux.obj' },
  enganche_l200: { label: 'Enganche L200 — piezas', file: 'models/enganche_l200.obj' },
  portarruedas_kitcar: { label: 'Portarruedas Kitcar — piezas', file: 'models/portarruedas_kitcar.obj' },
  portarruedas_mitta: { label: 'Portarruedas Mitta — piezas', file: 'models/portarruedas_mitta.obj' },
  portarruedas_tipo_t: { label: 'Portarruedas Tipo T — piezas', file: 'models/portarruedas_tipo_t.obj' },
};

// AutoCAD ACI colors per solid index (from the DWG), softened for viewing.
const ACI_COLORS = {
  1: 0xd9534f,   // red
  2: 0xd4b942,   // yellow
  3: 0x5cb85c,   // green
  5: 0x4da3ff,   // blue
  256: 0x9aa5b1, // bylayer -> steel gray
};
const SOLID_ACI = {
  enganche: [3, 1, 3, 256, 2, 5, 5, 1, 2, 2, 2],
  barrera: [256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256, 256],
};
// Fallback palette when everything is bylayer, so parts are distinguishable.
// Steel grays with subtle tints, like the shaded views in the drawings.
const FALLBACK_PALETTE = [
  0x9aa2ac, 0x98a0b0, 0xa4a8ae, 0x9ba8a4, 0xaba49c,
  0x9fa4b4, 0xaaa89e, 0xa39ead, 0x97aaa8, 0xac9ea4,
  0xa0ab9c, 0x9aa0b8,
];

// Colores por pieza para los modelos armados (estilo vista 3D de la lamina).
const NAME_COLORS = [
  ['arco', 0x5b7fb5],
  ['pata', 0x5fa88a],
  ['placas_base', 0xd28bb0],
  ['placas', 0x8f9bb0],
  ['discos', 0xe0913f],
  ['pertiga', 0xb5a05f],
  ['focos', 0x6a6f78],
  ['anclaje', 0xc98b5a],
  ['malla', 0x9aa4b0],
  ['barra', 0x5b7fb5],
  ['soporte', 0x5fa88a],
  ['bola', 0xe0913f],
];

function colorForName(name) {
  for (const [prefix, c] of NAME_COLORS) {
    if (name.startsWith(prefix)) return c;
  }
  return null;
}

const container = document.getElementById('canvas-container');
const loadingEl = document.getElementById('loading');
const hudInfo = document.getElementById('hud-info');

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(container.clientWidth, container.clientHeight);
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf2f3f5);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100000);
camera.up.set(0, 0, 1); // CAD convention: Z up
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const key = new THREE.DirectionalLight(0xffffff, 1.4);
key.position.set(1, -1, 1.5);
scene.add(key);
const fill = new THREE.DirectionalLight(0xffffff, 0.55);
fill.position.set(-1.2, 1, -0.6);
scene.add(fill);
const hemi = new THREE.HemisphereLight(0xffffff, 0x8a929e, 0.55);
scene.add(hemi);

let gridHelper = null;
let axesHelper = null;
let modelGroup = null;
let wireframe = false;
let currentModel = null;
const solidMeshes = []; // { name, meshes[], color, visible }

function clearModel() {
  if (modelGroup) {
    scene.remove(modelGroup);
    modelGroup.traverse((o) => {
      if (o.isMesh) {
        o.geometry.dispose();
        o.material.dispose();
      }
    });
    modelGroup = null;
  }
  solidMeshes.length = 0;
}

function buildHelpers(radius, center) {
  if (gridHelper) scene.remove(gridHelper);
  if (axesHelper) scene.remove(axesHelper);
  const size = Math.pow(10, Math.ceil(Math.log10(radius * 2.5)));
  gridHelper = new THREE.GridHelper(size, 20, 0xb8bfc9, 0xdcdfe4);
  gridHelper.rotation.x = Math.PI / 2; // grid on XY plane (Z up)
  gridHelper.position.set(center.x, center.y, 0);
  gridHelper.visible = document.getElementById('btn-grid').classList.contains('toggled');
  scene.add(gridHelper);
  axesHelper = new THREE.AxesHelper(radius * 1.2);
  axesHelper.position.copy(center);
  axesHelper.visible = document.getElementById('btn-axes').classList.contains('toggled');
  scene.add(axesHelper);
}

function fitView(target) {
  const obj = target || modelGroup;
  if (!obj) return;
  const box = new THREE.Box3().setFromObject(obj);
  if (box.isEmpty()) return;
  const center = box.getCenter(new THREE.Vector3());
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const dist = sphere.radius / Math.tan((camera.fov * Math.PI) / 360) * 1.15;
  const dir = new THREE.Vector3(1, -1, 0.7).normalize();
  camera.position.copy(center).addScaledVector(dir, dist);
  camera.near = dist / 100;
  camera.far = dist * 100;
  camera.updateProjectionMatrix();
  controls.target.copy(center);
  controls.update();
}

let gridLayout = true;

// The DWG modelspace has the parts scattered like a fabrication drawing.
// Grid layout regroups them near the origin so they can be inspected.
function applyLayout() {
  if (!modelGroup) return;
  const meshes = solidMeshes.map((s) => s.meshes[0]);
  if (!gridLayout) {
    for (const m of meshes) m.position.set(0, 0, 0);
    return;
  }
  const boxes = meshes.map((m) => {
    m.position.set(0, 0, 0);
    m.updateMatrixWorld(true);
    return new THREE.Box3().setFromObject(m);
  });
  const sizes = boxes.map((b) => b.getSize(new THREE.Vector3()));
  const order = meshes.map((_, i) => i).sort((a, b2) => sizes[b2].y - sizes[a].y);
  const totalArea = sizes.reduce((t, s) => t + (s.x + 1) * (s.y + 1), 0);
  const maxRowW = Math.sqrt(totalArea) * 1.5;
  const gap = Math.sqrt(totalArea) * 0.04;
  let x = 0, y = 0, rowH = 0;
  for (const i of order) {
    const s = sizes[i], b = boxes[i];
    if (x > 0 && x + s.x > maxRowW) {
      x = 0;
      y -= rowH + gap;
      rowH = 0;
    }
    meshes[i].position.set(x - b.min.x, y - s.y - b.min.y, -b.min.z);
    x += s.x + gap;
    rowH = Math.max(rowH, s.y);
  }
}

function applyWireframe() {
  for (const s of solidMeshes) {
    for (const m of s.meshes) m.material.wireframe = wireframe;
  }
}

function renderSolidList() {
  const list = document.getElementById('solid-list');
  list.innerHTML = '';
  solidMeshes.forEach((s, i) => {
    const item = document.createElement('label');
    item.className = 'solid-item';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = s.visible;
    cb.addEventListener('change', () => {
      s.visible = cb.checked;
      for (const m of s.meshes) m.visible = cb.checked;
      item.classList.toggle('hidden-solid', !cb.checked);
    });
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = '#' + s.color.toString(16).padStart(6, '0');
    const txt = document.createElement('span');
    txt.textContent = /^solid_\d+$/.test(s.name)
      ? `Sólido ${i + 1}`
      : s.name.replace(/_/g, ' ');
    txt.title = 'Clic para centrar';
    txt.style.cursor = 'zoom-in';
    txt.addEventListener('click', (ev) => {
      ev.preventDefault();
      fitView(s.meshes[0]);
    });
    item.appendChild(cb);
    item.appendChild(sw);
    item.appendChild(txt);
    list.appendChild(item);
  });
}

async function loadModel(key) {
  currentModel = key;
  // Assembled models keep their real positions; loose parts get the grid.
  gridLayout = !MODELS[key].assembled;
  const layoutBtn = document.getElementById('btn-layout');
  layoutBtn.classList.toggle('toggled', gridLayout);
  layoutBtn.textContent = gridLayout ? 'Cuadrícula (O)' : 'Original (O)';
  document.querySelectorAll('.model-tab').forEach((t) =>
    t.classList.toggle('active', t.dataset.key === key));
  loadingEl.style.display = 'flex';
  clearModel();

  const loader = new OBJLoader();
  let obj;
  try {
    obj = await loader.loadAsync(MODELS[key].file);
  } catch (e) {
    loadingEl.textContent = 'Error cargando ' + MODELS[key].file;
    return;
  }

  modelGroup = new THREE.Group();
  const acis = SOLID_ACI[key] || [];
  const allBylayer = acis.every((c) => c === 256);
  let idx = 0;
  let totalTris = 0;

  for (const child of [...obj.children]) {
    if (!child.isMesh) continue;
    const aci = acis[idx] !== undefined ? acis[idx] : 256;
    const named = colorForName(child.name || '');
    const color = named !== null
      ? named
      : (allBylayer
        ? FALLBACK_PALETTE[idx % FALLBACK_PALETTE.length]
        : (ACI_COLORS[aci] || 0x9aa5b1));
    const mat = new THREE.MeshStandardMaterial({
      color,
      metalness: 0.25,
      roughness: 0.45,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(smoothGeometry(child.geometry), mat);
    modelGroup.add(mesh);
    totalTris += (child.geometry.index
      ? child.geometry.index.count
      : child.geometry.attributes.position.count) / 3;
    solidMeshes.push({ name: child.name || `solid_${idx}`, meshes: [mesh], color, visible: true });
    idx++;
  }

  scene.add(modelGroup);
  applyWireframe();
  applyLayout();
  modelGroup.updateMatrixWorld(true);

  const box = new THREE.Box3().setFromObject(modelGroup);
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const size = box.getSize(new THREE.Vector3());
  buildHelpers(sphere.radius, sphere.center);
  fitView();
  renderSolidList();

  hudInfo.textContent =
    `${MODELS[key].label} — ${solidMeshes.length} sólidos, ` +
    `${Math.round(totalTris).toLocaleString('es')} triángulos, ` +
    `${size.x.toFixed(0)} × ${size.y.toFixed(0)} × ${size.z.toFixed(0)} mm`;
  loadingEl.style.display = 'none';
}

// ---- UI wiring ----
const tabsEl = document.getElementById('model-tabs');
for (const [key2, m] of Object.entries(MODELS)) {
  const b = document.createElement('button');
  b.className = 'model-tab';
  b.dataset.key = key2;
  b.textContent = m.label;
  b.addEventListener('click', () => loadModel(key2));
  tabsEl.appendChild(b);
}

document.getElementById('btn-fit').addEventListener('click', () => fitView());
document.getElementById('btn-layout').addEventListener('click', (e) => {
  gridLayout = !gridLayout;
  e.currentTarget.classList.toggle('toggled', gridLayout);
  e.currentTarget.textContent = gridLayout ? 'Cuadrícula (O)' : 'Original (O)';
  applyLayout();
  if (modelGroup) modelGroup.updateMatrixWorld(true);
  fitView();
});
document.getElementById('btn-wire').addEventListener('click', (e) => {
  wireframe = !wireframe;
  e.currentTarget.classList.toggle('toggled', wireframe);
  applyWireframe();
});
document.getElementById('btn-grid').addEventListener('click', (e) => {
  e.currentTarget.classList.toggle('toggled');
  if (gridHelper) gridHelper.visible = e.currentTarget.classList.contains('toggled');
});
document.getElementById('btn-axes').addEventListener('click', (e) => {
  e.currentTarget.classList.toggle('toggled');
  if (axesHelper) axesHelper.visible = e.currentTarget.classList.contains('toggled');
});

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  const k = e.key.toLowerCase();
  if (k === 'f') fitView();
  if (k === 'o') document.getElementById('btn-layout').click();
  if (k === 'w') document.getElementById('btn-wire').click();
  if (k === 'g') document.getElementById('btn-grid').click();
  if (k === 'a') document.getElementById('btn-axes').click();
});

// ---- Axis orientation HUD ----
const axisCanvas = document.getElementById('axis-hud');
const axisCtx = axisCanvas.getContext('2d');
function drawAxisHud() {
  const w = axisCanvas.width, h = axisCanvas.height;
  axisCtx.clearRect(0, 0, w, h);
  const cx = w / 2, cy = h / 2, len = w * 0.32;
  const q = camera.quaternion.clone().invert();
  const axes = [
    { v: new THREE.Vector3(1, 0, 0), color: '#e05555', label: 'X' },
    { v: new THREE.Vector3(0, 1, 0), color: '#55c05a', label: 'Y' },
    { v: new THREE.Vector3(0, 0, 1), color: '#4da3ff', label: 'Z' },
  ];
  axes.sort((a, b) => a.v.clone().applyQuaternion(q).z - b.v.clone().applyQuaternion(q).z);
  axisCtx.font = 'bold 20px sans-serif';
  axisCtx.textAlign = 'center';
  axisCtx.textBaseline = 'middle';
  for (const a of axes) {
    const p = a.v.clone().applyQuaternion(q);
    const x = cx + p.x * len, y = cy - p.y * len;
    axisCtx.strokeStyle = a.color;
    axisCtx.lineWidth = 4;
    axisCtx.beginPath();
    axisCtx.moveTo(cx, cy);
    axisCtx.lineTo(x, y);
    axisCtx.stroke();
    axisCtx.fillStyle = a.color;
    axisCtx.fillText(a.label, cx + p.x * (len + 16), cy - p.y * (len + 16));
  }
}

function onResize() {
  const w = container.clientWidth, h = container.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', onResize);
onResize();

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
  drawAxisHud();
}
animate();

// Drag & drop de archivos OBJ/STL (p.ej. exportados directo desde AutoCAD).
function showDropped(objectOrGeometry, label) {
  document.querySelectorAll('.model-tab').forEach((t) => t.classList.remove('active'));
  clearModel();
  modelGroup = new THREE.Group();
  let meshes = [];
  if (objectOrGeometry.isBufferGeometry) {
    const mat = new THREE.MeshStandardMaterial({
      color: 0x9aa5b1, metalness: 0.35, roughness: 0.55, side: THREE.DoubleSide,
    });
    meshes = [new THREE.Mesh(smoothGeometry(objectOrGeometry), mat)];
  } else {
    let idx = 0;
    objectOrGeometry.traverse((c) => {
      if (!c.isMesh) return;
      const mat = new THREE.MeshStandardMaterial({
        color: FALLBACK_PALETTE[idx % FALLBACK_PALETTE.length],
        metalness: 0.35, roughness: 0.55, side: THREE.DoubleSide,
      });
      meshes.push(new THREE.Mesh(smoothGeometry(c.geometry), mat));
      idx++;
    });
  }
  meshes.forEach((m, i) => {
    modelGroup.add(m);
    solidMeshes.push({ name: `${label}_${i}`, meshes: [m], color: m.material.color.getHex(), visible: true });
  });
  scene.add(modelGroup);
  applyWireframe();
  applyLayout();
  modelGroup.updateMatrixWorld(true);
  const sphere = new THREE.Box3().setFromObject(modelGroup).getBoundingSphere(new THREE.Sphere());
  buildHelpers(sphere.radius, sphere.center);
  fitView();
  renderSolidList();
  hudInfo.textContent = `${label} — ${meshes.length} piezas (archivo local)`;
  loadingEl.style.display = 'none';
}

const viewport = document.getElementById('viewport');
viewport.addEventListener('dragover', (e) => e.preventDefault());
viewport.addEventListener('drop', async (e) => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (!file) return;
  const ext = file.name.split('.').pop().toLowerCase();
  if (ext === 'stl') {
    const geo = new STLLoader().parse(await file.arrayBuffer());
    showDropped(geo, file.name);
  } else if (ext === 'obj') {
    const obj = new OBJLoader().parse(await file.text());
    showDropped(obj, file.name);
  } else {
    hudInfo.textContent = 'Formato no soportado (arrastra .stl o .obj)';
  }
});

loadModel('barrera_armada');
