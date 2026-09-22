# ============================================================
# STRUCTURAL MODEL - Edificio de Ingenieria UANDES
# ============================================================
# Construye el modelo estructural 3D de gravedad en OpenSeesPy a
# partir del JSON geometrico (structural_geometry.json):
#   - Nodos
#   - Columnas (70x70)
#   - Malla de vigas: vigas de Santiago + vigas de reparto de losa
#   - Muros equivalentes (elementos verticales, seccion t x L)
#   - Apoyos empotrados en base
#   - Diafragmas rigidos por piso
# Unidades: kN y metros.
# ============================================================
import os, json
from math import hypot

import openseespy.opensees as ops

from materials import Q_G, CONCRETO_H30
from sections import wall_section_props, COL, BEAM_SECTIONS

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOMETRY_PATH = os.path.join(PROJECT_DIR, "structural_geometry.json")

PISO_LEVELS = ["CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]
DEFAULT_REPART = "V30/80"
TAG_BASE = 800000             # nodos/elementos generados por encima de esto

# ---------------------------------------------------------------
# Registro de tags numericos generados
# ---------------------------------------------------------------
_counter = [TAG_BASE]


def _next_tag():
    _counter[0] += 1
    return _counter[0]


# ---------------------------------------------------------------
# Carga de geometria
# ---------------------------------------------------------------
def load_geometry():
    with open(GEOMETRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def node_map(geometry):
    return {n["id"]: n for n in geometry["nodes"]}


def nodes_by_level(geometry):
    by = {}
    for n in geometry["nodes"]:
        by.setdefault(n["level"], []).append(n)
    return by


def pos_index(nodes_level):
    idx = {}
    for n in nodes_level:
        if None not in (n["x"], n["y"]):
            idx[(round(n["x"], 4), round(n["y"], 4))] = n["id"]
    return idx


def _beam_section_of_id(beam_id):
    for nm in sorted(BEAM_SECTIONS, key=len, reverse=True):
        if nm in beam_id:
            return nm
    return DEFAULT_REPART


# ---------------------------------------------------------------
# MALLA DE VIGAS POR PISO
# ---------------------------------------------------------------
def subdivide_beam(i_node_id, j_node_id, nodes_level):
    ni = nj = None
    for n in nodes_level:
        if n["id"] == i_node_id:
            ni = n
        if n["id"] == j_node_id:
            nj = n
    if ni is None or nj is None:
        return [(i_node_id, j_node_id)]
    ax, ay = ni["x"], ni["y"]
    bx, by = nj["x"], nj["y"]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return []
    pts = []
    for n in nodes_level:
        if None in (n["x"], n["y"]) or n["id"] in (i_node_id, j_node_id):
            continue
        vx, vy = n["x"] - ax, n["y"] - ay
        if abs(dx * vy - dy * vx) < 1e-6:
            t = (vx * dx + vy * dy) / L2
            if -1e-9 <= t <= 1.0 + 1e-9:
                pts.append((t, n["id"]))
    pts.sort()
    ordered = [i_node_id] + [pid for _, pid in pts] + [j_node_id]
    return list(zip(ordered, ordered[1:]))


def floor_beam_mesh(geometry, level, extra_nodes=None, node_coords=None):
    """Construye la malla de vigas de un piso como UNION DE BORDES DE LOS
    PANELES DE LOSA (cada borde compartido = una viga, sin duplicados).
    La seccion de cada borde es la de la viga de Santiago que lo cubre
    (misma linea, borde dentro del tramo) o `DEFAULT_REPART` si no hay.
    Se crean los nodos de esquina faltantes (registrados en `extra_nodes`).
    Retorna (mesh, extra_nodes, node_coords)."""
    nm = node_map(geometry)
    nbl = nodes_by_level(geometry)
    nodes_level = nbl.get(level, [])
    pos_idx = pos_index(nodes_level)
    z = geometry["levels"][level]
    if node_coords is None:
        node_coords = {n["id"]: (n["x"], n["y"]) for n in nodes_level}
    if extra_nodes is None:
        extra_nodes = []
    created = {}

    def get_or_create(x, y):
        key = (round(x, 4), round(y, 4))
        if key in pos_idx:
            return pos_idx[key]
        if key in created:
            return created[key]
        nid = _next_tag()
        created[key] = nid
        pos_idx[key] = nid
        node_coords[nid] = (x, y)
        extra_nodes.append({"id": nid, "x": x, "y": y, "z": z,
                            "level": level})
        return nid

    # vigas de Santiago del nivel (rangos para asignar seccion)
    santiago = []
    for b in geometry["beams"]:
        if b["level"] != level:
            continue
        n1 = nm[b["node_i"]]; n2 = nm[b["node_j"]]
        if None in (n1["x"], n1["y"], n2["x"], n2["y"]):
            continue
        santiago.append({
            "id": b["id"],
            "x1": min(n1["x"], n2["x"]), "x2": max(n1["x"], n2["x"]),
            "y1": min(n1["y"], n2["y"]), "y2": max(n1["y"], n2["y"]),
            "seccion": _beam_section_of_id(str(b.get("id", ""))),
        })

    def section_for_edge(p, q):
        # horizontal (y constante)
        if abs(p[1] - q[1]) < 1e-9:
            c_y = p[1]; lo = min(p[0], q[0]); hi = max(p[0], q[0])
            for s in santiago:
                if (abs(s["y1"] - c_y) < 0.01 and abs(s["y2"] - c_y) < 0.01
                        and s["x1"] <= lo + 0.01 and s["x2"] >= hi - 0.01):
                    return s["seccion"]
            return DEFAULT_REPART
        # vertical (x constante)
        c_x = p[0]; lo = min(p[1], q[1]); hi = max(p[1], q[1])
        for s in santiago:
            if (abs(s["x1"] - c_x) < 0.01 and abs(s["x2"] - c_x) < 0.01
                    and s["y1"] <= lo + 0.01 and s["y2"] >= hi - 0.01):
                return s["seccion"]
        return DEFAULT_REPART

    # union de bordes unicos de los paneles
    edges = {}
    for s in geometry.get("slabs", []):
        if s["level"] != level:
            continue
        if None in (s["x1"], s["x2"], s["y1"], s["y2"]):
            continue
        x1, x2 = sorted([s["x1"], s["x2"]])
        y1, y2 = sorted([s["y1"], s["y2"]])
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        for i in range(4):
            p, q = corners[i], corners[(i + 1) % 4]
            key = frozenset({(round(p[0], 4), round(p[1], 4)),
                             (round(q[0], 4), round(q[1], 4))})
            if key not in edges:
                edges[key] = section_for_edge(p, q)

    mesh = []
    for key, seccion in edges.items():
        (p, q) = list(key)
        n1 = get_or_create(p[0], p[1])
        n2 = get_or_create(q[0], q[1])
        mesh.append({"iNode": n1, "jNode": n2, "seccion": seccion})
    return mesh, extra_nodes, node_coords


# ---------------------------------------------------------------
# MUROS EQUIVALENTES (elementos verticales por nivel)
# ---------------------------------------------------------------
def build_walls(geometry, node_registry, level_to_z):
    """Para cada muro ACTIVE crea nodos en el centroide del muro en sus
    dos niveles extremos y devuelve un elemento vertical equivalente.
    node_registry: dict (x,y,level) -> node_id (compartido).
    Retorna (lista_walls, lista_nodos_nuevos, escalvos_por_nivel)."""
    walls = []
    new_nodes = []
    slaves = {lv: [] for lv in PISO_LEVELS}

    def ensure(x, y, level):
        key = (round(x, 4), round(y, 4), level)
        if key in node_registry:
            return node_registry[key]
        # buscar nodo existente del nivel cerca
        for n in node_registry_coords(level):
            if None not in (n["x"], n["y"]) and abs(n["x"] - x) < 0.03 \
               and abs(n["y"] - y) < 0.03:
                node_registry[key] = n["id"]
                return n["id"]
        # crear nodo nuevo
        nid = _next_tag()
        z = level_to_z[level]
        node_registry[key] = nid
        new_nodes.append({"id": nid, "x": x, "y": y, "z": z, "level": level})
        return nid

    # registrar nodos existentes por nivel para reutilizar
    existing_by_level = {}
    for n in geometry["nodes"]:
        existing_by_level.setdefault(n["level"], []).append(n)

    def node_registry_coords(level):
        return existing_by_level.get(level, [])

    for w in geometry["walls"]:
        if w["status"] != "ACTIVE":
            continue
        if None in (w["x1"], w["y1"], w["x2"], w["y2"], w["thickness"]):
            continue
        if w["z_bottom"] is None or w["z_top"] is None:
            continue
        L = hypot(w["x2"] - w["x1"], w["y2"] - w["y1"])
        if L < 0.3:
            continue
        cx = (w["x1"] + w["x2"]) / 2.0
        cy = (w["y1"] + w["y2"]) / 2.0
        lv_bottom = z_to_level(level_to_z, w["z_bottom"])
        lv_top = z_to_level(level_to_z, w["z_top"])
        ni = ensure(cx, cy, lv_bottom)
        nj = ensure(cx, cy, lv_top)
        if lv_bottom in slaves:
            slaves[lv_bottom].append(ni)
        if lv_top in slaves:
            slaves[lv_top].append(nj)
        props = wall_section_props(w["thickness"], L)
        walls.append({"tag": _next_tag(), "node_i": ni, "node_j": nj, "props": props,
                      "length": L, "bottom": lv_bottom, "top": lv_top,
                      "grid_x": w.get("grid_x1"), "grid_y": w.get("grid_y1")})
    return walls, new_nodes, slaves


def z_to_level(level_to_z, z):
    best = None
    best_diff = 1e9
    for lv, vz in level_to_z.items():
        if vz is None:
            continue
        d = abs(vz - z)
        if d < best_diff:
            best_diff = d
            best = lv
    return best


# ---------------------------------------------------------------
# ENSAMBLADO (datos)
# ---------------------------------------------------------------
def assemble(geometry):
    nm = node_map(geometry)
    level_to_z = geometry["levels"]

    # columnas
    columns = []
    for c in geometry["columns"]:
        columns.append({"tag": c["node_i"], "iNode": c["node_i"],
                        "jNode": c["node_j"], "seccion": "COL"})

    # vigas (+ nodos generados de reparto de losa)
    beams = []
    gen_nodes = []
    node_coords = {}
    for level in PISO_LEVELS:
        mesh, extra_nodes, node_coords = floor_beam_mesh(
            geometry, level, gen_nodes, node_coords)
        for tb in mesh:
            beams.append({"tag": _next_tag(), "iNode": tb["iNode"],
                          "jNode": tb["jNode"], "seccion": tb["seccion"],
                          "piso": level})

    # muros
    node_registry = {}
    walls, wall_nodes, wall_slaves = build_walls(geometry, node_registry,
                                                 level_to_z)
    gen_nodes.extend(wall_nodes)

    # apoyos: nodos de columna en FOUNDATION
    supports = []
    for c in geometry["columns"]:
        ni = c["node_i"]
        n_ = nm.get(ni)
        if n_ and n_["level"] == "FOUNDATION":
            supports.append({"node": ni, "fixity": (1, 1, 1, 1, 1, 1)})

    # apoyos adicionales: nodos de muro cuyo extremo inferior esta en FOUNDATION
    for w in walls:
        if w["bottom"] == "FOUNDATION":
            supports.append({"node": w["node_i"], "fixity": (1, 1, 1, 1, 1, 1)})

    # deduplicar apoyos por nodo
    seen = set()
    supports_u = []
    for s in supports:
        if s["node"] not in seen:
            seen.add(s["node"])
            supports_u.append(s)
    supports = supports_u

    # diafragmas
    nbl = nodes_by_level(geometry)
    diafragmas = {}
    centroids = {}
    extra_by_level = {lv: [] for lv in PISO_LEVELS}
    for gn in gen_nodes:
        if gn["level"] in extra_by_level:
            extra_by_level[gn["level"]].append(gn)
    for level in PISO_LEVELS:
        nodes_lv = nbl.get(level, []) + extra_by_level[level]
        xs = [n["x"] for n in nodes_lv if None not in (n["x"], n["y"])]
        ys = [n["y"] for n in nodes_lv if None not in (n["x"], n["y"])]
        cx = sum(xs) / len(xs) if xs else 0.0
        cy = sum(ys) / len(ys) if ys else 0.0
        centroids[level] = (cx, cy, level_to_z[level])
        maestro = _next_tag()
        slaves = set()
        for c in geometry["columns"]:
            nj = c["node_j"]
            n_ = nm.get(nj)
            if n_ and n_["level"] == level:
                slaves.add(nj)
        for tb in beams:
            if tb["piso"] == level:
                slaves.add(tb["iNode"])
                slaves.add(tb["jNode"])
        for wn in wall_slaves.get(level, []):
            slaves.add(wn)
        for gn in extra_by_level[level]:
            slaves.add(gn["id"])
        # nodos de columna del piso
        for c in geometry["columns"]:
            ni = c["node_i"]
            n_ = nm.get(ni)
            if n_ and n_["level"] == level:
                slaves.add(ni)
        diafragmas[level] = {"maestro": maestro, "slaves": sorted(slaves)}

    # node_map ampliado con nodos generados
    nm_amp = dict(nm)
    for gn in gen_nodes:
        nm_amp[gn["id"]] = gn

    return {
        "columns": columns,
        "beams": beams,
        "walls": walls,
        "wall_nodes": gen_nodes,
        "supports": supports,
        "diafragmas": diafragmas,
        "centroids": centroids,
        "node_map": nm_amp,
    }


# ---------------------------------------------------------------
# CONSTRUCCION OPENSEES
# ---------------------------------------------------------------
def build_model(structure, geometry):
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)
    E = CONCRETO_H30.E
    Gm = CONCRETO_H30.G
    nm = structure["node_map"]

    # coord lookup (node_map ampliado ya incluye nodos generados)
    coords = {nid: (n["x"], n["y"], n["z"]) for nid, n in structure["node_map"].items()
              if None not in (n["x"], n["y"], n["z"])}

    # nodos realmente activos: extremos de columnas/vigas/muros + apoyos
    active = set()
    for c in structure["columns"]:
        active.add(c["iNode"]); active.add(c["jNode"])
    for b in structure["beams"]:
        active.add(b["iNode"]); active.add(b["jNode"])
    for w in structure["walls"]:
        active.add(w["node_i"]); active.add(w["node_j"])
    for s in structure["supports"]:
        active.add(s["node"])

    for nid in active:
        if nid in coords:
            ops.node(nid, *coords[nid])

    ops.geomTransf("Linear", 1, 1, 0, 0)   # verticales (col/muro)
    ops.geomTransf("Linear", 2, 0, 0, 1)   # vigas

    for s in structure["supports"]:
        ops.fix(s["node"], *s["fixity"])

    for c in structure["columns"]:
        ops.element("elasticBeamColumn", c["tag"], c["iNode"], c["jNode"],
                    COL["A"], E, Gm, COL["J"], COL["Iy"], COL["Iz"], 1)

    for b in structure["beams"]:
        p = BEAM_SECTIONS.get(b["seccion"], BEAM_SECTIONS[DEFAULT_REPART])
        ops.element("elasticBeamColumn", b["tag"], b["iNode"], b["jNode"],
                    p["A"], E, Gm, p["J"], p["Iy"], p["Iz"], 2)

    for w in structure["walls"]:
        p = w["props"]
        ops.element("elasticBeamColumn", w["tag"], w["node_i"], w["node_j"],
                    p["A"], E, Gm, p["J"], p["Iy"], p["Iz"], 1)

    for level, df in structure["diafragmas"].items():
        cx, cy, z = structure["centroids"][level]
        maestro = df["maestro"]
        ops.node(maestro, cx, cy, z)
        ops.fix(maestro, 0, 0, 1, 1, 1, 0)
        ops.rigidDiaphragm(3, maestro, *df["slaves"])

    return True


if __name__ == "__main__":
    geometry = load_geometry()
    st = assemble(geometry)
    from collections import Counter
    sections = Counter(b["seccion"] for b in st["beams"])
    tops = Counter(w["top"] for w in st["walls"])
    bot = Counter(w["bottom"] for w in st["walls"])
    print("Columnas:", len(st["columns"]))
    print("Vigas:", len(st["beams"]), dict(sections))
    print("Muros equiv:", len(st["walls"]))
    print("Nodos de muro nuevos:", len(st["wall_nodes"]))
    print("Apoyos:", len(st["supports"]))
    for lv, df in st["diafragmas"].items():
        print(f"  Diafragma {lv}: {len(df['slaves'])} esclavos")
    print("Muros por nivel (top):", dict(tops))
