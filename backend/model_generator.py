"""
model_generator.py — Stage 3: 2D→3D Geometry Segmentation

Converts 2D parsed geometry into pre-segmented 3D mesh descriptors
that can be directly rendered by Three.js BoxGeometry.

KEY DESIGN DECISION: No CSG in the browser.
Walls with openings (doors/windows) are pre-split into solid box segments
on the backend, so the frontend just renders boxes — no boolean subtraction.
"""

import math
from typing import List, Dict, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WALL_HEIGHT_M = 3.0
WALL_THICKNESS_M = 0.23       # 230mm standard brick wall
FLOOR_THICKNESS_M = 0.15      # 150mm RCC slab
COLUMN_SIZE_M = 0.3            # 300mm square column
COLUMN_HEIGHT_M = WALL_HEIGHT_M

COLORS = {
    "load-bearing": "#2563eb",   # Blue
    "partition":    "#10b981",   # Green
    "floor":        "#94a3b8",   # Slate
    "column":       "#f59e0b",   # Amber
    "header":       "#6366f1",   # Indigo (above doors/windows)
    "sill":         "#8b5cf6",   # Violet (below windows)
}


# ---------------------------------------------------------------------------
# Mesh creation helpers
# ---------------------------------------------------------------------------
def _create_box_mesh(
    center_x: float, center_y: float, center_z: float,
    width: float, height: float, depth: float,
    color: str, wall_id: str = "", wall_type: str = "",
    segment_type: str = "solid", element_type: str = "wall",
) -> dict:
    """Create a single box mesh descriptor for Three.js."""
    return {
        "type": "box",
        "position": [round(center_x, 3), round(center_y, 3), round(center_z, 3)],
        "dimensions": [round(max(width, 0.01), 3),
                       round(max(height, 0.01), 3),
                       round(max(depth, 0.01), 3)],
        "color": color,
        "wall_id": wall_id,
        "wall_type": wall_type,
        "segment_type": segment_type,
        "element_type": element_type,
    }


def _wall_mesh_from_px(
    x1_px: float, y1_px: float, x2_px: float, y2_px: float,
    orientation: str, scale: float,
    base_m: float, height_m: float,
    color: str, wall_id: str, wall_type: str,
    segment_type: str = "solid",
) -> Optional[dict]:
    """Convert pixel-space wall segment to 3D box mesh in meters."""
    x1_m = x1_px / scale
    y1_m = y1_px / scale
    x2_m = x2_px / scale
    y2_m = y2_px / scale

    if orientation == "horizontal":
        length = abs(x2_m - x1_m)
        if length < 0.01:
            return None
        center_x = (x1_m + x2_m) / 2
        center_z = (y1_m + y2_m) / 2
        w = length
        d = WALL_THICKNESS_M
    else:  # vertical
        length = abs(y2_m - y1_m)
        if length < 0.01:
            return None
        center_x = (x1_m + x2_m) / 2
        center_z = (y1_m + y2_m) / 2
        w = WALL_THICKNESS_M
        d = length

    center_y = base_m + height_m / 2

    return _create_box_mesh(
        center_x, center_y, center_z,
        w, height_m, d,
        color, wall_id, wall_type, segment_type,
    )


# ---------------------------------------------------------------------------
# Opening segmentation (the CSG-free approach)
# ---------------------------------------------------------------------------
def _split_wall_at_openings(
    wall: dict, openings: list, scale: float,
    color: str, wall_type: str,
) -> List[dict]:
    """
    Split a wall with openings into solid box segments.

    For a wall with a door:
      ┌──────┐  ┌──────┐   ← header segment (above door)
      │      │  │      │
      │ left │  │right │   ← left & right segments (full height)
      │      │  │      │
      └──────┘  └──────┘

    For a wall with a window:
      ┌──────┐  ┌──────┐
      │      │  │      │
      │ left │  │right │   ← left & right segments (full height)
      │      ├──┤      │   ← header above window
      │      │  │      │   ← window gap
      │      ├──┤      │   ← sill below window
      └──────┘  └──────┘
    """
    meshes = []
    wid = wall["id"]
    orient = wall["orientation"]
    x1, y1 = wall["start"]
    x2, y2 = wall["end"]

    # Determine the primary axis range
    if orient == "horizontal":
        axis_start = min(x1, x2)
        axis_end = max(x1, x2)
        fixed_coord = (y1 + y2) / 2
    else:
        axis_start = min(y1, y2)
        axis_end = max(y1, y2)
        fixed_coord = (x1 + x2) / 2

    # Sort openings along the wall axis
    sorted_ops = sorted(openings, key=lambda o: (
        o["position"][0] if orient == "horizontal" else o["position"][1]
    ))

    # Build solid segments between/around openings
    current_pos = axis_start

    for op in sorted_ops:
        op_center = op["position"][0] if orient == "horizontal" else op["position"][1]
        op_half_w = op.get("width_px", 40) / 2
        op_start = op_center - op_half_w
        op_end = op_center + op_half_w

        op_height_m = op.get("height_m", 2.1)
        op_sill_m = op.get("sill_m", 0.0)
        op_type = op.get("type", "door")

        # Segment: wall from current_pos to opening start (full height)
        if op_start > current_pos + 2:  # need at least ~2px to be meaningful
            if orient == "horizontal":
                m = _wall_mesh_from_px(
                    current_pos, fixed_coord, op_start, fixed_coord,
                    orient, scale, 0, WALL_HEIGHT_M, color, wid, wall_type, "left"
                )
            else:
                m = _wall_mesh_from_px(
                    fixed_coord, current_pos, fixed_coord, op_start,
                    orient, scale, 0, WALL_HEIGHT_M, color, wid, wall_type, "bottom"
                )
            if m:
                meshes.append(m)

        # Header above opening
        header_base = op_sill_m + op_height_m
        header_height = WALL_HEIGHT_M - header_base
        if header_height > 0.05:
            if orient == "horizontal":
                m = _wall_mesh_from_px(
                    op_start, fixed_coord, op_end, fixed_coord,
                    orient, scale, header_base, header_height,
                    COLORS["header"], wid, wall_type, "header"
                )
            else:
                m = _wall_mesh_from_px(
                    fixed_coord, op_start, fixed_coord, op_end,
                    orient, scale, header_base, header_height,
                    COLORS["header"], wid, wall_type, "header"
                )
            if m:
                meshes.append(m)

        # Sill below window (only for windows)
        if op_type == "window" and op_sill_m > 0.05:
            if orient == "horizontal":
                m = _wall_mesh_from_px(
                    op_start, fixed_coord, op_end, fixed_coord,
                    orient, scale, 0, op_sill_m,
                    COLORS["sill"], wid, wall_type, "sill"
                )
            else:
                m = _wall_mesh_from_px(
                    fixed_coord, op_start, fixed_coord, op_end,
                    orient, scale, 0, op_sill_m,
                    COLORS["sill"], wid, wall_type, "sill"
                )
            if m:
                meshes.append(m)

        current_pos = op_end

    # Final segment: from last opening end to wall end (full height)
    if axis_end > current_pos + 2:
        if orient == "horizontal":
            m = _wall_mesh_from_px(
                current_pos, fixed_coord, axis_end, fixed_coord,
                orient, scale, 0, WALL_HEIGHT_M, color, wid, wall_type, "right"
            )
        else:
            m = _wall_mesh_from_px(
                fixed_coord, current_pos, fixed_coord, axis_end,
                orient, scale, 0, WALL_HEIGHT_M, color, wid, wall_type, "top"
            )
        if m:
            meshes.append(m)

    return meshes


# ---------------------------------------------------------------------------
# Floor slab & columns
# ---------------------------------------------------------------------------
def _create_floor_slab(walls: list, scale: float) -> dict:
    """Create a floor slab covering the building footprint."""
    all_x = []
    all_y = []
    for wall in walls:
        all_x.extend([wall["start"][0], wall["end"][0]])
        all_y.extend([wall["start"][1], wall["end"][1]])

    if not all_x:
        return _create_box_mesh(0, -FLOOR_THICKNESS_M / 2, 0, 1, FLOOR_THICKNESS_M, 1,
                                COLORS["floor"], element_type="floor")

    min_x, max_x = min(all_x) / scale, max(all_x) / scale
    min_z, max_z = min(all_y) / scale, max(all_y) / scale

    width = max_x - min_x
    depth = max_z - min_z
    center_x = (min_x + max_x) / 2
    center_z = (min_z + max_z) / 2

    return _create_box_mesh(
        center_x, -FLOOR_THICKNESS_M / 2, center_z,
        width + 0.2, FLOOR_THICKNESS_M, depth + 0.2,
        COLORS["floor"], element_type="floor",
        segment_type="slab",
    )


def _create_column_mesh(column: dict, scale: float) -> dict:
    """Create a column mesh at the specified position."""
    cx = column["position"][0] / scale
    cz = column["position"][1] / scale

    return _create_box_mesh(
        cx, COLUMN_HEIGHT_M / 2, cz,
        COLUMN_SIZE_M, COLUMN_HEIGHT_M, COLUMN_SIZE_M,
        COLORS["column"],
        wall_id=f"col_{column.get('room_id', 'unknown')}",
        element_type="column",
        segment_type="column",
    )


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------
def generate_3d_model(geometry_data: dict) -> dict:
    """
    Stage 3 main function: converts Stage 2 geometry into pre-segmented
    3D mesh descriptors for direct Three.js rendering.

    Args:
        geometry_data: Output from reconstruct_geometry() — contains walls,
                       rooms, openings, classified_walls, columns_required.

    Returns:
        dict with:
          - meshes: List of box mesh descriptors
          - labels: 3D positions for room labels
          - metadata: Heights, thickness, scale info
    """
    walls = geometry_data["walls"]
    rooms = geometry_data.get("rooms", [])
    openings = geometry_data.get("openings", [])
    classified = geometry_data["classified_walls"]
    columns = geometry_data.get("columns_required", [])
    scale = geometry_data.get("scale_factor", 50.0)

    # Build lookup: wall_id → classification type
    wall_types = {}
    for cw in classified:
        wall_types[cw["wall_id"]] = cw["type"]

    # Build lookup: wall_id → list of openings
    wall_openings = {}
    for op in openings:
        wid = op["wall_id"]
        if wid not in wall_openings:
            wall_openings[wid] = []
        wall_openings[wid].append(op)

    meshes = []

    # --- Generate wall meshes ---
    for wall in walls:
        wid = wall["id"]
        wtype = wall_types.get(wid, "partition")
        color = COLORS.get(wtype, COLORS["partition"])

        ops = wall_openings.get(wid, [])

        if not ops:
            # Solid wall — single box
            m = _wall_mesh_from_px(
                wall["start"][0], wall["start"][1],
                wall["end"][0], wall["end"][1],
                wall["orientation"], scale,
                0, WALL_HEIGHT_M,
                color, wid, wtype,
            )
            if m:
                meshes.append(m)
        else:
            # Wall with openings — pre-segmented (no browser CSG needed)
            segments = _split_wall_at_openings(wall, ops, scale, color, wtype)
            meshes.extend(segments)

    # --- Floor slab ---
    floor = _create_floor_slab(walls, scale)
    meshes.append(floor)

    # --- Columns ---
    for col in columns:
        m = _create_column_mesh(col, scale)
        meshes.append(m)

    # --- Room labels (for 3D text placement) ---
    labels = []
    for room in rooms:
        cx, cy = room["centroid"]
        labels.append({
            "label": room["label"],
            "position": [round(cx / scale, 3), 0.1, round(cy / scale, 3)],
            "area_m2": room["area_m2"],
        })

    return {
        "meshes": meshes,
        "labels": labels,
        "metadata": {
            "wall_height_m": WALL_HEIGHT_M,
            "wall_thickness_m": WALL_THICKNESS_M,
            "floor_thickness_m": FLOOR_THICKNESS_M,
            "scale_factor": scale,
            "total_meshes": len(meshes),
        },
    }
