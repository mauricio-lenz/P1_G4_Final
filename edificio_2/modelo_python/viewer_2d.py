from pathlib import Path

import plotly.graph_objects as go


def valid_xy(item):
    return item.get("x") is not None and item.get("y") is not None


def hover_text(item, item_type):
    parts = [f"ID: {item.get('id')}", f"TYPE: {item_type}"]
    for key in ["x", "y", "level", "width", "height", "length", "thickness", "bx", "by", "reinforcement"]:
        if key in item:
            parts.append(f"{key.upper()}: {item.get(key)}")
    return "<br>".join(parts)


def create_viewer_2d(geometry, output_path):
    fig = go.Figure()
    beam_load_map = {item["beam_id"]: item for item in geometry.get("beam_tributary_loads", [])}
    trace_levels = []
    trace_parts = []
    all_levels = ["FOUNDATION", "CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]

    def register(levels, part="STRUCTURE"):
        trace_levels.append(set(levels))
        trace_parts.append(part)

    def level_from_z(z):
        for level_name, level_z in geometry["levels"].items():
            if z == level_z:
                return level_name
        return None

    x_values = [x for x in geometry["grids"]["x"].values() if x is not None]
    y_values = [y for y in geometry["grids"]["y"].values() if y is not None]
    xmin, xmax = (min(x_values) - 1, max(x_values) + 1) if x_values else (-1, 1)
    ymin, ymax = (min(y_values) - 1, max(y_values) + 1) if y_values else (-1, 1)

    for axis_name, x in geometry["grids"]["x"].items():
        if x is None:
            continue
        fig.add_trace(go.Scatter(
            x=[x, x],
            y=[ymin, ymax],
            mode="lines+text",
            name=f"GRID X {axis_name}",
            text=[axis_name, ""],
            line=dict(color="lightgray", dash="dash"),
        ))
        register(all_levels)

    for axis_name, y in geometry["grids"]["y"].items():
        if y is None:
            continue
        fig.add_trace(go.Scatter(
            x=[xmin, xmax],
            y=[y, y],
            mode="lines+text",
            name=f"GRID Y {axis_name}",
            text=[axis_name, ""],
            line=dict(color="lightgray", dash="dash"),
        ))
        register(all_levels)

    nodes = [node for node in geometry["nodes"] if valid_xy(node)]
    for level in all_levels:
        level_nodes = [node for node in nodes if node["level"] == level]
        if not level_nodes:
            continue
        fig.add_trace(go.Scatter(
            x=[node["x"] for node in level_nodes],
            y=[node["y"] for node in level_nodes],
            mode="markers+text",
            name=f"NODES {level}",
            text=[str(node["id"]) for node in level_nodes],
            hovertext=[hover_text(node, "NODE") for node in level_nodes],
            hoverinfo="text",
        ))
        register([level])

    node_map = {node["id"]: node for node in geometry["nodes"]}
    support_nodes = [node_map[support["node"]] for support in geometry.get("supports", []) if support["node"] in node_map and valid_xy(node_map[support["node"]])]
    if support_nodes:
        fig.add_trace(go.Scatter(
            x=[node["x"] for node in support_nodes],
            y=[node["y"] for node in support_nodes],
            mode="markers",
            name="SUPPORTS FIXED",
            marker=dict(symbol="triangle-up", size=13, color="black"),
            hovertext=[f"NODE: {node['id']}<br>TYPE: FIXED SUPPORT<br>ux uy uz rx ry rz fixed" for node in support_nodes],
            hoverinfo="text",
        ))
        register(["FOUNDATION"])

    for collection_name, color in [("beams", "blue")]:
        for element in geometry[collection_name]:
            ni = node_map.get(element["node_i"])
            nj = node_map.get(element["node_j"])
            if not ni or not nj or not valid_xy(ni) or not valid_xy(nj):
                continue
            hovertext = hover_text(element, element["type"])
            tributary_load = beam_load_map.get(element["id"])
            if tributary_load:
                hovertext += f"<br>TRIB AREA: {tributary_load['tributary_area_m2']:.3f} m2<br>D: {tributary_load['loads_kN']['D']:.3f} kN<br>L: {tributary_load['loads_kN']['L']:.3f} kN"
            fig.add_trace(go.Scatter(
                x=[ni["x"], nj["x"]],
                y=[ni["y"], nj["y"]],
                mode="lines",
                name=collection_name.upper(),
                line=dict(color=color, width=4),
                hovertext=hovertext,
                hoverinfo="text",
            ))
            register([element.get("level", "FOUNDATION")])

    for diaphragm in geometry.get("rigid_diaphragms", []):
        if None in [diaphragm["x1"], diaphragm["x2"], diaphragm["y1"], diaphragm["y2"]]:
            continue
        x0, x1 = diaphragm["x1"], diaphragm["x2"]
        y0, y1 = diaphragm["y1"], diaphragm["y2"]
        fig.add_trace(go.Scatter(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            mode="lines",
            fill="toself",
            name="RIGID DIAPHRAGMS",
            line=dict(color="rgba(0, 170, 220, 0.70)", width=1),
            fillcolor="rgba(0, 170, 220, 0.12)",
            hovertext=hover_text(diaphragm, diaphragm["type"]),
            hoverinfo="text",
        ))
        register([diaphragm["level"]], "DIAPHRAGM")

    for foundation in geometry["foundations"]:
        if foundation.get("boundary"):
            x = [point[0] for point in foundation["boundary"]] + [foundation["boundary"][0][0]]
            y = [point[1] for point in foundation["boundary"]] + [foundation["boundary"][0][1]]
            fig.add_trace(go.Scatter(
                x=x,
                y=y,
                mode="lines",
                fill="toself",
                name="FOUNDATIONS",
                line=dict(color="brown", width=2),
                fillcolor="rgba(120, 70, 20, 0.20)",
                hovertext=hover_text(foundation, foundation["type"]),
                hoverinfo="text",
            ))
            register(["FOUNDATION"])
            continue
        if foundation["center_x"] is None or foundation["center_y"] is None:
            continue
        fig.add_trace(go.Scatter(
            x=[foundation["center_x"]],
            y=[foundation["center_y"]],
            mode="markers",
            name="FOUNDATIONS",
            marker=dict(symbol="square", size=14, color="brown"),
            hovertext=hover_text(foundation, foundation["type"]),
            hoverinfo="text",
        ))
        register(["FOUNDATION"])

    for element in geometry["foundation_beams"]:
        ni = node_map.get(element["node_i"])
        nj = node_map.get(element["node_j"])
        if not ni or not nj or not valid_xy(ni) or not valid_xy(nj):
            continue
        fig.add_trace(go.Scatter(
            x=[ni["x"], nj["x"]],
            y=[ni["y"], nj["y"]],
            mode="lines",
            name="FOUNDATION_BEAMS",
            line=dict(color="orange", width=7),
            hovertext=hover_text(element, element["type"]),
            hoverinfo="text",
        ))
        register(["FOUNDATION"])

    for wall in geometry["walls"]:
        if None in [wall["x1"], wall["y1"], wall["x2"], wall["y2"]]:
            continue
        wall_level = level_from_z(wall["z_top"]) or "FOUNDATION"
        if wall["x1"] == wall["x2"] and wall["y1"] == wall["y2"]:
            fig.add_trace(go.Scatter(
                x=[wall["x1"]],
                y=[wall["y1"]],
                mode="markers+text",
                name="WALLS",
                text=[wall["id"]],
                marker=dict(symbol="diamond", size=16, color="red"),
                hovertext=hover_text(wall, wall["type"]),
                hoverinfo="text",
            ))
            register([wall_level])
            continue
        fig.add_trace(go.Scatter(
            x=[wall["x1"], wall["x2"]],
            y=[wall["y1"], wall["y2"]],
            mode="lines",
            name="WALLS",
            line=dict(color="red", width=6),
            hovertext=hover_text(wall, wall["type"]),
            hoverinfo="text",
        ))
        register([wall_level])

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
        title="UANDES structural geometry - 2D viewer",
        xaxis=dict(title="X [m]", scaleanchor="y", scaleratio=1),
        yaxis=dict(title="Y [m]"),
        legend=dict(groupclick="toggleitem"),
        updatemenus=[
            dict(buttons=buttons, x=0.0, y=1.12),
            dict(buttons=diaphragm_buttons, x=0.38, y=1.12),
        ],
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    return output_path
