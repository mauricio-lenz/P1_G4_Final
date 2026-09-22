import json
from math import sqrt
from pathlib import Path


def export_unity_structure(geometry, output_path):
    def beam_section_id(beam):
        width = beam.get("width")
        height = beam.get("height")
        if width is None or height is None:
            return "PENDING_SECTION"
        return f"V{int(round(width * 100))}/{int(round(height * 100))}"

    node_ids = set()
    for collection_name in ["columns", "beams", "foundation_beams"]:
        for element in geometry[collection_name]:
            node_ids.add(element["node_i"])
            node_ids.add(element["node_j"])
    for support in geometry.get("supports", []):
        node_ids.add(support["node"])

    nodes = []
    for node in geometry["nodes"]:
        if node["id"] not in node_ids:
            continue
        if None in [node["x"], node["y"], node["z"]]:
            continue
        nodes.append({"id": node["id"], "x": node["x"], "y": node["y"], "z": node["z"]})

    valid_node_ids = {node["id"] for node in nodes}
    node_lookup = {node["id"]: node for node in nodes}
    elements = []
    element_id = 1
    beam_loads = {item["beam_id"]: item for item in geometry.get("beam_tributary_loads", [])}
    nodal_factored_reactions = {node_id: 0.0 for node_id in valid_node_ids}

    for beam in geometry["beams"] + geometry["foundation_beams"]:
        if beam["node_i"] not in valid_node_ids or beam["node_j"] not in valid_node_ids:
            continue
        factored_load = beam_loads.get(beam["id"], {}).get("load_combinations_kN", {}).get("U_1_2D_1_6L", 0.0)
        nodal_factored_reactions[beam["node_i"]] += factored_load / 2.0
        nodal_factored_reactions[beam["node_j"]] += factored_load / 2.0

    column_axials = {}
    carried_to_node = {node_id: nodal_factored_reactions.get(node_id, 0.0) for node_id in valid_node_ids}
    sorted_columns = sorted(
        [column for column in geometry["columns"] if column["node_i"] in valid_node_ids and column["node_j"] in valid_node_ids],
        key=lambda column: node_lookup[column["node_i"]]["z"],
        reverse=True,
    )
    for column in sorted_columns:
        axial = carried_to_node.get(column["node_j"], 0.0)
        column_axials[column["id"]] = axial
        carried_to_node[column["node_i"]] = carried_to_node.get(column["node_i"], 0.0) + axial

    for column in geometry["columns"]:
        if column["node_i"] not in valid_node_ids or column["node_j"] not in valid_node_ids:
            continue
        axial = column_axials.get(column["id"], 0.0)
        elements.append({
            "id": element_id,
            "elementTag": column["id"],
            "sourceId": column["id"],
            "sectionId": "COL70/70",
            "materialId": "HORMIGON_ARMADO",
            "type": "columna",
            "nodeI": column["node_i"],
            "nodeJ": column["node_j"],
            "uniformLoad": 0.0,
            "tributaryArea": 0.0,
            "deadLoad": 0.0,
            "liveLoad": 0.0,
            "factoredLoad14D": 0.0,
            "factoredLoad12D16L": axial,
            "axialI": -axial,
            "axialJ": -axial,
            "shearI": 0.0,
            "shearJ": 0.0,
            "momentI": 0.0,
            "momentJ": 0.0,
        })
        element_id += 1

    for collection_name in ["beams", "foundation_beams"]:
        for beam in geometry[collection_name]:
            if beam["node_i"] not in valid_node_ids or beam["node_j"] not in valid_node_ids:
                continue
            loads = beam_loads.get(beam["id"], {})
            load_cases = loads.get("loads_kN", {})
            combinations = loads.get("load_combinations_kN", {})
            node_i = node_lookup[beam["node_i"]]
            node_j = node_lookup[beam["node_j"]]
            length = sqrt((node_j["x"] - node_i["x"]) ** 2 + (node_j["y"] - node_i["y"]) ** 2 + (node_j["z"] - node_i["z"]) ** 2)
            factored_load = combinations.get("U_1_2D_1_6L", 0.0)
            uniform_load = factored_load / length if length > 0.0 else 0.0
            end_shear = uniform_load * length / 2.0
            elements.append({
                "id": element_id,
                "elementTag": beam["id"],
                "sourceId": beam["id"],
                "sectionId": beam_section_id(beam),
                "materialId": "HORMIGON_ARMADO",
                "type": "viga",
                "nodeI": beam["node_i"],
                "nodeJ": beam["node_j"],
                "uniformLoad": uniform_load,
                "tributaryArea": loads.get("tributary_area_m2", 0.0),
                "deadLoad": load_cases.get("D", 0.0),
                "liveLoad": load_cases.get("L", 0.0),
                "factoredLoad14D": combinations.get("U_1_4D", 0.0),
                "factoredLoad12D16L": combinations.get("U_1_2D_1_6L", 0.0),
                "axialI": 0.0,
                "axialJ": 0.0,
                "shearI": end_shear,
                "shearJ": -end_shear,
                "momentI": 0.0,
                "momentJ": 0.0,
            })
            element_id += 1

    supports = []
    for support in geometry.get("supports", []):
        if support["node"] not in valid_node_ids:
            continue
        supports.append({
            "node": support["node"],
            "type": support["type"],
            "ux": support["ux"],
            "uy": support["uy"],
            "uz": support["uz"],
            "rx": support["rx"],
            "ry": support["ry"],
            "rz": support["rz"],
        })

    diaphragms = []
    for diaphragm in geometry.get("rigid_diaphragms", []):
        diaphragms.append({
            "id": diaphragm["id"],
            "level": diaphragm["level"],
            "z": diaphragm["z"],
            "load_profile": diaphragm.get("load_profile", ""),
            "x1": diaphragm["x1"],
            "x2": diaphragm["x2"],
            "y1": diaphragm["y1"],
            "y2": diaphragm["y2"],
            "type": diaphragm["type"],
        })

    data = {
        "units": "m, kN, kN*m",
        "nodes": nodes,
        "elements": elements,
        "pointLoads": [],
        "supports": supports,
        "rigidDiaphragms": diaphragms,
        "materials": geometry.get("materials", {}),
        "sections": geometry.get("sections", {}),
        "loads": geometry.get("loads", {}),
        "loadCombinations": geometry.get("load_combinations", {}),
        "tributaryAreas": geometry.get("tributary_areas", []),
        "beamTributaryLoads": geometry.get("beam_tributary_loads", []),
        "tributaryChecks": geometry.get("tributary_checks", {}),
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)

    return output_path
