from pathlib import Path
from math import hypot

import plotly.graph_objects as go


def add_line(fig, p1, p2, name, color, width=5, visible=True, hovertext=""):
    if None in [*p1, *p2]:
        return False
    fig.add_trace(go.Scatter3d(
        x=[p1[0], p2[0]],
        y=[p1[1], p2[1]],
        z=[p1[2], p2[2]],
        mode="lines",
        name=name,
        line=dict(color=color, width=width),
        visible=visible,
        hovertext=hovertext,
        hoverinfo="text",
    ))
    return True


def box_mesh(center_x, center_y, width, length, z_top, height):
    if None in [center_x, center_y, width, length, z_top, height]:
        return None
    x0, x1 = center_x - width / 2, center_x + width / 2
    y0, y1 = center_y - length / 2, center_y + length / 2
    z0, z1 = z_top - height, z_top
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return vertices, faces


def add_box(fig, mesh_data, name, color, hovertext="", opacity=0.55):
    if mesh_data is None:
        return False
    vertices, faces = mesh_data
    x, y, z = zip(*vertices)
    i, j, k = zip(*faces)
    fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, name=name, color=color, opacity=opacity, hovertext=hovertext, hoverinfo="text"))
    return True


def wall_mesh(wall):
    if None in [wall["x1"], wall["y1"], wall["x2"], wall["y2"], wall["thickness"], wall["z_bottom"], wall["z_top"]]:
        return None
    dx = wall["x2"] - wall["x1"]
    dy = wall["y2"] - wall["y1"]
    length = hypot(dx, dy)
    if length <= 0:
        return None
    nx = -dy / length * wall["thickness"] / 2
    ny = dx / length * wall["thickness"] / 2
    z0 = wall["z_bottom"]
    z1 = wall["z_top"]
    vertices = [
        (wall["x1"] + nx, wall["y1"] + ny, z0),
        (wall["x1"] - nx, wall["y1"] - ny, z0),
        (wall["x2"] - nx, wall["y2"] - ny, z0),
        (wall["x2"] + nx, wall["y2"] + ny, z0),
        (wall["x1"] + nx, wall["y1"] + ny, z1),
        (wall["x1"] - nx, wall["y1"] - ny, z1),
        (wall["x2"] - nx, wall["y2"] - ny, z1),
        (wall["x2"] + nx, wall["y2"] + ny, z1),
    ]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return vertices, faces


def beam_mesh(beam, start, end):
    if None in [beam["width"], beam["height"], *start, *end]:
        return None
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = hypot(dx, dy)
    if length <= 0:
        return None
    nx = -dy / length * beam["width"] / 2
    ny = dx / length * beam["width"] / 2
    z0 = start[2] - beam["height"] / 2
    z1 = start[2] + beam["height"] / 2
    vertices = [
        (start[0] + nx, start[1] + ny, z0),
        (start[0] - nx, start[1] - ny, z0),
        (end[0] - nx, end[1] - ny, z0),
        (end[0] + nx, end[1] + ny, z0),
        (start[0] + nx, start[1] + ny, z1),
        (start[0] - nx, start[1] - ny, z1),
        (end[0] - nx, end[1] - ny, z1),
        (end[0] + nx, end[1] + ny, z1),
    ]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return vertices, faces


def diaphragm_mesh(diaphragm, display_thickness):
    if None in [diaphragm["x1"], diaphragm["x2"], diaphragm["y1"], diaphragm["y2"], diaphragm["z"]]:
        return None
    x0, x1 = sorted([diaphragm["x1"], diaphragm["x2"]])
    y0, y1 = sorted([diaphragm["y1"], diaphragm["y2"]])
    z1 = diaphragm["z"]
    z0 = z1 - display_thickness
    vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return vertices, faces


def radier_mesh(radier):
    boundary = radier.get("boundary", [])
    if len(boundary) < 3 or radier.get("z_top") is None:
        return None
    z1 = radier["z_top"]
    z0 = z1 - radier.get("thickness", 0.15)
    vertices = [(point[0], point[1], z) for z in [z0, z1] for point in boundary]
    count = len(boundary)
    faces = []
    for index in range(1, count - 1):
        faces.extend([(0, index, index + 1), (count, count + index + 1, count + index)])
    for index in range(count):
        next_index = (index + 1) % count
        faces.extend([(index, next_index, count + next_index), (index, count + next_index, count + index)])
    return vertices, faces


def polygon_prism_mesh(boundary, z_top, thickness):
    if len(boundary) < 3 or z_top is None or thickness is None:
        return None
    z1 = z_top
    z0 = z1 - thickness
    vertices = [(point[0], point[1], z) for z in [z0, z1] for point in boundary]
    count = len(boundary)
    faces = []
    for index in range(1, count - 1):
        faces.extend([(0, index, index + 1), (count, count + index + 1, count + index)])
    for index in range(count):
        next_index = (index + 1) % count
        faces.extend([(index, next_index, count + next_index), (index, count + next_index, count + index)])
    return vertices, faces


def stair_segment_mesh(segment, width, thickness):
    if None in [segment["x1"], segment["y1"], segment["z1"], segment["x2"], segment["y2"], segment["z2"], width, thickness]:
        return None
    dx = segment["x2"] - segment["x1"]
    dy = segment["y2"] - segment["y1"]
    length = hypot(dx, dy)
    if length <= 0:
        return None
    nx, ny = -dy / length * width / 2, dx / length * width / 2
    vertices = [
        (segment["x1"] + nx, segment["y1"] + ny, segment["z1"]),
        (segment["x1"] - nx, segment["y1"] - ny, segment["z1"]),
        (segment["x2"] - nx, segment["y2"] - ny, segment["z2"]),
        (segment["x2"] + nx, segment["y2"] + ny, segment["z2"]),
        (segment["x1"] + nx, segment["y1"] + ny, segment["z1"] - thickness),
        (segment["x1"] - nx, segment["y1"] - ny, segment["z1"] - thickness),
        (segment["x2"] - nx, segment["y2"] - ny, segment["z2"] - thickness),
        (segment["x2"] + nx, segment["y2"] + ny, segment["z2"] - thickness),
    ]
    faces = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)]
    return vertices, faces


def create_viewer_3d(geometry, output_path):
    fig = go.Figure()
    node_map = {node["id"]: node for node in geometry["nodes"]}
    beam_load_map = {item["beam_id"]: item for item in geometry.get("beam_tributary_loads", [])}
    trace_levels = []
    trace_parts = []

    def register(levels, part="STRUCTURE"):
        trace_levels.append(set(levels))
        trace_parts.append(part)

    def level_from_z(z):
        for level_name, level_z in geometry["levels"].items():
            if z == level_z:
                return level_name
        return None

    for node in geometry["nodes"]:
        if None in [node["x"], node["y"], node["z"]]:
            continue
        fig.add_trace(go.Scatter3d(x=[node["x"]], y=[node["y"]], z=[node["z"]], mode="markers+text", name="NODES", text=[str(node["id"])], marker=dict(size=4), hovertext=f"ID: {node['id']}<br>TYPE: NODE<br>LEVEL: {node['level']}", hoverinfo="text"))
        register([node["level"]])

    support_nodes = [node_map[support["node"]] for support in geometry.get("supports", []) if support["node"] in node_map]
    if support_nodes:
        fig.add_trace(go.Scatter3d(
            x=[node["x"] for node in support_nodes],
            y=[node["y"] for node in support_nodes],
            z=[node["z"] for node in support_nodes],
            mode="markers",
            name="SUPPORTS FIXED",
            marker=dict(size=6, symbol="diamond", color="black"),
            hovertext=[f"NODE: {node['id']}<br>TYPE: FIXED SUPPORT<br>ux uy uz rx ry rz fixed" for node in support_nodes],
            hoverinfo="text",
        ))
        register(["FOUNDATION"])

    for column in geometry["columns"]:
        ni = node_map.get(column["node_i"])
        nj = node_map.get(column["node_j"])
        if ni and nj:
            if None not in [column["x_center"], column["y_center"], column["bx"], column["by"], column["z_top"]] and column["z_bottom"] is not None:
                if add_box(fig, box_mesh(column["x_center"], column["y_center"], column["bx"], column["by"], column["z_top"], column["z_top"] - column["z_bottom"]), "COLUMNS", "black", hovertext=f"ID: {column['id']}<br>TYPE: COLUMN<br>DIM: {column['bx']} x {column['by']} m"):
                    register([ni["level"], nj["level"]])
            else:
                if add_line(fig, (ni["x"], ni["y"], ni["z"]), (nj["x"], nj["y"], nj["z"]), "COLUMNS", "black", hovertext=f"ID: {column['id']}<br>TYPE: COLUMN"):
                    register([ni["level"], nj["level"]])

    for beam in geometry["beams"]:
        ni = node_map.get(beam["node_i"])
        nj = node_map.get(beam["node_j"])
        if ni and nj:
            start = (ni["x"], ni["y"], ni["z"])
            end = (nj["x"], nj["y"], nj["z"])
            hovertext = f"ID: {beam['id']}<br>TYPE: BEAM<br>LEVEL: {beam['level']}<br>SECTION: {beam['width']} x {beam['height']} m"
            tributary_load = beam_load_map.get(beam["id"])
            if tributary_load:
                hovertext += f"<br>TRIB AREA: {tributary_load['tributary_area_m2']:.3f} m2<br>D: {tributary_load['loads_kN']['D']:.3f} kN<br>L: {tributary_load['loads_kN']['L']:.3f} kN"
            if add_box(fig, beam_mesh(beam, start, end), "BEAMS", "blue", hovertext=hovertext, opacity=0.75):
                register([beam["level"]])
            elif add_line(fig, start, end, "BEAMS", "blue", hovertext=hovertext):
                register([beam["level"]])

    diaphragm_thickness = geometry.get("constants", {}).get("diaphragm_display_thickness", 0.03)
    for diaphragm in geometry.get("rigid_diaphragms", []):
        hovertext = f"ID: {diaphragm['id']}<br>TYPE: RIGID_DIAPHRAGM<br>LEVEL: {diaphragm['level']}<br>Z: {diaphragm['z']} m"
        if add_box(fig, diaphragm_mesh(diaphragm, diaphragm_thickness), "RIGID DIAPHRAGMS", "cyan", hovertext=hovertext, opacity=0.25):
            register([diaphragm["level"]], "DIAPHRAGM")

    for wall in geometry["walls"]:
        if None in [wall["x1"], wall["y1"]]:
            continue
        z_bottom = wall["z_bottom"] if wall["z_bottom"] is not None else 0.0
        z_top = wall["z_top"] if wall["z_top"] is not None else z_bottom + 0.5
        if wall["x1"] == wall["x2"] and wall["y1"] == wall["y2"]:
            fig.add_trace(go.Scatter3d(
                x=[wall["x1"]],
                y=[wall["y1"]],
                z=[z_bottom],
                mode="markers+text",
                name="WALLS",
                text=[wall["id"]],
                marker=dict(size=8, symbol="diamond", color="red"),
                hovertext=f"ID: {wall['id']}<br>TYPE: STRUCTURAL_WALL<br>STATUS: pending length/thickness",
                hoverinfo="text",
            ))
            register([level_from_z(z_top) or "FOUNDATION"])
        else:
            wall_hovertext = f"ID: {wall['id']}<br>TYPE: STRUCTURAL_WALL<br>THICKNESS: {wall['thickness']} m"
            if add_box(fig, wall_mesh(wall), "WALLS", "red", hovertext=wall_hovertext):
                register([level_from_z(wall["z_top"]) or "FOUNDATION"])
            elif add_line(fig, (wall["x1"], wall["y1"], z_bottom), (wall["x2"], wall["y2"], z_bottom), "WALLS", "red", hovertext=wall_hovertext):
                register(["FOUNDATION"])

    for foundation in geometry["foundations"]:
        mesh = None
        if foundation.get("boundary"):
            mesh = polygon_prism_mesh(foundation["boundary"], geometry["levels"]["FOUNDATION"], foundation["thickness"])
        else:
            mesh = box_mesh(foundation["center_x"], foundation["center_y"], foundation["width"], foundation["length"], geometry["levels"]["FOUNDATION"], foundation["thickness"])
        if add_box(fig, mesh, "FOUNDATIONS", "brown", hovertext=f"ID: {foundation['id']}<br>TYPE: {foundation['type']}<br>THICKNESS: {foundation['thickness']} m"):
            register(["FOUNDATION"])

    for fb in geometry["foundation_beams"]:
        ni = node_map.get(fb["node_i"])
        nj = node_map.get(fb["node_j"])
        if ni and nj:
            start = (ni["x"], ni["y"], fb["z"] if fb["z"] is not None else ni["z"])
            end = (nj["x"], nj["y"], fb["z"] if fb["z"] is not None else nj["z"])
            hovertext = f"ID: {fb['id']}<br>TYPE: FOUNDATION_BEAM<br>SECTION: {fb['width']} x {fb['height']} m"
            if add_box(fig, beam_mesh(fb, start, end), "FOUNDATION BEAMS", "orange", hovertext=hovertext, opacity=0.9):
                register(["FOUNDATION"])
            elif add_line(fig, start, end, "FOUNDATION BEAMS", "orange", hovertext=hovertext):
                register(["FOUNDATION"])

    for radier in geometry["radiers"]:
        if add_box(fig, radier_mesh(radier), "RADIERS", "purple", hovertext=f"ID: {radier['id']}<br>TYPE: RADIER<br>THICKNESS: {radier['thickness']} m<br>Z TOP: {radier['z_top']} m", opacity=0.35):
            register(["FOUNDATION"])

    for stair in geometry.get("stairs", []):
        for segment in stair["segments"]:
            if add_box(fig, stair_segment_mesh(segment, stair["width"], stair["thickness"]), "STAIR", "gold", hovertext=f"ID: {stair['id']}<br>SEGMENT: {segment['id']}<br>WIDTH: {stair['width']} m<br>THICKNESS: {stair['thickness']} m<br>SLOPE: {segment['slope']}", opacity=0.75):
                register(["FOUNDATION"], "STRUCTURE")

    for stair_wall in geometry.get("stair_walls", []):
        if add_line(fig, (stair_wall["x1"], stair_wall["y1"], stair_wall["z1"]), (stair_wall["x2"], stair_wall["y2"], stair_wall["z2"]), "STAIR WALLS", "darkred", width=8, hovertext=f"ID: {stair_wall['id']}<br>THICKNESS: {stair_wall['thickness']} m<br>TOP LEVEL: {stair_wall['top_level']}"):
            register(["FOUNDATION"], "STRUCTURE")

    level_buttons = [
        ("FOUNDATIONS ONLY", "FOUNDATION"),
        ("CIELO 1S", "CIELO_1S"),
        ("CIELO 1", "CIELO_1"),
        ("CIELO 2", "CIELO_2"),
        ("CIELO 3", "CIELO_3"),
        ("CIELO 4", "CIELO_4"),
    ]

    buttons = [dict(label="SHOW ALL", method="update", args=[{"visible": [True] * len(fig.data)}])]
    for label, level in level_buttons:
        buttons.append(dict(
            label=label,
            method="update",
            args=[{"visible": [level in levels for levels in trace_levels]}],
        ))

    diaphragm_buttons = [
        dict(label="DIAFRAGMAS ON", method="update", args=[{"visible": [True] * len(fig.data)}]),
        dict(label="SIN DIAFRAGMAS", method="update", args=[{"visible": [part != "DIAPHRAGM" for part in trace_parts]}]),
        dict(label="SOLO DIAFRAGMAS", method="update", args=[{"visible": [part == "DIAPHRAGM" or part == "STRUCTURE" for part in trace_parts]}]),
    ]

    fig.update_layout(
        title="UANDES structural geometry - 3D viewer",
        scene=dict(xaxis_title="X [m]", yaxis_title="Y [m]", zaxis_title="Z [m]", aspectmode="data"),
        updatemenus=[
            dict(buttons=buttons, x=0.0, y=1.12),
            dict(buttons=diaphragm_buttons, x=0.38, y=1.12),
        ]
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path
