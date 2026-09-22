"""
Genera un visualizador 3D interactivo en HTML a partir de las tablas
JSON exportadas por modelo_pasillos (coordenadas_nodos.json y elementos.json).

Usa Three.js (CDN). Produce resultados/modelo_3d.html autocontenido con los
datos embebidos. Se abre directamente en el navegador (doble clic).
"""

import os
import json

BASE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(BASE, "resultados")
OUT_HTML = os.path.join(RES, "modelo_3d.html")

COLS = {"viga_longitudinal": "#2f7fe0", "viga_transversal": "#e08b2f",
        "columna": "#37b34a", "viga_long_voladizo_p2": "#00cccc"}
GMESH = {"viga_longitudinal": (0.6, 0.8), "viga_transversal": (0.6, 0.8),
         "columna": (0.7, 0.7), "viga_long_voladizo_p2": (0.3, 0.45)}


def leer_datos():
    coords_raw = json.load(open(os.path.join(RES, "coordenadas_nodos.json"),
                                encoding="utf-8"))
    elems = json.load(open(os.path.join(RES, "elementos.json"),
                           encoding="utf-8"))
    coords = {int(k): v for k, v in coords_raw.items()}
    muros = json.load(open(os.path.join(RES, "muros.json"),
                           encoding="utf-8"))
    losas = json.load(open(os.path.join(RES, "losas.json"),
                           encoding="utf-8"))
    return coords, elems, muros, losas


def build_js(coords, elems, muros, losas):
    segs = []
    for e in elems:
        p1 = coords[e["nodo_i"]]
        p2 = coords[e["nodo_j"]]
        segs.append({"tipo": e["tipo"], "plano": e["plano"],
                     "a": p1, "b": p2})
    paneles = []
    for m in muros:
        pts = [coords[n] for n in m["nodos"]]
        paneles.append({"plano": m["plano"], "t": m.get("t", 0.2),
                        "p": pts})
    losas_j = []
    for l in losas:
        pts = [coords[n] for n in l["nodos"]]
        losas_j.append({"nivel": l["nivel"], "t": l.get("t", 0.15),
                        "detalle": l.get("detalle", "losas"), "p": pts})
    data = json.dumps(segs)
    data_m = json.dumps(paneles)
    data_l = json.dumps(losas_j)
    return (f"const DATOS = {data};\n"
            f"const MUROS = {data_m};\n"
            f"const LOSAS = {data_l};")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Modelo 3D - Dos Pasillos (4 pisos)</title>
<style>
  html, body { margin:0; height:100%; overflow:hidden; font-family:Segoe UI,Arial,sans-serif; }
  #c { display:block; width:100%; height:100%; background:#0f1419; }
  #panel { position:fixed; top:12px; left:12px; background:rgba(20,25,32,.88);
    color:#e8eef6; padding:12px 14px; border-radius:8px; font-size:13px;
    box-shadow:0 2px 12px rgba(0,0,0,.5); max-width:240px; z-index:10; max-height:92vh; overflow:auto; }
  #panel h1 { font-size:14px; margin:0 0 8px; }
  #panel h2 { font-size:11px; margin:10px 0 4px; color:#7fb0e0; letter-spacing:.4px; }
  #panel label { display:flex; align-items:center; gap:8px; margin:4px 0; cursor:pointer; }
  #panel input { cursor:pointer; }
  .swatch { width:12px; height:12px; border-radius:2px; display:inline-block; }
  .btn { display:inline-block; margin:2px 2px 0 0; padding:4px 8px; border-radius:4px;
    border:1px solid #3a4a5a; background:#1a2330; color:#dbe7f5; cursor:pointer;
    font-size:12px; user-select:none; }
  .btn:hover { background:#263449; }
  .btn.on { background:#2f7fe0; border-color:#2f7fe0; color:#fff; }
  #info { position:fixed; bottom:12px; left:12px; color:#9fb0c2; font-size:11px;
    background:rgba(20,25,32,.7); padding:6px 10px; border-radius:6px; z-index:10; }
  #inspeccion { position:fixed; bottom:12px; right:12px; color:#fff; font:12px/1.5 monospace;
    background:rgba(15,30,50,.9); padding:10px 14px; border-radius:8px; z-index:15;
    border:1px solid #2f7fe0; min-width:220px; display:none; white-space:pre-line; }
  #inspeccion b { color:#7fd0ff; }
  #errcaja { display:none; position:fixed; top:12px; right:12px; max-width:420px;
    color:#ffd6d6; background:rgba(180,30,30,.92); padding:10px 14px; border-radius:8px;
    font:12px/1.4 monospace; white-space:pre-wrap; z-index:20; }
</style>
</head>
<body>
<div id="c"></div>
<div id="errcaja"></div>
<div id="panel">
  <h1>Modelo: Dos Pasillos - 4 pisos</h1>
  <h2>Mostrar barras</h2>
  <label><input type="checkbox" data-tipo="columna" checked>
    <span class="swatch" style="background:#37b34a"></span> Columnas (70×70)</label>
  <label><input type="checkbox" data-tipo="viga_longitudinal" checked>
    <span class="swatch" style="background:#2f7fe0"></span> Vigas longitudinales (60×80)</label>
  <label><input type="checkbox" data-tipo="viga_transversal" checked>
    <span class="swatch" style="background:#e08b2f"></span> Vigas transversales (60×80)</label>
  <label><input type="checkbox" data-tipo="viga_long_voladizo_p2" checked>
    <span class="swatch" style="background:#00cccc"></span> Viga ext. voladizo p2 (30×45)</label>
  <h2>Mostrar muros</h2>
  <label><input type="checkbox" data-muro checked>
    <span class="swatch" style="background:#b06ae0"></span> Muros estructurales (t=20/25 cm)</label>
  <h2>Mostrar losas</h2>
  <label><input type="checkbox" data-losa checked>
    <span class="swatch" style="background:#4fcec0"></span> Losas de piso (diafragmas)</label>
  <label><input type="checkbox" data-losa-muro checked>
    <span class="swatch" style="background:#e7cf8a"></span> Zona de muro (losa pendiente)</label>
  <h2>Ver por piso</h2>
  <div id="pisos">
    <span class="btn on" data-piso="0">Todos</span>
    <span class="btn" data-piso="1">Piso 1</span>
    <span class="btn" data-piso="2">Piso 2</span>
    <span class="btn" data-piso="3">Piso 3</span>
    <span class="btn" data-piso="4">Piso 4</span>
  </div>
  <h2>Rotar / Vistas</h2>
  <div id="vistas">
    <span class="btn on" data-vista="iso">3D</span>
    <span class="btn" data-vista="planta">Planta</span>
    <span class="btn" data-vista="alzado">Alz. long</span>
    <span class="btn" data-vista="lateral">Lateral</span>
  </div>
  <div>
    <span class="btn" id="btn_auto">Auto girar</span>
    <span class="btn" id="btn_reset">Reset vista</span>
  </div>
  <h2>Inspeccionar (clic en una barra)</h2>
</div>
<div id="info">Arrastrar: rotar · Rueda: zoom · Derecho/Shift: desplazar · <b>Clic en barra: ver coordenadas</b></div>
<div id="inspeccion"></div>

<script>
// Muestra en pantalla cualquier error de carga/script en vez de pantalla negra
window.addEventListener('error', function(e){
  var b=document.getElementById('errcaja');
  b.style.display='block';
  b.textContent='Error: '+(e.message||e.type||'desconocido')+' en '+(e.filename||'');
  if(e.lineno) b.textContent+=' (linea '+e.lineno+')';
  return false;
});
window.addEventListener('unhandledrejection', function(e){
  var b=document.getElementById('errcaja');
  b.style.display='block';
  b.textContent='Error de carga: '+(e.reason && e.reason.message ? e.reason.message : e.reason);
});
</script>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>
<script type="module">
__DATA__

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const TIPO_COLOR = { viga_longitudinal:'#2f7fe0', viga_transversal:'#e08b2f', columna:'#37b34a', viga_long_voladizo_p2:'#00cccc' };
const TIPO_SIZE  = { viga_longitudinal:[0.6,0.8], viga_transversal:[0.6,0.8], columna:[0.7,0.7], viga_long_voladizo_p2:[0.3,0.45] };
const SISTEMA = { viga_longitudinal:'Viga longitudinal', viga_transversal:'Viga transversal', columna:'Columna', viga_long_voladizo_p2:'Viga ext. voladizo p2' };
const WALL_COLOR = { muro_ppal:'#b06ae0', muro_ext:'#e06ab0' };
const WALL_NAME  = { muro_ppal:'Muro principal', muro_ext:'Muro extremo' };
const LOSA_COLOR = { losas:'#4fcec0', zona_muro:'#e7cf8a' };

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(50, innerWidth/innerHeight, 0.1, 2000);
const renderer = new THREE.WebGLRenderer({ antialias:true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(devicePixelRatio);
document.getElementById('c').appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(60, 80, 40);
scene.add(sun);
const sun2 = new THREE.DirectionalLight(0xffffff, 0.35);
sun2.position.set(-50, 20, -60);
scene.add(sun2);

// Rejilla del suelo
const grid = new THREE.GridHelper(100, 40, 0x3a4a5a, 0x22303d);
grid.position.y = -0.01;
scene.add(grid);

// Ejes X (rojo), Y (verde), Z (azul)
const ejesG = new THREE.Group();
(()=>{
  const mk=(c,rotz,rotx)=>{
    const m=new THREE.Mesh(new THREE.CylinderGeometry(0.15,0.15,6,8),
        new THREE.MeshBasicMaterial({color:c}));
    if(rotz) m.rotation.z=rotz; if(rotx) m.rotation.x=rotx; return m;
  };
  ejesG.add(mk(0xff4444,Math.PI/2,0));      // X
  ejesG.add(mk(0x44ff44,0,Math.PI/2));      // Y
  ejesG.add(mk(0x4488ff,0,0));              // Z
  ejesG.position.set(0,0,0);
})();
scene.add(ejesG);

// Etiquetas de texto (sprites) para coordenadas clave
function etiqueta(texto, pos, color){
  const cv=document.createElement('canvas'); cv.width=256; cv.height=64;
  const ctx=cv.getContext('2d'); ctx.font='bold 40px Arial'; ctx.fillStyle=color||'#cfe3ff';
  ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(texto,128,32);
  const tex=new THREE.CanvasTexture(cv);
  const mat=new THREE.SpriteMaterial({map:tex, depthTest:false, transparent:true});
  const sp=new THREE.Sprite(mat); sp.scale.set(3,0.75,1); sp.position.set(pos[0],pos[1],pos[2]);
  return sp;
}
// Nombres de lineas transversales (Y) a lo largo del eje X
const LINEAS_Y = [
  ['Y=+8.90 (P1)', 0,  8.90, 0], ['Y=0 (centro)', 0,  0,   0],
  ['Y=-7.25 (P2)', 0, -7.25, 0], ['Y=-11.37',     0, -11.37, 0]
];
// Etiquetas de X en el suelo
let X_MIN=0, X_MAX=0;
(()=>{ let xs=[],ys=[],zs=[];
  DATOS.forEach(d=>[d.a,d.b].forEach(p=>{xs.push(p[0]);ys.push(p[1]);zs.push(p[2]);}));
  MUROS.forEach(wn=>wn.p.forEach(p=>{xs.push(p[0]);ys.push(p[1]);zs.push(p[2]);}));
  LOSAS.forEach(lw=>lw.p.forEach(p=>{xs.push(p[0]);ys.push(p[1]);zs.push(p[2]);}));
  X_MIN=Math.min(...xs); X_MAX=Math.max(...xs);
})();
const X_LABEL = [0,5,7.51,10,15,20,25,30,35,37.55,40,-10].filter(x=>x>=X_MIN-0.01&&x<=X_MAX+0.01);
X_LABEL.forEach(x=>scene.add(etiqueta('X='+x, [x,-11.9,0.2], '#ffd0a0')));
LINEAS_Y.forEach(ly=>scene.add(etiqueta(ly[0],[ly[1]-1.0,ly[2],0.2],'#a0ffc0')));
scene.add(etiqueta('X (long)',[(X_MIN+X_MAX)/2,11,-0.2],'#ffffff'));
scene.add(etiqueta('Y (trans)',[-13,-3.5,-0.2],'#ffffff'));

// --- Construccion de barras (prismas) + raycast ---
const roots = {};   // 3 grupos, uno por tipo
Object.keys(TIPO_COLOR).forEach(t=>{ roots[t]=new THREE.Group(); scene.add(roots[t]); });

const DIR = new THREE.Vector3(), axis = new THREE.Vector3(0,0,1);
const quat = new THREE.Quaternion();
const meshes = [];      // paralelo a DATOS

DATOS.forEach((d,idx)=>{
  const [bx,bz] = TIPO_SIZE[d.tipo];
  const geom = new THREE.BoxGeometry(bx, bx, bz);
  const mat = new THREE.MeshPhongMaterial({ color:new THREE.Color(TIPO_COLOR[d.tipo]) });
  const mesh = new THREE.Mesh(geom, mat);

  const x1=d.a[0],y1=d.a[1],z1=d.a[2];
  const x2=d.b[0],y2=d.b[1],z2=d.b[2];
  DIR.set(x2-x1, y2-y1, z2-z1);
  const len = DIR.length();
  mesh.scale.set(1, 1, len/bz);
  quat.setFromUnitVectors(axis, DIR.clone().normalize());
  mesh.quaternion.copy(quat);
  mesh.position.set((x1+x2)/2,(y1+y2)/2,(z1+z2)/2);
  mesh.userData.idx = idx;
  roots[d.tipo].add(mesh);
  meshes.push(mesh);
});
scene.add(ejesG);

// --- Construccion de muros (paneles verticales) ---
const rootMuro = new THREE.Group();
scene.add(rootMuro);
const wallMeshes = [];
const vAxis = new THREE.Vector3(0,0,1);
MUROS.forEach((wn, widx)=>{
  const p0=wn.p[0], p1=wn.p[1], p2=wn.p[2];
  // dims: largo en planta (p0->p1), alto de banda (p1->p2), espesor wn.t
  const largo = Math.hypot(p1[0]-p0[0], p1[1]-p0[1]);
  const alto  = Math.hypot(p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]);
  const cx=(p0[0]+p1[0]+p2[0]+wn.p[3][0])/4;
  const cy=(p0[1]+p1[1]+p2[1]+wn.p[3][1])/4;
  const cz=(p0[2]+p1[2]+p2[2]+wn.p[3][2])/4;
  const hdir = new THREE.Vector3(p1[0]-p0[0], p1[1]-p0[1], 0).normalize();
  const geom = new THREE.BoxGeometry(largo, wn.t, alto);
  const mat = new THREE.MeshPhongMaterial({
    color:new THREE.Color(WALL_COLOR[wn.plano]),
    transparent:true, opacity:0.45,
    side:THREE.DoubleSide,
    depthWrite:false
  });
  const mesh = new THREE.Mesh(geom, mat);
  // orientar: largo en el plano (rotacion en Z), luego directo en Z para alto
  const angZ = Math.atan2(hdir.y, hdir.x);
  mesh.rotation.z = angZ;
  mesh.position.set(cx, cy, cz);
  const wire = new THREE.LineSegments(
    new THREE.EdgesGeometry(geom),
    new THREE.LineBasicMaterial({ color:new THREE.Color(WALL_COLOR[wn.plano]), transparent:true, opacity:0.9 })
  );
  wire.rotation.z = angZ; wire.position.set(cx, cy, cz);
  mesh.userData.widx = widx;
  mesh.userData.plano = wn.plano; mesh.userData.t = wn.t;
  mesh.userData.p = wn.p;
  rootMuro.add(mesh);
  rootMuro.add(wire);
  wallMeshes.push(mesh);
});

// --- Construccion de losas (planos HORIZONTALES de piso) ---
const rootLosa = new THREE.Group();
scene.add(rootLosa);
const losaMeshes = [];
LOSAS.forEach((l, lidx)=>{
  const p0=l.p[0], p1=l.p[1], p2=l.p[2], p3=l.p[3];
  // Los nodos p0->p1 corren a lo largo de X y p0->p3 a lo largo de Y (mismo Z).
  // Dimensiones en planta (plano X-Y):
  const largoX = Math.hypot(p1[0]-p0[0], p1[1]-p0[1]);   // lado a lo largo de X
  const largoY = Math.hypot(p3[0]-p0[0], p3[1]-p0[1]);   // lado a lo largo de Y
  const cx=(p0[0]+p1[0]+p2[0]+p3[0])/4;
  const cy=(p0[1]+p1[1]+p2[1]+p3[1])/4;
  const cz=(p0[2]+p1[2]+p2[2]+p3[2])/4;
  const espesor = l.t || 0.15;
  // Box geometry: (X, Y, Z). El espesor debe quedar a lo largo de Z (vertical),
  // por lo que va como 3er argumento: la losa es horizontal en el plano X-Y.
  const geom = new THREE.BoxGeometry(largoX, largoY, espesor);
  const mat = new THREE.MeshPhongMaterial({
    color:new THREE.Color(LOSA_COLOR[l.detalle] || LOSA_COLOR.losas),
    transparent:true, opacity:0.4, side:THREE.DoubleSide, depthWrite:false
  });
  const mesh = new THREE.Mesh(geom, mat);
  mesh.position.set(cx, cy, cz);
  mesh.userData.lidx = lidx;
  mesh.userData.nivel = l.nivel;
  mesh.userData.detalle = l.detalle;
  mesh.userData.p = l.p;
  rootLosa.add(mesh);
  losaMeshes.push(mesh);
});

// --- Controles de visibilidad por tipo ---
document.querySelectorAll('input[data-tipo]').forEach(cb=>{
  cb.addEventListener('change', ()=> { roots[cb.dataset.tipo].visible = cb.checked; aplicarPiso(); });
});
document.querySelectorAll('input[data-muro]').forEach(cb=>{
  cb.addEventListener('change', ()=> { rootMuro.visible = cb.checked; });
});
let losaVisible=()=>true, losaMuroVisible=()=>true;
function aplicarLosaVis(){
  losaMeshes.forEach(m=>{
    const esMuro = m.userData.detalle==='zona_muro';
    m.visible = (esMuro? losaMuroVisible():losaVisible()) && (filtroPiso===0 || pisoDeLosa(m));
  });
}
document.querySelectorAll('input[data-losa]').forEach(cb=>{
  cb.addEventListener('change', ()=> { losaVisible=()=>cb.checked; aplicarLosaVis(); });
});
document.querySelectorAll('input[data-losa-muro]').forEach(cb=>{
  cb.addEventListener('change', ()=> { losaMuroVisible=()=>cb.checked; aplicarLosaVis(); });
});

// --- Orbit Controls ---
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// Encuadre automatico + guardado de vista inicial
let CX0, CY0, CZ0, RAD;
(()=>{
  let xs=[],ys=[],zs=[];
  DATOS.forEach(d=>{ [d.a,d.b].forEach(p=>{xs.push(p[0]);ys.push(p[1]);zs.push(p[2]);}); });
  MUROS.forEach(wn=>wn.p.forEach(p=>{xs.push(p[0]);ys.push(p[1]);zs.push(p[2]);}));
  LOSAS.forEach(lw=>lw.p.forEach(p=>{xs.push(p[0]);ys.push(p[1]);zs.push(p[2]);}));
  CX0=(Math.min(...xs)+Math.max(...xs))/2; CY0=(Math.min(...ys)+Math.max(...ys))/2;
  CZ0=(Math.min(...zs)+Math.max(...zs))/2;
  RAD=Math.max(Math.max(...xs)-Math.min(...xs), Math.max(...ys)-Math.min(...ys),
               Math.max(...zs)-Math.min(...zs))/2 + 10;
  controls.target.set(CX0,CY0,CZ0);
  camera.position.set(CX0, CY0-RAD*1.1, CZ0+RAD);
  camera.lookAt(controls.target);
})();

function setVista(offx,offy,offz){
  camera.position.set(controls.target.x+offx, controls.target.y+offy, controls.target.z+offz);
  camera.lookAt(controls.target);
}
function vistaActual(){ return controls.target; }

// Botones de vista
let autoGirar=false;
const vistas={
  iso:()=>setVista( RAD*1.0, -RAD*1.05, RAD*1.1 ),
  planta:()=>setVista( 0, -0.2, RAD*2.2 ),
  alzado:()=>setVista( 0, RAD*2.4, 0 ),      // Y: plano X-Z
  lateral:()=>setVista( -RAD*2.4, 0, 0 )      // X: plano Y-Z
};
document.querySelectorAll('[data-vista]').forEach(b=>{
  b.addEventListener('click',()=>{
    document.querySelectorAll('[data-vista]').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    vistas[b.dataset.vista]();
  });
});
document.getElementById('btn_reset').addEventListener('click',()=>{
  controls.target.set(CX0,CY0,CZ0); vistas.iso();
  document.querySelectorAll('[data-vista]').forEach(x=>x.classList.toggle('on',x.dataset.vista==='iso'));
});
document.getElementById('btn_auto').addEventListener('click',e=>{
  autoGirar=!autoGirar; e.target.classList.toggle('on',autoGirar);
});

// --- Filtrar por piso (segun Z del baricentro) ---
function pisoDeBarra(d){
  const zc=((d.a[2]+d.b[2])/2);
  if(zc<=12.0001) return Math.ceil((zc+0.0001)/4);   // 1..3
  return 4;
}
function pisoDeLosa(m){
  const zc=m.position.z;
  if(Math.abs(zc)<0.001) return 5;      // techo sotano (no un piso elevado)
  if(zc<=12.0001) return Math.ceil((zc+0.0001)/4);
  return 4;
}
let filtroPiso=0;   // 0 = todos
function aplicarPiso(){
  meshes.forEach((m,idx)=>{
    const d=DATOS[idx];
    const visibleTipo = roots[d.tipo].visible;
    const visiblePiso = filtroPiso===0 || pisoDeBarra(d)===filtroPiso;
    m.visible = visibleTipo && visiblePiso;
  });
  aplicarLosaVis();
}
document.querySelectorAll('[data-piso]').forEach(b=>{
  b.addEventListener('click',()=>{
    document.querySelectorAll('[data-piso]').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    filtroPiso=+b.dataset.piso;
    aplicarPiso();
  });
});

// --- Inspeccionar con clic (raycast) ---
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const insp = document.getElementById('inspeccion');

function fmt(n){ return (Math.round(n*100)/100).toFixed(2); }
function describir(d){
  const t=d.tipo, plano=d.plano;
  const a=d.a, b=d.b;
  const iz=a[2], fz=b[2];
  const esCol = t==='columna';
  const esLong = t==='viga_longitudinal';
  const esTrans = t==='viga_transversal';
  let coords='';
  if(esCol){
    coords='X='+fmt(a[0])+', Y='+fmt(a[1])+'\\n  Z: '+fmt(Math.min(iz,fz))+' → '+fmt(Math.max(iz,fz))+' m';
  } else {
    coords='X: '+fmt(a[0])+' → '+fmt(b[0])+' m\\nY: '+fmt(a[1])+' → '+fmt(b[1])+' m\\nZ= '+fmt(a[2])+' m';
  }
  return SISTEMA[t]+' (plano: '+plano+')\\n'+coords;
}
renderer.domElement.addEventListener('click', ev=>{
  const rect=renderer.domElement.getBoundingClientRect();
  mouse.x=((ev.clientX-rect.left)/rect.width)*2-1;
  mouse.y=-((ev.clientY-rect.top)/rect.height)*2+1;
  raycaster.setFromCamera(mouse,camera);
  const hits=raycaster.intersectObjects(meshes.concat(wallMeshes).concat(losaMeshes));
  if(hits.length){
    const o=hits[0].object;
    if(o.userData.lidx!==undefined){
      const l=LOSAS[o.userData.lidx];
      const c=l.p[0];
      insp.style.display='block';
      insp.innerHTML='<b>Losa de piso</b> (nivel Z='+fmt(l.nivel)+' m, t='+fmt(l.t)+' m)<br>'
        +(l.detalle==='zona_muro'?'<b>Zona de muro</b> (losa distinta pendiente)<br>':'')
        +'X= '+fmt(c[0])+' \\u2192 '+fmt(l.p[2][0])+' m<br>Y= '+fmt(c[1])+' \\u2192 '+fmt(l.p[2][1])+' m';
    } else if(o.userData.widx!==undefined){
      const wn=MUROS[o.userData.widx];
      const c=wn.p[0];
      insp.style.display='block';
      insp.innerHTML='<b>'+WALL_NAME[wn.plano]+'</b> (plano '+wn.plano+'), t='+fmt(wn.t)+' m<br>'+
        'X= '+fmt(c[0])+'\\u2192 '+fmt(wn.p[1][0])+' m, Y= '+fmt(c[1])+' m<br>Z= '+fmt(wn.p[1][2])+' \\u2192 '+fmt(wn.p[2][2])+' m';
    } else {
      const d=DATOS[o.userData.idx];
      insp.style.display='block';
      insp.innerHTML='<b>'+SISTEMA[d.tipo]+'</b> (plano '+d.plano+')<br>'+describir(d).replace('\\n','<br>');
    }
  } else {
    insp.style.display='none';
  }
});

// Cambiar la etiqueta de cursor para indicar clic
renderer.domElement.style.cursor='pointer';

window.addEventListener('resize', ()=>{
  camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight);
});

function animate(){
  requestAnimationFrame(animate);
  if(autoGirar) controls.autoRotate=true; else controls.autoRotate=false;
  controls.update();
  renderer.render(scene,camera);
}
animate();
</script>
</body>
</html>
"""


def generar():
    coords, elems, muros, losas = leer_datos()
    data_js = build_js(coords, elems, muros, losas)
    html = HTML_TEMPLATE.replace("__DATA__", data_js)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    n_col = sum(1 for e in elems if e["tipo"] == "columna")
    n_vl = sum(1 for e in elems if e["tipo"] == "viga_longitudinal")
    n_vt = sum(1 for e in elems if e["tipo"] == "viga_transversal")
    n_muro = len(muros)
    n_losa = len(losas)
    n_losa_muro = sum(1 for l in losas if l.get("detalle") == "zona_muro")
    print(f"Visualizador generado: {OUT_HTML}")
    print(f"  Columnas:        {n_col}")
    print(f"  V. longitudinal: {n_vl}")
    print(f"  V. transversal:  {n_vt}")
    print(f"  Paneles de muro: {n_muro}")
    print(f"  Paneles de losa: {n_losa} ({n_losa_muro} en zona de muro)")
    print(f"  Total barras:    {len(elems)}")


if __name__ == "__main__":
    generar()
