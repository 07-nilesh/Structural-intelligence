"""
geometry.py — Stage 2: Geometry Reconstruction

Converts pixel-space wall segments into a structured geometric graph,
classifies every wall (load-bearing vs partition), detects spans,
and identifies where columns are required.
"""

import math
import networkx as nx
from shapely.geometry import LineString, Polygon, Point, MultiPoint
from shapely.ops import nearest_points
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Wall Graph Construction
# ---------------------------------------------------------------------------
def build_wall_graph(parsed_data: dict) -> nx.Graph:
    """
    Build a NetworkX graph from parsed wall data.

    Nodes = wall endpoints/junctions
    Edges = wall segments between nodes
    """
    G = nx.Graph()
    walls = parsed_data["walls"]
    scale = parsed_data.get("scale_factor", 50.0)

    for wall in walls:
        start = tuple(wall["start"])
        end = tuple(wall["end"])
        G.add_node(start, x=start[0], y=start[1])
        G.add_node(end, x=end[0], y=end[1])
        G.add_edge(
            start, end,
            wall_id=wall["id"],
            length_m=wall["length_m"],
            length_px=wall["length_px"],
            orientation=wall["orientation"],
        )

    return G


def detect_junctions(G: nx.Graph) -> Dict[str, list]:
    """
    Classify each node in the wall graph by its degree:
    - degree 1: endpoint (dead end)
    - degree 2: L-corner (two walls meet and turn)
    - degree 3: T-junction (three walls meet)
    - degree 4+: Crossroads
    """
    junctions = {"endpoints": [], "L_corners": [], "T_junctions": [], "crossroads": []}

    for node in G.nodes():
        deg = G.degree(node)
        if deg == 1:
            junctions["endpoints"].append(node)
        elif deg == 2:
            junctions["L_corners"].append(node)
        elif deg == 3:
            junctions["T_junctions"].append(node)
        else:
            junctions["crossroads"].append(node)

    return junctions


# ---------------------------------------------------------------------------
# Coordinate Snapping
# ---------------------------------------------------------------------------
def snap_to_grid(coordinates: list, grid_size_px: float = 5.0) -> list:
    """Round all coordinates to nearest grid_size_px to eliminate floating-point wall gaps."""
    return [[round(x / grid_size_px) * grid_size_px for x in coord]
            for coord in coordinates]


def snap_walls_to_grid(parsed_data: dict, grid_size: float = 5.0) -> dict:
    """Apply grid snapping to all wall coordinates."""
    for wall in parsed_data["walls"]:
        snapped = snap_to_grid([wall["start"], wall["end"]], grid_size)
        wall["start"] = [int(s) for s in snapped[0]]
        wall["end"] = [int(s) for s in snapped[1]]
    return parsed_data


# ---------------------------------------------------------------------------
# Wall Classification
# ---------------------------------------------------------------------------
def find_building_boundary(parsed_data: dict) -> Polygon:
    """Find the outer boundary of the building from all wall endpoints."""
    all_points = []
    for wall in parsed_data["walls"]:
        all_points.append(wall["start"])
        all_points.append(wall["end"])

    if len(all_points) < 3:
        return Polygon()

    mp = MultiPoint(all_points)
    hull = mp.convex_hull
    return hull


def is_perimeter_wall(wall: dict, boundary: Polygon, tolerance: float = 10.0) -> bool:
    """Rule 1: Check if a wall lies on the outer building boundary."""
    line = LineString([wall["start"], wall["end"]])
    boundary_line = boundary.exterior

    # Check if both endpoints are near the boundary
    start_dist = boundary_line.distance(Point(wall["start"]))
    end_dist = boundary_line.distance(Point(wall["end"]))

    return start_dist < tolerance and end_dist < tolerance


def is_structural_spine(wall: dict, all_walls: list, boundary: Polygon,
                         tolerance: float = 15.0) -> bool:
    """
    Rule 2: Check if wall is a structural spine — runs full length of
    building interior, connecting two exterior walls.
    """
    line = LineString([wall["start"], wall["end"]])
    orient = wall["orientation"]

    if orient == "horizontal":
        building_bounds = boundary.bounds  # (minx, miny, maxx, maxy)
        building_width = building_bounds[2] - building_bounds[0]
        wall_length_px = wall["length_px"]
        if wall_length_px > building_width * 0.6:
            return True
    elif orient == "vertical":
        building_bounds = boundary.bounds
        building_height = building_bounds[3] - building_bounds[1]
        wall_length_px = wall["length_px"]
        if wall_length_px > building_height * 0.6:
            return True

    return False


def has_long_span_above(wall: dict, rooms: list, scale_factor: float = 50.0,
                        threshold_m: float = 4.0) -> bool:
    """Rule 3: Check if wall supports a span > threshold.
    Only triggers for interior walls that provide mid-span support."""
    wall_line = LineString([wall["start"], wall["end"]])

    for room in rooms:
        room_poly = Polygon(room["polygon"])
        # Wall must actually border this room
        if wall_line.distance(room_poly) < 5:
            bounds = room_poly.bounds
            span_x = (bounds[2] - bounds[0])
            span_y = (bounds[3] - bounds[1])
            max_span_px = max(span_x, span_y)
            max_span_m = max_span_px / scale_factor
            # Only flag if this wall is shorter than half the span
            # (meaning it's a divider within a big room, not the room wall itself)
            if max_span_m > threshold_m and wall["length_px"] < max_span_px * 0.9:
                return True

    return False


def classify_walls(parsed_data: dict) -> list:
    """
    Classify all walls as load-bearing or partition.

    Rules (applied in order):
    1. Perimeter wall → LOAD-BEARING
    2. Structural spine (interior, full-length) → LOAD-BEARING
    3. Span support (below >4m span) → LOAD-BEARING
    4. Default → PARTITION
    """
    walls = parsed_data["walls"]
    rooms = parsed_data["rooms"]
    boundary = find_building_boundary(parsed_data)

    classified = []

    for wall in walls:
        # Rule 1: Perimeter
        if is_perimeter_wall(wall, boundary):
            classified.append({
                "wall_id": wall["id"],
                "type": "load-bearing",
                "reason": f"Perimeter wall — forms part of outer building boundary"
            })
            continue

        # Rule 2: Structural spine
        if is_structural_spine(wall, walls, boundary):
            classified.append({
                "wall_id": wall["id"],
                "type": "load-bearing",
                "reason": f"Structural spine — interior wall spanning >60% of building dimension, connects exterior walls"
            })
            continue

        # Rule 3: Span support
        sf = parsed_data.get("scale_factor", 50.0)
        if has_long_span_above(wall, rooms, scale_factor=sf):
            classified.append({
                "wall_id": wall["id"],
                "type": "load-bearing",
                "reason": f"Span support — wall provides mid-span support for room with span >4m"
            })
            continue

        # Rule 4: Default
        classified.append({
            "wall_id": wall["id"],
            "type": "partition",
            "reason": "Interior non-spanning divider — no structural load path"
        })

    return classified


# ---------------------------------------------------------------------------
# Span Detection
# ---------------------------------------------------------------------------
def detect_spans(parsed_data: dict, scale_factor: float = None) -> list:
    """
    For each room, find its longest unsupported dimension.
    Flag if > 4m (RCC) or > 5m (steel frame).
    """
    rooms = parsed_data["rooms"]
    sf = scale_factor or parsed_data.get("scale_factor", 50.0)
    concerns = []

    for room in rooms:
        poly = Polygon(room["polygon"])
        bounds = poly.bounds  # (minx, miny, maxx, maxy)

        span_x_px = bounds[2] - bounds[0]
        span_y_px = bounds[3] - bounds[1]
        max_span_px = max(span_x_px, span_y_px)
        max_span_m = round(max_span_px / sf, 2)

        room["max_span_m"] = max_span_m

        if max_span_m > 5.0:
            concerns.append({
                "room_id": room["id"],
                "room_label": room["label"],
                "span_m": max_span_m,
                "concern": f"Span of {max_span_m}m exceeds 5m threshold — steel frame or RCC beam mandatory",
                "severity": "critical",
                "requires_column": True,
            })
        elif max_span_m > 4.0:
            concerns.append({
                "room_id": room["id"],
                "room_label": room["label"],
                "span_m": max_span_m,
                "concern": f"Span of {max_span_m}m exceeds 4m threshold — RCC beam recommended",
                "severity": "high",
                "requires_column": True,
            })

    return concerns


# ---------------------------------------------------------------------------
# Column Placement
# ---------------------------------------------------------------------------
def compute_required_columns(concerns: list, rooms: list) -> list:
    """Generate column positions for rooms with long spans."""
    columns = []

    for concern in concerns:
        if not concern.get("requires_column"):
            continue
        room = next((r for r in rooms if r["id"] == concern["room_id"]), None)
        if room:
            cx, cy = room["centroid"]
            columns.append({
                "position": [cx, cy],
                "room_id": concern["room_id"],
                "reason": f"Mid-span support for {concern['room_label']} ({concern['span_m']}m span)"
            })

    return columns


# ---------------------------------------------------------------------------
# Main Pipeline Function
# ---------------------------------------------------------------------------
def reconstruct_geometry(parsed_data: dict) -> dict:
    """
    Stage 2 main function: takes Stage 1 output and produces
    classified walls, structural concerns, and column requirements.
    """
    # Grid snap first
    parsed_data = snap_walls_to_grid(parsed_data)

    # Build graph
    G = build_wall_graph(parsed_data)
    junctions = detect_junctions(G)

    # Classify walls
    classified_walls = classify_walls(parsed_data)

    # Detect spans
    structural_concerns = detect_spans(parsed_data)

    # Compute columns
    columns = compute_required_columns(structural_concerns, parsed_data["rooms"])

    # Build graph serialization
    graph_data = {
        "nodes": [{"position": list(n), "degree": G.degree(n)} for n in G.nodes()],
        "edges": [
            {
                "start": list(e[0]),
                "end": list(e[1]),
                "wall_id": G.edges[e].get("wall_id"),
                "length_m": G.edges[e].get("length_m"),
            }
            for e in G.edges()
        ],
        "junctions": {
            "endpoints": [list(n) for n in junctions["endpoints"]],
            "L_corners": [list(n) for n in junctions["L_corners"]],
            "T_junctions": [list(n) for n in junctions["T_junctions"]],
            "crossroads": [list(n) for n in junctions["crossroads"]],
        }
    }

    return {
        "walls": parsed_data["walls"],
        "rooms": parsed_data["rooms"],
        "openings": parsed_data.get("openings", []),
        "scale_factor": parsed_data.get("scale_factor", 50.0),
        "image_dimensions": parsed_data.get("image_dimensions", [800, 600]),
        "wall_graph": graph_data,
        "classified_walls": classified_walls,
        "structural_concerns": structural_concerns,
        "columns_required": columns,
    }
