from dataclasses import asdict, dataclass
from dataclasses import field
from typing import Optional


@dataclass
class Node:
    id: int
    grid_x: str
    grid_y: str
    level: str
    x: Optional[float]
    y: Optional[float]
    z: Optional[float]
    type: str = "NODE"


@dataclass
class Column:
    id: str
    grid_x: str
    grid_y: str
    x_center: Optional[float]
    y_center: Optional[float]
    bx: Optional[float]
    by: Optional[float]
    z_bottom: Optional[float]
    z_top: Optional[float]
    node_i: int
    node_j: int
    status: str = "PENDING_DIMENSIONS"
    type: str = "COLUMN"


@dataclass
class Beam:
    id: str
    node_i: int
    node_j: int
    width: Optional[float]
    height: Optional[float]
    level: str
    status: str = "PENDING_DIMENSIONS"
    type: str = "BEAM"


@dataclass
class Slab:
    id: str
    grid_x1: str
    grid_x2: str
    grid_y1: str
    grid_y2: str
    x1: Optional[float]
    x2: Optional[float]
    y1: Optional[float]
    y2: Optional[float]
    thickness: Optional[float]
    level: str
    z_top: Optional[float]
    reinforcement: list = field(default_factory=list)
    status: str = "ACTIVE"
    type: str = "SLAB"


@dataclass
class RigidDiaphragm:
    id: str
    grid_x1: str
    grid_x2: str
    grid_y1: str
    grid_y2: str
    x1: Optional[float]
    x2: Optional[float]
    y1: Optional[float]
    y2: Optional[float]
    level: str
    z: Optional[float]
    load_profile: str = "FLOOR"
    status: str = "ACTIVE"
    type: str = "RIGID_DIAPHRAGM"


@dataclass
class Stair:
    id: str
    x1: Optional[float]
    y1: Optional[float]
    x2: Optional[float]
    y2: Optional[float]
    width: Optional[float]
    thickness: Optional[float]
    segments: list
    status: str = "ACTIVE"
    type: str = "STAIR"


@dataclass
class StairWall:
    id: str
    side: str
    x1: Optional[float]
    y1: Optional[float]
    z1: Optional[float]
    x2: Optional[float]
    y2: Optional[float]
    z2: Optional[float]
    thickness: Optional[float]
    top_level: str
    status: str = "ACTIVE"
    type: str = "STAIR_SIDE_WALL"


@dataclass
class StructuralWall:
    id: str
    grid_x1: str
    grid_y1: str
    grid_x2: str
    grid_y2: str
    x1: Optional[float]
    y1: Optional[float]
    x2: Optional[float]
    y2: Optional[float]
    thickness: Optional[float]
    z_bottom: Optional[float]
    z_top: Optional[float]
    status: str = "PENDING_DIMENSIONS"
    type: str = "STRUCTURAL_WALL"


@dataclass
class Foundation:
    id: str
    type: str
    center_x: Optional[float]
    center_y: Optional[float]
    width: Optional[float]
    length: Optional[float]
    thickness: Optional[float]
    level: str
    supporting_element: str
    status: str = "PENDING_DIMENSIONS"
    boundary: list = field(default_factory=list)


@dataclass
class FoundationBeam:
    id: str
    node_i: int
    node_j: int
    width: Optional[float]
    height: Optional[float]
    z: Optional[float]
    status: str = "PENDING_DIMENSIONS"
    type: str = "FOUNDATION_BEAM"


@dataclass
class Radier:
    id: str
    boundary: list
    z_top: Optional[float]
    thickness: float = 0.15
    type: str = "RADIER"


def to_dict_list(items):
    return [asdict(item) for item in items]
