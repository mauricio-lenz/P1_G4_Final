import openseespy.opensees as ops


def build_opensees_nodes_only(geometry):
    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    created_nodes = []
    skipped_nodes = []
    created_node_ids = set()

    for node in geometry["nodes"]:
        if None in [node["x"], node["y"], node["z"]]:
            skipped_nodes.append(node["id"])
            continue
        ops.node(node["id"], node["x"], node["y"], node["z"])
        created_nodes.append(node["id"])
        created_node_ids.add(node["id"])

    fixed_supports = []
    for support in geometry.get("supports", []):
        node_id = support["node"]
        if node_id not in created_node_ids:
            continue
        ops.fix(node_id, support["ux"], support["uy"], support["uz"], support["rx"], support["ry"], support["rz"])
        fixed_supports.append(node_id)

    return {
        "created_nodes": created_nodes,
        "skipped_nodes_missing_coordinates": skipped_nodes,
        "fixed_supports": fixed_supports,
        "elements_created": 0,
        "note": "Foundation-level nodes are fixed. Elements are not created until E, A, G, J, Iy and Iz are explicitly provided.",
    }
