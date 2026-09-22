from collections import defaultdict, deque
from math import hypot, isclose


GEOMETRY_TOLERANCE = 0.005


def is_number(value):
    return isinstance(value, (int, float))


def node_lookup(geometry):
    return {node["id"]: node for node in geometry["nodes"]}


def element_key(element):
    return tuple(sorted([element["node_i"], element["node_j"]]))


def duplicate_nodes(geometry):
    seen = defaultdict(list)
    for node in geometry["nodes"]:
        seen[node["id"]].append(node)
    return [f"Duplicate node id {node_id}" for node_id, items in seen.items() if len(items) > 1]


def duplicate_elements(geometry):
    messages = []
    seen = defaultdict(list)
    for collection_name in ["columns", "beams", "foundation_beams"]:
        for element in geometry[collection_name]:
            seen[(collection_name, element_key(element))].append(element["id"])
    for key, ids in seen.items():
        if len(ids) > 1:
            messages.append(f"Duplicate {key[0]} connectivity {ids}")
    return messages


def zero_length_elements(geometry):
    messages = []
    nodes = node_lookup(geometry)
    for collection_name in ["columns", "beams", "foundation_beams"]:
        for element in geometry[collection_name]:
            ni = nodes.get(element["node_i"])
            nj = nodes.get(element["node_j"])
            if not ni or not nj:
                continue
            if None in [ni["x"], ni["y"], ni["z"], nj["x"], nj["y"], nj["z"]]:
                continue
            length = ((nj["x"] - ni["x"])**2 + (nj["y"] - ni["y"])**2 + (nj["z"] - ni["z"])**2) ** 0.5
            if isclose(length, 0.0, abs_tol=GEOMETRY_TOLERANCE):
                messages.append(f"Zero length element {element['id']}")
    return messages


def disconnected_nodes(geometry):
    connected = set()
    for collection_name in ["columns", "beams", "foundation_beams"]:
        for element in geometry[collection_name]:
            connected.add(element["node_i"])
            connected.add(element["node_j"])
    messages = []
    for node in geometry["nodes"]:
        if node["id"] in connected:
            continue
        if node.get("grid_x") in ["B_PRIME", "E1"] or node.get("grid_y") in ["8B", "8A"]:
            messages.append(f"WARNING: exterior node {node['id']} is prepared for pending radier/staircase connectivity")
            continue
        if None in [node["x"], node["y"], node["z"]]:
            messages.append(f"WARNING: prepared node {node['id']} is disconnected because coordinates are pending")
        else:
            messages.append(f"Disconnected node {node['id']}")
    return messages


def missing_node_references(geometry):
    messages = []
    nodes = node_lookup(geometry)
    for collection_name in ["columns", "beams", "foundation_beams"]:
        for element in geometry[collection_name]:
            for field in ["node_i", "node_j"]:
                if element[field] not in nodes:
                    messages.append(f"{element['id']} references missing node {element[field]}")
    return messages


def beam_without_support(geometry):
    messages = []
    column_top_nodes = {column["node_j"] for column in geometry["columns"]}
    for beam in geometry["beams"]:
        if beam["node_i"] not in column_top_nodes:
            messages.append(f"WARNING: Beam {beam['id']} node_i has no vertical supporting column: {beam['node_i']}")
        if beam["node_j"] not in column_top_nodes:
            messages.append(f"WARNING: Beam {beam['id']} node_j has no vertical supporting column: {beam['node_j']}")
    return messages


def vertical_column_alignment(geometry):
    messages = []
    nodes = node_lookup(geometry)
    for column in geometry["columns"]:
        ni = nodes.get(column["node_i"])
        nj = nodes.get(column["node_j"])
        if not ni or not nj or None in [ni["x"], ni["y"], nj["x"], nj["y"]]:
            continue
        if abs(ni["x"] - nj["x"]) > GEOMETRY_TOLERANCE or abs(ni["y"] - nj["y"]) > GEOMETRY_TOLERANCE:
            messages.append(f"WARNING: vertical alignment exceeds 5 mm in {column['id']}")
    return messages


def column_continuity(geometry):
    messages = []
    by_grid = defaultdict(list)
    for column in geometry["columns"]:
        by_grid[(column["grid_x"], column["grid_y"])].append(column)
    for key, columns in by_grid.items():
        if len(columns) < 2:
            messages.append(f"WARNING: incomplete vertical column continuity at {key}")
    return messages


def structural_islands(geometry):
    nodes = {node["id"] for node in geometry["nodes"]}
    adjacency = {node_id: set() for node_id in nodes}
    for collection_name in ["columns", "beams", "foundation_beams"]:
        for element in geometry[collection_name]:
            if element["node_i"] in adjacency and element["node_j"] in adjacency:
                adjacency[element["node_i"]].add(element["node_j"])
                adjacency[element["node_j"]].add(element["node_i"])
    if not nodes:
        return []
    start = next(iter(nodes))
    visited = set([start])
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    missing = nodes - visited
    return [f"WARNING: structural island/disconnected component includes node {node_id}" for node_id in sorted(missing)]


def invalid_dimensions(geometry):
    messages = []
    for foundation in geometry["foundations"]:
        fields = ["thickness"] if foundation.get("boundary") else ["width", "length", "thickness"]
        for field in fields:
            value = foundation[field]
            if value is None:
                messages.append(f"WARNING: Foundation {foundation['id']} has pending {field}")
            elif value <= 0:
                messages.append(f"Foundation {foundation['id']} has missing/invalid {field}")
    for beam in geometry["beams"] + geometry["foundation_beams"]:
        for field in ["width", "height"]:
            value = beam[field]
            if value is None:
                messages.append(f"WARNING: {beam['id']} has pending {field}")
            elif value <= 0:
                messages.append(f"{beam['id']} has missing/invalid {field}")
    for column in geometry["columns"]:
        for field in ["bx", "by"]:
            value = column[field]
            if value is None:
                messages.append(f"WARNING: Column {column['id']} has pending {field}")
            elif value <= 0:
                messages.append(f"Column {column['id']} has missing/invalid {field}")
    for wall in geometry["walls"]:
        if wall["thickness"] is None:
            messages.append(f"WARNING: Wall {wall['id']} has pending thickness")
        elif wall["thickness"] <= 0:
            messages.append(f"Wall {wall['id']} has missing/invalid thickness")
        if None not in [wall["x1"], wall["y1"], wall["x2"], wall["y2"]]:
            if hypot(wall["x2"] - wall["x1"], wall["y2"] - wall["y1"]) <= 0:
                messages.append(f"WARNING: Wall {wall['id']} has pending length/direction")
    for diaphragm in geometry.get("rigid_diaphragms", []):
        if diaphragm.get("z") is None:
            messages.append(f"Rigid diaphragm {diaphragm['id']} has missing z")
        if None not in [diaphragm["x1"], diaphragm["x2"], diaphragm["y1"], diaphragm["y2"]]:
            if abs(diaphragm["x2"] - diaphragm["x1"]) <= 0 or abs(diaphragm["y2"] - diaphragm["y1"]) <= 0:
                messages.append(f"Rigid diaphragm {diaphragm['id']} has invalid boundary")
    for radier in geometry["radiers"]:
        if radier["thickness"] != 0.15:
            messages.append(f"Radier {radier['id']} thickness is not 0.15 m")
    for level, check in geometry.get("tributary_checks", {}).items():
        if abs(check.get("area_error_m2", 0.0)) > 1e-6:
            messages.append(f"Tributary area is not conserved at {level}: {check['area_error_m2']} m2")
        if abs(check.get("D_error_kN", 0.0)) > 1e-6:
            messages.append(f"Dead load is not conserved at {level}: {check['D_error_kN']} kN")
        if abs(check.get("L_error_kN", 0.0)) > 1e-6:
            messages.append(f"Live load is not conserved at {level}: {check['L_error_kN']} kN")
    return messages


def invalid_levels(geometry):
    messages = []
    for level_name, z in geometry["levels"].items():
        if z is None:
            messages.append(f"WARNING: Level {level_name} has pending elevation")
    return messages


def run_all_checks(geometry):
    errors = []
    warnings = []

    checks = [
        duplicate_nodes,
        duplicate_elements,
        zero_length_elements,
        disconnected_nodes,
        missing_node_references,
        beam_without_support,
        vertical_column_alignment,
        column_continuity,
        structural_islands,
        invalid_dimensions,
        invalid_levels,
    ]

    for check in checks:
        for message in check(geometry):
            if message.startswith("WARNING"):
                warnings.append(message)
            else:
                errors.append(message)

    return errors, warnings
