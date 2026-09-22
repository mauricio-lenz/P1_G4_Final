from geometry import Beam, Column, Foundation, FoundationBeam, Node, Radier, RigidDiaphragm, Stair, StairWall, StructuralWall, to_dict_list
from math import hypot


GEOMETRY_TOLERANCE = 0.005

H20 = 0.20
H60 = 0.60
H100 = 1.00
H120 = 1.20

FOUNDATION_HEIGHTS = {
    "h20": H20,
    "h60": H60,
    "h100": H100,
    "h120": H120,
}

RADIER_THICKNESS = 0.15
EXTERIOR_RADIER_TOP_Z = -7.97
EXTERIOR_FOUNDATION_WALL_THICKNESS = 0.20
EXTERIOR_FOUNDATION_BEAM_WIDTH = 0.20
EXTERIOR_FOUNDATION_BEAM_HEIGHT = 1.505
STAIR_WIDTH = 4.30
STAIR_THICKNESS = 0.15
STAIR_FIRST_RUN = 4.17
STAIR_LANDING_RUN = 2.63
STAIR_FIRST_SLOPE = 0.5246
STAIR_SECOND_SLOPE = 0.5262
STAIR_ENTRY_EXTENSION = 1.22
STAIR_LANDING_Z = -5.945
STAIR_LANDING_WALL_TOP_Z = -5.15

ISOLATED_FOOTING = "ISOLATED_FOOTING"
STRIP_FOOTING = "STRIP_FOOTING"
FOUNDATION_BEAM = "FOUNDATION_BEAM"
FOUNDATION_WALL = "FOUNDATION_WALL"
RADIER = "RADIER"
REINFORCED_CONCRETE = "HORMIGON_ARMADO"

# Altura repetida informada por el usuario: 396 cm = 3.96 m.
FLOOR_HEIGHT = 3.96

CIELO_1S_Z = -4.01
CIELO_1_Z = -0.05
CIELO_2_Z = 3.91
CIELO_3_Z = 7.87
CIELO_4_Z = 11.83

levels = {
    "FOUNDATION": CIELO_1S_Z - RADIER_THICKNESS,
    "CIELO_1S": CIELO_1S_Z,
    "CIELO_1": CIELO_1_Z,
    "CIELO_2": CIELO_2_Z,
    "CIELO_3": CIELO_3_Z,
    "CIELO_4": CIELO_4_Z,
}

LEVEL_NODE_BASE = {
    "FOUNDATION": 1000,
    "CIELO_1S": 2000,
    "CIELO_1": 3000,
    "CIELO_2": 4000,
    "CIELO_3": 5000,
    "CIELO_4": 6000,
}

VERTICAL_LEVEL_SEQUENCE = ["FOUNDATION", "CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]
FLOOR_BEAM_LEVELS = ["CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]
DIAPHRAGM_LEVELS = ["CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]
DIAPHRAGM_DISPLAY_THICKNESS = 0.03
LOAD_SLAB_THICKNESS = 0.15
CONCRETE_UNIT_WEIGHT_KG_M3 = 2500.0
ADDITIONAL_DEAD_LOAD_KG_M2 = 260.0
LIVE_LOAD_KG_M2 = 500.0
ROOF_ADDITIONAL_DEAD_LOAD_KG_M2 = 200.0
ROOF_LIVE_LOAD_KG_M2 = 200.0
ELEVATOR_ROOF_ADDITIONAL_DEAD_LOAD_KG_M2 = 1500.0
ELEVATOR_ROOF_LIVE_LOAD_KG_M2 = 100.0
KGF_M2_TO_KN_M2 = 9.80665 / 1000.0
LOADED_DIAPHRAGM_LEVELS = ["CIELO_1S", "CIELO_1", "CIELO_2", "CIELO_3", "CIELO_4"]
LOAD_COMBINATIONS = {
    "U_1_4D": {"D": 1.4, "L": 0.0},
    "U_1_2D_1_6L": {"D": 1.2, "L": 1.6},
}
DIAPHRAGM_12_VOID_WIDTH = 1.50
DIAPHRAGM_12_VOID_PANELS = {
    ("A_PRIME", "A", "1A_PRIME", "2"),
    ("A_PRIME", "A", "2", "2A_PRIME"),
}
CIELO_4_DIAPHRAGM_VOIDS = [
    {
        "id": "VOID_L403_01",
        "origin_grid_x": "B",
        "origin_grid_y": "1",
        "offset_x": 0.0,
        "offset_y": 5.04,
        "width_x": 2.06,
        "length_y": 1.777,
    },
    {
        "id": "VOID_L403_02",
        "origin_grid_x": "B",
        "origin_grid_y": "1",
        "offset_x": -2.06,
        "offset_y": 5.04,
        "width_x": 2.06,
        "length_y": 1.777,
    },
    {
        "id": "VOID_L403_03",
        "origin_grid_x": "B",
        "origin_grid_y": "1",
        "offset_x": 0.0,
        "offset_y": 5.04 + 1.777 + 2.10,
        "width_x": 2.06,
        "length_y": 1.777,
    },
    {
        "id": "VOID_L403_04",
        "origin_grid_x": "B",
        "origin_grid_y": "1",
        "offset_x": -2.06,
        "offset_y": 5.04 + 1.777 + 2.10,
        "width_x": 2.06,
        "length_y": 1.777,
    },
    {
        "id": "VOID_CPRIME_2_TOWARD_C_01",
        "origin_grid_x": "C_PRIME",
        "origin_grid_y": "2",
        "offset_x": -0.353 - 2.06,
        "offset_y": 0.0,
        "width_x": 2.06,
        "length_y": 1.777,
    },
    {
        "id": "VOID_CPRIME_2_TOWARD_C_02",
        "origin_grid_x": "C_PRIME",
        "origin_grid_y": "2",
        "offset_x": -0.353 - 2.06,
        "offset_y": -2.06 - 1.777,
        "width_x": 2.06,
        "length_y": 1.777,
    },
]
DIAPHRAGM_LEVEL_PREFIX = {
    "CIELO_1S": "S",
    "CIELO_1": "1",
    "CIELO_2": "2",
    "CIELO_3": "3",
    "CIELO_4": "4",
}

# Ejes de planta. Se agregan ejes auxiliares solo donde el usuario definio vigas
# desplazadas desde ejes principales.
GRID_X_AXIS_NAMES = [
    "A_PRIME",
    "A",
    "A_B_MID",
    "B",
    "B_C_MID",
    "C",
    "C_CPRIME_500",
    "C_PRIME",
    "D",
    "D_PRIME",
    "B_PRIME",
    "E1",
]

GRID_Y_AXIS_NAMES = ["8B", "8A", "1", "1A_PRIME", "2", "2A_PRIME", "3"]
DIAPHRAGM_GRID_X_AXIS_NAMES = ["A_PRIME", "A", "B", "C", "C_PRIME", "D", "D_PRIME"]
DIAPHRAGM_GRID_Y_AXIS_NAMES = ["1", "1A_PRIME", "2", "2A_PRIME", "3"]

# Distancias entregadas por el usuario, convertidas de cm a m.
GRID_X_SPANS = [3.75, 3.75, 3.75, 5.00, 5.00, 5.00, 2.58, 2.42, 0.225]
GRID_Y_SPANS = [4.30, 6.42, 4.265, 4.635, 2.985, 4.265]

grid_x = {}
grid_y = {}

COLUMN_BX = 0.70
COLUMN_BY = 0.70

# Muro eje D' con apertura.
D_WALL_OPENING_START_FROM_GRID_1 = 6.15
D_WALL_OPENING_LENGTH = 2.40
ELEVATOR_TOP_WALL_Y = 3.205
ELEVATOR_WALL_LENGTH = 2.945
ELEVATOR_DIAPHRAGM_VOID_PANELS = {
    ("C_PRIME", "D", "1A_PRIME", "2"),
    ("D", "D_PRIME", "1A_PRIME", "2"),
}

# Muros de esquina interpretados desde las imagenes enviadas por el usuario.
AP1_VERTICAL_WALL_THICKNESS = 0.60
AP1_VERTICAL_WALL_DOWN = 1.095
AP1_VERTICAL_WALL_UP = 1.825
AP1_HORIZONTAL_WALL_THICKNESS = 0.30
AP1_HORIZONTAL_WALL_LENGTH = 1.45

AP3_VERTICAL_WALL_THICKNESS = 0.60
AP3_VERTICAL_WALL_DOWN = 1.825
AP3_VERTICAL_WALL_UP = 1.09
AP3_HORIZONTAL_WALL_THICKNESS = 0.30
AP3_HORIZONTAL_WALL_LENGTH = 1.85

STRUCTURAL_POSITIONS = [
    ("P01", "B", "1"),
    ("P02", "C", "1"),
    ("P03", "D_PRIME", "1"),
    ("P04", "A", "2"),
    ("P05", "B", "2"),
    ("P06", "C", "2"),
    ("P07", "B", "3"),
    ("P08", "C", "3"),
]

ISOLATED_FOOTING_SPECS = {}
FOUNDATION_BEAM_SPECS = []

EXTERIOR_NODE_X_AXES = ["B_PRIME", "E1"]
EXTERIOR_NODE_Y_AXES = ["8B", "8A"]

SUPERSTRUCTURE_BEAM_SPECS = [
    ("A_PRIME", "1", "A_PRIME", "3", 0.40, 0.80, "V40/80"),
    ("A_PRIME", "1", "D_PRIME", "1", 0.60, 0.80, "V60/80"),
    ("A_PRIME", "3", "D_PRIME", "3", 0.60, 0.80, "V60/80"),
    ("A", "1", "A", "3", 0.60, 0.80, "V60/80"),
    ("A_B_MID", "1", "A_B_MID", "3", 0.60, 0.80, "V60/80"),
    ("B", "1", "B", "3", 0.60, 0.80, "V60/80"),
    ("B_C_MID", "1", "B_C_MID", "3", 0.60, 0.80, "V60/80"),
    ("C", "1", "C", "3", 0.60, 0.80, "V60/80"),
    ("C_CPRIME_500", "1", "C_CPRIME_500", "3", 0.60, 0.80, "V60/80"),
    ("A_PRIME", "1A_PRIME", "A_B_MID", "1A_PRIME", 0.30, 0.80, "V30/80"),
    ("A", "2", "D_PRIME", "2", 0.60, 0.80, "V60/80"),
    ("A_PRIME", "2A_PRIME", "A_B_MID", "2A_PRIME", 0.30, 0.80, "V30/80"),
]


def rectangular_section(section_id, width, height, material=REINFORCED_CONCRETE):
    area = width * height
    iy = width * height ** 3 / 12.0
    iz = height * width ** 3 / 12.0
    torsion_j = iy + iz
    return {
        "id": section_id,
        "shape": "RECTANGULAR",
        "material": material,
        "width_m": width,
        "height_m": height,
        "area_m2": area,
        "Iy_m4": iy,
        "Iz_m4": iz,
        "J_approx_m4": torsion_j,
    }


MATERIALS = {
    REINFORCED_CONCRETE: {
        "id": REINFORCED_CONCRETE,
        "name": "Hormigon armado",
        "unit_weight_kN_m3": 25.0,
        "status": "ACTIVE_ASSUMED_STANDARD_VALUES",
    }
}

SECTIONS = {
    "V30/80": rectangular_section("V30/80", 0.30, 0.80),
    "V40/80": rectangular_section("V40/80", 0.40, 0.80),
    "V60/80": rectangular_section("V60/80", 0.60, 0.80),
    "COL70/70": rectangular_section("COL70/70", COLUMN_BX, COLUMN_BY),
    "MURO_EQ_25": rectangular_section("MURO_EQ_25", 0.25, FLOOR_HEIGHT),
    "MURO_EQ_30": rectangular_section("MURO_EQ_30", 0.30, FLOOR_HEIGHT),
    "MURO_EQ_60": rectangular_section("MURO_EQ_60", 0.60, FLOOR_HEIGHT),
}


def generate_grid_coordinates(axis_names, spans):
    coordinates = {}

    if not axis_names:
        return coordinates

    coordinates[axis_names[0]] = 0.0
    current = 0.0

    for index, axis_name in enumerate(axis_names[1:], start=1):
        if index - 1 < len(spans):
            current += spans[index - 1]
            coordinates[axis_name] = current
        else:
            coordinates[axis_name] = None

    return coordinates


def refresh_grids():
    global grid_x, grid_y
    grid_x = generate_grid_coordinates(GRID_X_AXIS_NAMES, GRID_X_SPANS)
    grid_y = generate_grid_coordinates(GRID_Y_AXIS_NAMES, GRID_Y_SPANS)

    # The exterior axes are an offset extension and must not move the original
    # building grid, whose axis 1 remains the origin.
    grid_x.update({
        "B_PRIME": grid_x["C"] + 3.224,
        "E1": grid_x["C"] + 3.224 + 7.05,
    })
    grid_y.update({
        "1": 0.0,
        "1A_PRIME": 4.265,
        "2": 8.90,
        "2A_PRIME": 11.885,
        "3": 16.15,
        "ELEVATOR_Y_LOW": ELEVATOR_TOP_WALL_Y,
        "ELEVATOR_Y_HIGH": ELEVATOR_TOP_WALL_Y + ELEVATOR_WALL_LENGTH,
        "DPRIME_3_STRIP_TOP": 16.15 + 1.20,
        "DPRIME_3_STRIP_BOTTOM": 16.15 - 9.20,
    })
    grid_y["8A"] = grid_y["1"] - 6.42
    grid_y["8B"] = grid_y["8A"] - 4.30


def structural_node(node_id, grid_x_name, grid_y_name, level):
    x = grid_x.get(grid_x_name)
    y = grid_y.get(grid_y_name)
    z = levels.get(level)
    return Node(node_id, grid_x_name, grid_y_name, level, x, y, z)


def add_wall_for_each_storey(walls, wall_id, gx1, gy1, gx2, gy2, x1, y1, x2, y2, thickness):
    for level_index, (bottom_level, top_level) in enumerate(zip(VERTICAL_LEVEL_SEQUENCE, VERTICAL_LEVEL_SEQUENCE[1:]), start=1):
        walls.append(StructuralWall(
            id=f"{wall_id}_L{level_index}",
            grid_x1=gx1,
            grid_y1=gy1,
            grid_x2=gx2,
            grid_y2=gy2,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            thickness=thickness,
            z_bottom=levels[bottom_level],
            z_top=levels[top_level],
            status="ACTIVE",
        ))


def create_diaphragm(diaphragm_number, level, gx1, gx2, gy1, gy2):
    x1 = grid_x.get(gx1)
    x2 = grid_x.get(gx2)
    if (gx1, gx2, gy1, gy2) in DIAPHRAGM_12_VOID_PANELS:
        x1 += DIAPHRAGM_12_VOID_WIDTH
    load_profile = "FLOOR"
    if level == "CIELO_4":
        load_profile = "ELEVATOR_ROOF" if (gx1, gx2, gy1, gy2) in ELEVATOR_DIAPHRAGM_VOID_PANELS else "ROOF"
    return RigidDiaphragm(
        id=f"D{diaphragm_number}",
        grid_x1=gx1,
        grid_x2=gx2,
        grid_y1=gy1,
        grid_y2=gy2,
        x1=x1,
        x2=x2,
        y1=grid_y.get(gy1),
        y2=grid_y.get(gy2),
        level=level,
        z=levels.get(level),
        load_profile=load_profile,
    )


def subtract_rectangular_void(rectangle, void):
    x1, x2, y1, y2 = rectangle
    vx1, vx2, vy1, vy2 = void
    ix1 = max(x1, vx1)
    ix2 = min(x2, vx2)
    iy1 = max(y1, vy1)
    iy2 = min(y2, vy2)

    if ix1 >= ix2 or iy1 >= iy2:
        return [rectangle]

    pieces = []
    if x1 < ix1:
        pieces.append((x1, ix1, y1, y2))
    if ix2 < x2:
        pieces.append((ix2, x2, y1, y2))
    if y1 < iy1:
        pieces.append((ix1, ix2, y1, iy1))
    if iy2 < y2:
        pieces.append((ix1, ix2, iy2, y2))

    return [piece for piece in pieces if piece[0] < piece[1] and piece[2] < piece[3]]


def split_diaphragm_by_voids(diaphragm, voids):
    pieces = [(diaphragm.x1, diaphragm.x2, diaphragm.y1, diaphragm.y2)]
    for void in voids:
        next_pieces = []
        for piece in pieces:
            next_pieces.extend(subtract_rectangular_void(piece, void))
        pieces = next_pieces

    if len(pieces) == 1 and pieces[0] == (diaphragm.x1, diaphragm.x2, diaphragm.y1, diaphragm.y2):
        return [diaphragm]

    split_diaphragms = []
    for index, (x1, x2, y1, y2) in enumerate(pieces, start=1):
        split_diaphragms.append(RigidDiaphragm(
            id=f"{diaphragm.id}_{index}",
            grid_x1=diaphragm.grid_x1,
            grid_x2=diaphragm.grid_x2,
            grid_y1=diaphragm.grid_y1,
            grid_y2=diaphragm.grid_y2,
            x1=x1,
            x2=x2,
            y1=y1,
            y2=y2,
            level=diaphragm.level,
            z=diaphragm.z,
            load_profile=diaphragm.load_profile,
            status=diaphragm.status,
        ))
    return split_diaphragms


def diaphragm_edge_areas(dx, dy):
    total_area = dx * dy
    short_side = min(dx, dy)
    long_side = max(dx, dy)
    ratio = long_side / short_side if short_side > 0 else 0.0
    areas = {"bottom": 0.0, "right": 0.0, "top": 0.0, "left": 0.0}

    if ratio > 2.0:
        if dx >= dy:
            areas["bottom"] = total_area / 2.0
            areas["top"] = total_area / 2.0
        else:
            areas["left"] = total_area / 2.0
            areas["right"] = total_area / 2.0
    elif dx <= dy:
        short_edge_area = dx * dx / 4.0
        long_edge_area = total_area / 2.0 - short_edge_area
        areas["bottom"] = short_edge_area
        areas["top"] = short_edge_area
        areas["left"] = long_edge_area
        areas["right"] = long_edge_area
    else:
        short_edge_area = dy * dy / 4.0
        long_edge_area = total_area / 2.0 - short_edge_area
        areas["left"] = short_edge_area
        areas["right"] = short_edge_area
        areas["bottom"] = long_edge_area
        areas["top"] = long_edge_area

    return ratio, areas


def find_beam_for_edge(beams, node_map, level, p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    edge_horizontal = abs(y1 - y2) <= GEOMETRY_TOLERANCE
    edge_vertical = abs(x1 - x2) <= GEOMETRY_TOLERANCE
    if not edge_horizontal and not edge_vertical:
        return None

    for beam in beams:
        if beam.level != level:
            continue
        ni = node_map.get(beam.node_i)
        nj = node_map.get(beam.node_j)
        if ni is None or nj is None or None in [ni.x, ni.y, nj.x, nj.y]:
            continue

        if edge_horizontal:
            if abs(ni.y - y1) > GEOMETRY_TOLERANCE or abs(nj.y - y1) > GEOMETRY_TOLERANCE:
                continue
            beam_x_min, beam_x_max = sorted([ni.x, nj.x])
            edge_x_min, edge_x_max = sorted([x1, x2])
            if beam_x_min <= edge_x_min + GEOMETRY_TOLERANCE and beam_x_max >= edge_x_max - GEOMETRY_TOLERANCE:
                return beam.id

        if edge_vertical:
            if abs(ni.x - x1) > GEOMETRY_TOLERANCE or abs(nj.x - x1) > GEOMETRY_TOLERANCE:
                continue
            beam_y_min, beam_y_max = sorted([ni.y, nj.y])
            edge_y_min, edge_y_max = sorted([y1, y2])
            if beam_y_min <= edge_y_min + GEOMETRY_TOLERANCE and beam_y_max >= edge_y_max - GEOMETRY_TOLERANCE:
                return beam.id

    return None


def compute_tributary_loads(rigid_diaphragms, beams, nodes):
    pp_losa_kg_m2 = LOAD_SLAB_THICKNESS * CONCRETE_UNIT_WEIGHT_KG_M3
    load_profiles = {
        "FLOOR": {
            "description": "Cielo 1 subterraneo a cielo piso 3",
            "D": {"q_kg_m2": pp_losa_kg_m2 + ADDITIONAL_DEAD_LOAD_KG_M2},
            "L": {"q_kg_m2": LIVE_LOAD_KG_M2},
        },
        "ROOF": {
            "description": "Cielo piso 4 general",
            "D": {"q_kg_m2": pp_losa_kg_m2 + ROOF_ADDITIONAL_DEAD_LOAD_KG_M2},
            "L": {"q_kg_m2": ROOF_LIVE_LOAD_KG_M2},
        },
        "ELEVATOR_ROOF": {
            "description": "Cielo piso 4 zona ascensor",
            "D": {"q_kg_m2": pp_losa_kg_m2 + ELEVATOR_ROOF_ADDITIONAL_DEAD_LOAD_KG_M2},
            "L": {"q_kg_m2": ELEVATOR_ROOF_LIVE_LOAD_KG_M2},
        },
    }
    for profile in load_profiles.values():
        for case in ["D", "L"]:
            profile[case]["q_kN_m2"] = profile[case]["q_kg_m2"] * KGF_M2_TO_KN_M2

    combinations = {}
    for profile_id, profile in load_profiles.items():
        combinations[profile_id] = {}
        for combo_id, factors in LOAD_COMBINATIONS.items():
            combinations[profile_id][combo_id] = {
                "factors": factors,
                "q_kN_m2": factors["D"] * profile["D"]["q_kN_m2"] + factors["L"] * profile["L"]["q_kN_m2"],
            }

    node_map = {node.id: node for node in nodes}
    tributary_areas = []
    beam_tributary_loads = {}
    checks_by_level = {}

    for diaphragm in rigid_diaphragms:
        if diaphragm.level not in LOADED_DIAPHRAGM_LEVELS:
            continue
        x_min, x_max = sorted([diaphragm.x1, diaphragm.x2])
        y_min, y_max = sorted([diaphragm.y1, diaphragm.y2])
        dx = x_max - x_min
        dy = y_max - y_min
        if dx <= 0 or dy <= 0:
            continue
        panel_area = dx * dy
        profile_id = diaphragm.load_profile
        profile = load_profiles[profile_id]
        ratio, edge_areas = diaphragm_edge_areas(dx, dy)
        action = "ONE_WAY" if ratio > 2.0 else "TWO_WAY"
        edges = {
            "bottom": ((x_min, y_min), (x_max, y_min), dx),
            "right": ((x_max, y_min), (x_max, y_max), dy),
            "top": ((x_max, y_max), (x_min, y_max), dx),
            "left": ((x_min, y_max), (x_min, y_min), dy),
        }
        level_check = checks_by_level.setdefault(diaphragm.level, {"panel_area_m2": 0.0, "tributary_area_m2": 0.0, "D_kN": 0.0, "L_kN": 0.0, "D_expected_kN": 0.0, "L_expected_kN": 0.0})
        level_check["panel_area_m2"] += panel_area
        level_check["D_expected_kN"] += panel_area * profile["D"]["q_kN_m2"]
        level_check["L_expected_kN"] += panel_area * profile["L"]["q_kN_m2"]

        for side, area in edge_areas.items():
            p1, p2, edge_length = edges[side]
            beam_id = find_beam_for_edge(beams, node_map, diaphragm.level, p1, p2)
            loads = {case_id: profile[case_id]["q_kN_m2"] * area for case_id in ["D", "L"]}
            combo_loads = {combo_id: combo["q_kN_m2"] * area for combo_id, combo in combinations[profile_id].items()}
            entry = {
                "diaphragm_id": diaphragm.id,
                "level": diaphragm.level,
                "load_profile": profile_id,
                "side": side,
                "action": action,
                "ratio_b_over_a": ratio,
                "panel_area_m2": panel_area,
                "tributary_area_m2": area,
                "edge_length_m": edge_length,
                "beam_id": beam_id,
                "loads_kN": loads,
                "load_combinations_kN": combo_loads,
                "line_loads_kN_m": {case_id: load / edge_length if edge_length > 0 else 0.0 for case_id, load in loads.items()},
                "combination_line_loads_kN_m": {combo_id: load / edge_length if edge_length > 0 else 0.0 for combo_id, load in combo_loads.items()},
            }
            tributary_areas.append(entry)
            level_check["tributary_area_m2"] += area
            level_check["D_kN"] += loads["D"]
            level_check["L_kN"] += loads["L"]

            if beam_id is None or area <= 0:
                continue
            beam_entry = beam_tributary_loads.setdefault(beam_id, {
                "beam_id": beam_id,
                "tributary_area_m2": 0.0,
                "loads_kN": {"D": 0.0, "L": 0.0},
                "load_combinations_kN": {combo_id: 0.0 for combo_id in LOAD_COMBINATIONS},
                "source_edges": [],
            })
            beam_entry["tributary_area_m2"] += area
            beam_entry["loads_kN"]["D"] += loads["D"]
            beam_entry["loads_kN"]["L"] += loads["L"]
            for combo_id, load in combo_loads.items():
                beam_entry["load_combinations_kN"][combo_id] += load
            beam_entry["source_edges"].append({"diaphragm_id": diaphragm.id, "side": side, "tributary_area_m2": area})

    for level, check in checks_by_level.items():
        check["area_error_m2"] = check["tributary_area_m2"] - check["panel_area_m2"]
        check["D_error_kN"] = check["D_kN"] - check["D_expected_kN"]
        check["L_error_kN"] = check["L_kN"] - check["L_expected_kN"]

    return {
        "load_cases": load_profiles,
        "load_combinations": combinations,
        "tributary_areas": tributary_areas,
        "beam_tributary_loads": list(beam_tributary_loads.values()),
        "checks_by_level": checks_by_level,
    }


def create_geometry():
    refresh_grids()

    nodes = []
    columns = []
    beams = []
    slabs = []
    rigid_diaphragms = []
    foundations = []
    foundation_beams = []
    walls = []
    radiers = []
    stairs = []
    stair_walls = []

    node_registry = {}
    next_node_index_by_level = {level: 1 for level in levels}

    def get_or_create_node(gx, gy, level):
        key = (gx, gy, level)
        if key in node_registry:
            return node_registry[key]

        node_id = LEVEL_NODE_BASE[level] + next_node_index_by_level[level]
        next_node_index_by_level[level] += 1
        node = structural_node(node_id, gx, gy, level)
        nodes.append(node)
        node_registry[key] = node_id
        return node_id

    position_to_nodes = {}

    for idx, (position_id, gx, gy) in enumerate(STRUCTURAL_POSITIONS, start=1):
        position_to_nodes[position_id] = {}

        for level in VERTICAL_LEVEL_SEQUENCE:
            position_to_nodes[position_id][level] = get_or_create_node(gx, gy, level)

        n_foundation = structural_node(position_to_nodes[position_id]["FOUNDATION"], gx, gy, "FOUNDATION")
        for level_index, (bottom_level, top_level) in enumerate(zip(VERTICAL_LEVEL_SEQUENCE, VERTICAL_LEVEL_SEQUENCE[1:]), start=1):
            columns.append(Column(
                id=f"C{level_index}{idx:03d}",
                grid_x=gx,
                grid_y=gy,
                x_center=n_foundation.x,
                y_center=n_foundation.y,
                bx=COLUMN_BX,
                by=COLUMN_BY,
                z_bottom=levels[bottom_level],
                z_top=levels[top_level],
                node_i=position_to_nodes[position_id][bottom_level],
                node_j=position_to_nodes[position_id][top_level],
                status="ACTIVE",
            ))

    # Nodes for the exterior extension. Their future stair/radier elements are
    # intentionally not invented until dimensions and connectivity are supplied.
    for gx in EXTERIOR_NODE_X_AXES:
        for gy in EXTERIOR_NODE_Y_AXES:
            for level in VERTICAL_LEVEL_SEQUENCE:
                get_or_create_node(gx, gy, level)

    def split_beam_spec(gx1, gy1, gx2, gy2):
        """Return sub-specs (gx1, gy1, gx2, gy2) contiguous between columns.

        A beam that runs over an intermediate column grid position is split so
        that every segment starts and ends at a structural position, matching
        the column grid line, producing one beam per span between columns.
        """
        if gx1 == gx2:
            axis_grid = gx1
            intermediates = []
            for pos_id, pgx, pgy in STRUCTURAL_POSITIONS:
                if pgx != axis_grid:
                    continue
                if pgy in (gy1, gy2):
                    continue
                intermediates.append(pgy)
            axis_1, axis_2 = gy1, gy2
            def key_of(pgy):
                return grid_y[pgy]
        elif gy1 == gy2:
            axis_grid = gy1
            intermediates = []
            for pos_id, pgx, pgy in STRUCTURAL_POSITIONS:
                if pgy != axis_grid:
                    continue
                if pgx in (gx1, gx2):
                    continue
                intermediates.append(pgx)
            axis_1, axis_2 = gx1, gx2
            def key_of(pgx):
                return grid_x[pgx]
        else:
            return [(gx1, gy1, gx2, gy2)]

        v1, v2 = key_of(axis_1), key_of(axis_2)
        lo, hi = min(v1, v2), max(v1, v2)

        def strictly_between(name):
            value = key_of(name)
            return lo < value < hi

        intermediates = [g for g in intermediates if strictly_between(g)]
        if not intermediates:
            return [(gx1, gy1, gx2, gy2)]

        anchors = [axis_1] + sorted(intermediates, key=key_of) + [axis_2]
        if gx1 == gx2:
            return [(axis_grid, a, axis_grid, b) for a, b in zip(anchors, anchors[1:])]
        return [(a, axis_grid, b, axis_grid) for a, b in zip(anchors, anchors[1:])]

    beam_id = 3001
    for level in FLOOR_BEAM_LEVELS:
        for gx1, gy1, gx2, gy2, width, height, section_name in SUPERSTRUCTURE_BEAM_SPECS:
            for sgx1, sgy1, sgx2, sgy2 in split_beam_spec(gx1, gy1, gx2, gy2):
                beams.append(Beam(
                    id=f"B{beam_id}_{section_name}",
                    node_i=get_or_create_node(sgx1, sgy1, level),
                    node_j=get_or_create_node(sgx2, sgy2, level),
                    width=width,
                    height=height,
                    level=level,
                    status="ACTIVE",
                ))
                beam_id += 1

    for level in DIAPHRAGM_LEVELS:
        diaphragm_index = 1
        level_voids = []
        if level == "CIELO_4":
            for void in CIELO_4_DIAPHRAGM_VOIDS:
                vx1 = grid_x[void["origin_grid_x"]] + void["offset_x"]
                vy1 = grid_y[void["origin_grid_y"]] + void["offset_y"]
                level_voids.append((vx1, vx1 + void["width_x"], vy1, vy1 + void["length_y"]))
        for row_index, (gy1, gy2) in enumerate(zip(DIAPHRAGM_GRID_Y_AXIS_NAMES, DIAPHRAGM_GRID_Y_AXIS_NAMES[1:]), start=1):
            for col_index, (gx1, gx2) in enumerate(zip(DIAPHRAGM_GRID_X_AXIS_NAMES, DIAPHRAGM_GRID_X_AXIS_NAMES[1:]), start=1):
                if level != "CIELO_4" and (gx1, gx2, gy1, gy2) in ELEVATOR_DIAPHRAGM_VOID_PANELS:
                    continue
                diaphragm_number = f"{DIAPHRAGM_LEVEL_PREFIX[level]}{diaphragm_index:02d}"
                diaphragm = create_diaphragm(diaphragm_number, level, gx1, gx2, gy1, gy2)
                rigid_diaphragms.extend(split_diaphragm_by_voids(diaphragm, level_voids))
                diaphragm_index += 1

    for beam_id, gx1, gy1, gx2, gy2, width, height in FOUNDATION_BEAM_SPECS:
        foundation_beams.append(FoundationBeam(
            id=beam_id,
            node_i=get_or_create_node(gx1, gy1, "FOUNDATION"),
            node_j=get_or_create_node(gx2, gy2, "FOUNDATION"),
            width=width,
            height=height,
            z=levels["FOUNDATION"],
            status="ACTIVE",
        ))

    d_x = grid_x.get("D")
    d_prime_x = grid_x.get("D_PRIME")
    a_prime_x = grid_x.get("A_PRIME")
    c_prime_x = grid_x.get("C_PRIME")
    y_1 = grid_y.get("1")
    y_1a_prime = grid_y.get("1A_PRIME")
    y_3 = grid_y.get("3")

    if None not in [d_prime_x, c_prime_x]:
        elevator_wall_end_y = ELEVATOR_TOP_WALL_Y + ELEVATOR_WALL_LENGTH
        add_wall_for_each_storey(walls, "W_DPRIME_ELEVATOR_TOP_TO_CPRIME", "D_PRIME", "ELEVATOR_TOP", "C_PRIME", "ELEVATOR_TOP", d_prime_x, ELEVATOR_TOP_WALL_Y, c_prime_x, ELEVATOR_TOP_WALL_Y, 0.30)
        add_wall_for_each_storey(walls, "W_CPRIME_ELEVATOR_SIDE", "C_PRIME", "ELEVATOR_TOP", "C_PRIME", "OPENING_START_294_5CM", c_prime_x, ELEVATOR_TOP_WALL_Y, c_prime_x, elevator_wall_end_y, 0.25)
        add_wall_for_each_storey(walls, "W_DPRIME_ELEVATOR_SIDE", "D_PRIME", "ELEVATOR_TOP", "D_PRIME", "OPENING_START_294_5CM", d_prime_x, ELEVATOR_TOP_WALL_Y, d_prime_x, elevator_wall_end_y, 0.25)

    if None not in [d_prime_x, y_1, y_3]:
        opening_start_y = y_1 + D_WALL_OPENING_START_FROM_GRID_1
        opening_end_y = opening_start_y + D_WALL_OPENING_LENGTH
        add_wall_for_each_storey(walls, "W_DPRIME_1_TO_ELEVATOR_TOP", "D_PRIME", "1", "D_PRIME", "ELEVATOR_TOP", d_prime_x, y_1, d_prime_x, ELEVATOR_TOP_WALL_Y, 0.25)
        add_wall_for_each_storey(walls, "W_DPRIME_OPENING_TO_3", "D_PRIME", "OPENING_END", "D_PRIME", "3", d_prime_x, opening_end_y, d_prime_x, y_3, 0.25)

    exterior_c_x = grid_x.get("C")
    exterior_bp_x = grid_x.get("B_PRIME")
    exterior_e1_x = grid_x.get("E1")
    exterior_8b_y = grid_y.get("8B")
    exterior_8a_y = grid_y.get("8A")
    if None not in [exterior_c_x, exterior_bp_x, exterior_e1_x, exterior_8b_y, exterior_8a_y]:
        exterior_wall_end_x = exterior_c_x - 1.22
        foundation_wall_specs = [
            ("FW_E1_8B_TO_C_PLUS_122", exterior_e1_x, exterior_8b_y, exterior_wall_end_x, exterior_8b_y),
            ("FW_E1_8B_TO_8A", exterior_e1_x, exterior_8b_y, exterior_e1_x, exterior_8a_y),
            ("FW_E1_8A_TO_C_PLUS_122", exterior_e1_x, exterior_8a_y, exterior_wall_end_x, exterior_8a_y),
            ("FW_BPRIME_8B_TO_8A", exterior_bp_x, exterior_8b_y, exterior_bp_x, exterior_8a_y),
        ]
        for wall_id, x1, y1, x2, y2 in foundation_wall_specs:
            walls.append(StructuralWall(
                id=wall_id,
                grid_x1="EXTERIOR",
                grid_y1="EXTERIOR",
                grid_x2="EXTERIOR",
                grid_y2="EXTERIOR",
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                thickness=EXTERIOR_FOUNDATION_WALL_THICKNESS,
                z_bottom=EXTERIOR_RADIER_TOP_Z,
                z_top=None,
                status="ACTIVE_PENDING_WALL_HEIGHT",
            ))

        radiers.append(Radier(
            id="R_EXT_001",
            boundary=[
                [exterior_wall_end_x, exterior_8b_y],
                [exterior_e1_x, exterior_8b_y],
                [exterior_e1_x, exterior_8a_y],
                [exterior_wall_end_x, exterior_8a_y],
            ],
            z_top=EXTERIOR_RADIER_TOP_Z,
        ))

        stair_x1, stair_x2 = exterior_c_x, exterior_e1_x
        stair_y1 = (exterior_8a_y + exterior_8b_y) / 2
        stair_y2 = stair_y1
        total_plan_run = stair_x2 - stair_x1
        final_run = total_plan_run - STAIR_FIRST_RUN - STAIR_LANDING_RUN
        first_stair_base_z = EXTERIOR_RADIER_TOP_Z

        def point_at(distance):
            ratio = distance / total_plan_run
            return stair_x1 + (stair_x2 - stair_x1) * ratio, stair_y1 + (stair_y2 - stair_y1) * ratio

        p0 = point_at(0.0)
        p1 = point_at(STAIR_FIRST_RUN)
        p2 = point_at(STAIR_FIRST_RUN + STAIR_LANDING_RUN)
        p3 = point_at(total_plan_run)
        base_segments = [
            ("EXTENSION", stair_x1 - STAIR_ENTRY_EXTENSION, stair_x1, 0.0, 0.0, 0.0),
            ("TRAMO_1", p0[0], p1[0], 0.0, STAIR_FIRST_RUN * STAIR_FIRST_SLOPE, STAIR_FIRST_SLOPE),
            ("DESCANSO", p1[0], p2[0], STAIR_FIRST_RUN * STAIR_FIRST_SLOPE, STAIR_FIRST_RUN * STAIR_FIRST_SLOPE, 0.0),
            ("TRAMO_2", p2[0], p3[0], STAIR_FIRST_RUN * STAIR_FIRST_SLOPE, STAIR_FIRST_RUN * STAIR_FIRST_SLOPE + final_run * STAIR_SECOND_SLOPE, STAIR_SECOND_SLOPE),
        ]
        for storey_index, storey_base_z in enumerate([first_stair_base_z + index * FLOOR_HEIGHT for index in range(4)], start=1):
            storey_segments = []
            for segment_id, x_start, x_end, rise_start, rise_end, slope in base_segments:
                segment = {
                    "id": f"L{storey_index}_{segment_id}",
                    "x1": x_start,
                    "y1": stair_y1,
                    "x2": x_end,
                    "y2": stair_y1,
                    "z1": storey_base_z + rise_start,
                    "z2": storey_base_z + rise_end,
                    "slope": slope,
                }
                if segment_id == "DESCANSO":
                    segment["obra_gruesa"] = storey_base_z + rise_start
                storey_segments.append(segment)
            stairs.append(Stair(
                id=f"ESC_EXT_{storey_index:03d}",
                x1=stair_x1,
                y1=stair_y1,
                x2=stair_x2,
                y2=stair_y2,
                width=STAIR_WIDTH,
                thickness=STAIR_THICKNESS,
                segments=storey_segments,
            ))
            for side, y_side in [("8B", exterior_8b_y), ("8A", exterior_8a_y)]:
                for segment in storey_segments:
                    wall_z1 = storey_base_z + (STAIR_LANDING_WALL_TOP_Z - EXTERIOR_RADIER_TOP_Z) if segment["id"].endswith("DESCANSO") else segment["z1"]
                    wall_z2 = wall_z1 if segment["id"].endswith("DESCANSO") else segment["z2"]
                    stair_walls.append(StairWall(
                        id=f"MW_{storey_index}_{side}_{segment['id']}",
                        side=side,
                        x1=segment["x1"],
                        y1=y_side,
                        z1=wall_z1,
                        x2=segment["x2"],
                        y2=y_side,
                        z2=wall_z2,
                        thickness=EXTERIOR_FOUNDATION_WALL_THICKNESS,
                        top_level="-5.15 m" if segment["id"].endswith("DESCANSO") else "VAR",
                    ))

    if None not in [a_prime_x, y_1]:
        add_wall_for_each_storey(walls, "W_APRIME_1_VERTICAL", "A_PRIME", "A1_DOWN", "A_PRIME", "A1_UP", a_prime_x, y_1 - AP1_VERTICAL_WALL_DOWN, a_prime_x, y_1 + AP1_VERTICAL_WALL_UP, AP1_VERTICAL_WALL_THICKNESS)
        add_wall_for_each_storey(walls, "W_APRIME_1_HORIZONTAL", "A_PRIME", "1", "A1_ARM", "1", a_prime_x, y_1, a_prime_x + AP1_HORIZONTAL_WALL_LENGTH, y_1, AP1_HORIZONTAL_WALL_THICKNESS)

    if None not in [a_prime_x, y_3]:
        add_wall_for_each_storey(walls, "W_APRIME_3_VERTICAL", "A_PRIME", "A3_DOWN", "A_PRIME", "A3_UP", a_prime_x, y_3 - AP3_VERTICAL_WALL_DOWN, a_prime_x, y_3 + AP3_VERTICAL_WALL_UP, AP3_VERTICAL_WALL_THICKNESS)
        add_wall_for_each_storey(walls, "W_APRIME_3_HORIZONTAL", "A_PRIME", "3", "A3_ARM", "3", a_prime_x, y_3, a_prime_x + AP3_HORIZONTAL_WALL_LENGTH, y_3, AP3_HORIZONTAL_WALL_THICKNESS)

    radiers.append(Radier(id="R001", boundary=[], z_top=levels["FOUNDATION"]))

    supports = []
    for node in nodes:
        if node.level != "FOUNDATION" or None in [node.x, node.y, node.z]:
            continue
        supports.append({
            "node": node.id,
            "type": "fixed",
            "ux": 1,
            "uy": 1,
            "uz": 1,
            "rx": 1,
            "ry": 1,
            "rz": 1,
        })

    tributary_load_data = compute_tributary_loads(rigid_diaphragms, beams, nodes)

    return {
        "metadata": {
            "name": "UANDES Structural Model",
            "units": {"length": "m", "force": "kN"},
            "geometry_tolerance": GEOMETRY_TOLERANCE,
            "note": "Geometry is parametric. Missing dimensions are kept as null and are not invented.",
            "diaphragm_note": "Rigid diaphragms replace slab panels. No finite-element slabs are generated.",
            "diaphragm_12_void_note": "The panel between A'-A and 1A'-2A' is shortened by 1.50 m from axis A' on every diaphragm level.",
            "tributary_load_note": "Loads are assigned from rigid diaphragm panel tributary areas, not from finite-element slabs.",
            "exterior_extension_note": "Exterior radier and foundation walls are modeled; staircase dimensions remain pending.",
            "plant_levels": {
                "FOUNDATION": "Planta de fundaciones",
                "CIELO_1S": "Planta cielo 1 subterraneo",
                "CIELO_1": "Planta cielo piso 1",
                "CIELO_2": "Planta cielo piso 2",
                "CIELO_3": "Planta cielo piso 3",
                "CIELO_4": "Planta cielo piso 4",
            },
        },
        "levels": levels,
        "grids": {"x": grid_x, "y": grid_y},
        "constants": {
            "foundation_heights": FOUNDATION_HEIGHTS,
            "radier_thickness": RADIER_THICKNESS,
            "diaphragm_display_thickness": DIAPHRAGM_DISPLAY_THICKNESS,
            "load_slab_thickness": LOAD_SLAB_THICKNESS,
            "concrete_unit_weight_kg_m3": CONCRETE_UNIT_WEIGHT_KG_M3,
            "additional_dead_load_kg_m2": ADDITIONAL_DEAD_LOAD_KG_M2,
            "live_load_kg_m2": LIVE_LOAD_KG_M2,
            "roof_additional_dead_load_kg_m2": ROOF_ADDITIONAL_DEAD_LOAD_KG_M2,
            "roof_live_load_kg_m2": ROOF_LIVE_LOAD_KG_M2,
            "elevator_roof_additional_dead_load_kg_m2": ELEVATOR_ROOF_ADDITIONAL_DEAD_LOAD_KG_M2,
            "elevator_roof_live_load_kg_m2": ELEVATOR_ROOF_LIVE_LOAD_KG_M2,
            "loaded_diaphragm_levels": LOADED_DIAPHRAGM_LEVELS,
            "stair_width": STAIR_WIDTH,
            "stair_thickness": STAIR_THICKNESS,
        },
        "materials": MATERIALS,
        "sections": SECTIONS,
        "nodes": to_dict_list(nodes),
        "columns": to_dict_list(columns),
        "beams": to_dict_list(beams),
        "slabs": to_dict_list(slabs),
        "rigid_diaphragms": to_dict_list(rigid_diaphragms),
        "walls": to_dict_list(walls),
        "foundations": to_dict_list(foundations),
        "foundation_beams": to_dict_list(foundation_beams),
        "radiers": to_dict_list(radiers),
        "stairs": to_dict_list(stairs),
        "stair_walls": to_dict_list(stair_walls),
        "supports": supports,
        "loads": tributary_load_data["load_cases"],
        "load_combinations": tributary_load_data["load_combinations"],
        "tributary_areas": tributary_load_data["tributary_areas"],
        "beam_tributary_loads": tributary_load_data["beam_tributary_loads"],
        "tributary_checks": tributary_load_data["checks_by_level"],
    }
