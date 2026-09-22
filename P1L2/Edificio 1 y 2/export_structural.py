# ============================================================
# EXPORT STRUCTURAL - Edificio de Ingenieria UANDES
# ============================================================
# Exporta un JSON ampliado (compatible con el viewer Unity pero con
# secciones adicionales) con la superestructura analizada:
#   - nodes, elements (columnas/vigas), supports  [base viewer]
#   - walls          : muros equivalentes
#   - diaphragms     : maestro + nodos esclavos por piso
#   - tributaryAreas : area y carga q_G por viga
#   - localAxes      : vector de eje local de cada elemento
# Unidades: m, kN, kN*m.
# ============================================================
import os, json
from math import hypot

from materials import Q_G
from structural_model import DEFAULT_REPART, BEAM_SECTIONS

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(PROJECT_DIR, "outputs", "estructura_gravedad_unity.json")


def extract_forces(structure):
    """Extrae las fuerzas internas reales (axial, corte vertical, momento de
    flexion vertical) de cada elemento con ops.eleForce, tras el analisis.

    Para elasticBeamColumn 3D eleForce devuelve 12 valores:
      [N, Vy, Vz, T, Mz, My] en el nodo i y [..] en el nodo j.
    - axial (N)                   : indices 0 y 6
    - corte vertical (Vz)         : indices 2 y 8
    - momento flexion vertical(My): indices 4 y 10  (verificado con voladizo)
    Devuelve dict {tag: {axial:[i,j], shear:[i,j], moment:[i,j], w_uniformo}}.
    """
    import openseespy.opensees as ops
    forces = {}
    for grupo in ("columns", "beams", "walls"):
        for el in structure[grupo]:
            tag = el["tag"]
            try:
                f = list(ops.eleForce(tag))
            except Exception:
                continue
            if len(f) < 12:
                continue
            axial = (f[0], f[6])
            shear = (f[2], f[8])
            moment = (f[4], f[10])
            w_uniformo = 0.0
            if grupo == "beams":
                d = structure.get("beam_data", {}).get(tag)
                if d and d.get("largo", 0.0) > 0 and d.get("carga", 0.0) > 0:
                    w_uniformo = -abs(d["carga"] / d["largo"])
            forces[tag] = {
                "axial": axial, "shear": shear, "moment": moment,
                "w_uniformo": w_uniformo,
            }
    return forces


def node_coord_map(structure, geometry):
    coords = {}
    for n in geometry["nodes"]:
        if None not in (n["x"], n["y"], n["z"]):
            coords[n["id"]] = (n["x"], n["y"], n["z"])
    for ne in structure["wall_nodes"]:
        coords[ne["id"]] = (ne["x"], ne["y"], ne["z"])
    for level, (cx, cy, z) in structure["centroids"].items():
        coords[structure["diafragmas"][level]["maestro"]] = (cx, cy, z)
    return coords


def export_extended(structure, geometry, beam_data, out_path=OUT_PATH,
                    forces=None):
    coords = node_coord_map(structure, geometry)
    if forces is None:
        forces = {}

    # nodos a incluir: extremos de columnas/vigas/muros + apoyos + maestros
    used = set()
    for c in structure["columns"]:
        used |= {c["iNode"], c["jNode"]}
    for b in structure["beams"]:
        used |= {b["iNode"], b["jNode"]}
    for w in structure["walls"]:
        used |= {w["node_i"], w["node_j"]}
    for s in structure["supports"]:
        used.add(s["node"])
    for lv, df in structure["diafragmas"].items():
        used.add(df["maestro"])

    nodes = [{"id": nid, "x": coords[nid][0], "y": coords[nid][1],
              "z": coords[nid][2]} for nid in sorted(used)
             if nid in coords]
    valid = {n["id"] for n in nodes}

    # colores/tipos
    def tree(name, pos, color, extra=None):
        node = {"name": name, "x": pos[0], "y": pos[1], "z": pos[2],
                "color": color}
        if extra:
            node.update(extra)
        return node

    elements = []
    eid = 1
    for c in structure["columns"]:
        if c["iNode"] not in valid or c["jNode"] not in valid:
            continue
        fa = forces.get(c["tag"], {}).get("axial", (0.0, 0.0))
        fs = forces.get(c["tag"], {}).get("shear", (0.0, 0.0))
        fm = forces.get(c["tag"], {}).get("moment", (0.0, 0.0))
        elements.append({
            "id": eid, "type": "columna", "nodeI": c["iNode"], "nodeJ": c["jNode"],
            "seccion": c["seccion"],
            "uniformLoad": 0.0,
            "axialI": fa[0], "axialJ": fa[1],
            "shearI": fs[0], "shearJ": fs[1],
            "momentI": fm[0], "momentJ": fm[1],
            "piso": "", "areaTributaria": 0.0, "cargaTributaria": 0.0,
        })
        eid += 1
    for b in structure["beams"]:
        if b["iNode"] not in valid or b["jNode"] not in valid:
            continue
        ta = beam_data.get(b["tag"])
        fa = forces.get(b["tag"], {}).get("axial", (0.0, 0.0))
        fs = forces.get(b["tag"], {}).get("shear", (0.0, 0.0))
        fm = forces.get(b["tag"], {}).get("moment", (0.0, 0.0))
        wu = forces.get(b["tag"], {}).get("w_uniformo", 0.0)
        elements.append({
            "id": eid, "type": "viga", "nodeI": b["iNode"], "nodeJ": b["jNode"],
            "seccion": b["seccion"], "piso": b["piso"],
            "uniformLoad": wu,
            "axialI": fa[0], "axialJ": fa[1],
            "shearI": fs[0], "shearJ": fs[1],
            "momentI": fm[0], "momentJ": fm[1],
            "areaTributaria": ta["area"] if ta else 0.0,
            "cargaTributaria": ta["carga"] if ta else 0.0,
        })
        eid += 1

    walls = []
    for w in structure["walls"]:
        if w["node_i"] not in valid or w["node_j"] not in valid:
            continue
        walls.append({"id": eid, "iNode": w["node_i"], "jNode": w["node_j"],
                      "type": "muro", "grosor": round(w["props"]["b"], 4),
                      "longitud": round(w["length"], 3),
                      "bottom": w["bottom"], "top": w["top"]})
        eid += 1

    supports = [{"node": s["node"], "type": "fixed", "ux": 1, "uy": 1,
                 "uz": 1, "rx": 1, "ry": 1, "rz": 1}
                for s in structure["supports"]]

    diaphragms = {}
    for level, df in structure["diafragmas"].items():
        cx, cy, z = structure["centroids"][level]
        diaphragms[level] = {
            "maestro": df["maestro"], "x": cx, "y": cy, "z": z,
            "slaves": df["slaves"],
        }

    # areas tributarias por piso (resumen)
    tributary = {}
    for level, d in sorted(beam_data.items()):
        piso = d["piso"]
        tributary.setdefault(piso, {"area_total": 0.0, "carga_total": 0.0,
                                    "vigas": 0})
        tributary[piso]["area_total"] += d["area"]
        tributary[piso]["carga_total"] += d["carga"]
        tributary[piso]["vigas"] += 1
    tributary_list = [{"piso": lv, "area_total": v["area_total"],
                       "carga_total": v["carga_total"], "vigas": v["vigas"]}
                      for lv, v in sorted(tributary.items())]

    # ejes locales
    local_axes = []
    for el in elements:
        p1 = coords[el["nodeI"]]; p2 = coords[el["nodeJ"]]
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        L = (dx*dx+dy*dy)**0.5
        local_axes.append({"element": el["id"], "dx": dx/L if L else 0.0,
                           "dy": dy/L if L else 0.0})
    for wall in walls:
        p1 = coords[wall["iNode"]]; p2 = coords[wall["jNode"]]
        dx, dy = p2[0]-p1[0], p2[1]-p1[1]
        L = (dx*dx+dy*dy)**0.5
        local_axes.append({"element": wall["id"], "dx": dx/L if L else 0.0,
                           "dy": dy/L if L else 0.0})

    # listas orientadas a arrays (legibles por JsonUtility de Unity)
    diaphragm_list = [{"level": lv, "x": df_x["x"], "y": df_x["y"],
                       "z": df_x["z"], "maestro": df_x["maestro"],
                       "slaves": df_x["slaves"]}
                      for lv, df_x in diaphragms.items()]

    # forma base compatible con el viewer (nodulos limitados)
    data = {
        "units": "m, kN, kN*m",
        "q_G": Q_G,
        "nodes": nodes,
        "elements": elements,
        "walls": walls,
        "supports": supports,
        "diaphragms": diaphragms,
        "diaphragmList": diaphragm_list,
        "tributaryAreasByFloor": tributary,
        "tributaryList": tributary_list,
        "localAxes": local_axes,
        "pointLoads": [],
        "statistics": {
            "columnas": len(structure["columns"]),
            "vigas": len(structure["beams"]),
            "muros_equiv": len(walls),
            "apoyos": len(supports),
        },
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return out_path


if __name__ == "__main__":
    from structural_model import load_geometry, assemble
    geometry = load_geometry()
    st = assemble(geometry)
    # generar datos tributarios minimos
    from gravity_analysis import compute_tributary_areas
    beam_data, _ = compute_tributary_areas(geometry, st)
    p = export_extended(st, geometry, beam_data)
    print("Exportado:", p)
