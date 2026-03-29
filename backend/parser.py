"""
parser.py — Stage 1: Floor Plan Parsing

Accepts a floor plan image (PNG/JPG) and extracts:
- Walls (line segments with start/end coordinates)
- Rooms (enclosed polygon regions with labels)
- Openings (doors and windows as gaps in walls)

Implements the 70% area heuristic fallback for robustness.
"""

import cv2
import numpy as np
import json
import os
import math
from shapely.geometry import LineString, Polygon, MultiLineString, box
from shapely.ops import polygonize, unary_union
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CV_CONFIG = {
    "binary_threshold": 200,
    "canny_low": 50,
    "canny_high": 150,
    "hough_threshold": 80,
    "hough_min_line_length": 30,
    "hough_max_line_gap": 10,
    "angle_snap_tolerance_deg": 5,
    "line_dedup_distance_px": 8,
    "min_room_area_px2": 2000,
    "min_rooms_before_fallback": 2,
    "area_coverage_threshold": 0.70,
    "door_gap_min_px": 40,
    "door_gap_max_px": 120,
    "window_gap_min_px": 20,
    "window_gap_max_px": 60,
    "endpoint_merge_tolerance_px": 10,
    "default_scale_factor": 50.0,
}

FALLBACK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallback")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def snap_angle(x1, y1, x2, y2, tolerance_deg=5):
    """Snap line to nearest orthogonal direction if within tolerance."""
    angle = math.degrees(math.atan2(abs(y2 - y1), abs(x2 - x1)))
    if angle <= tolerance_deg:
        # Near-horizontal → snap to horizontal
        mid_y = (y1 + y2) / 2
        return x1, mid_y, x2, mid_y, "horizontal"
    elif angle >= (90 - tolerance_deg):
        # Near-vertical → snap to vertical
        mid_x = (x1 + x2) / 2
        return mid_x, y1, mid_x, y2, "vertical"
    else:
        # Diagonal — likely artifact
        return None


def line_distance(l1, l2):
    """Compute perpendicular distance between two parallel line segments."""
    (x1, y1, x2, y2) = l1
    (x3, y3, x4, y4) = l2
    # Use midpoint distance for simplicity
    mx1, my1 = (x1 + x2) / 2, (y1 + y2) / 2
    mx2, my2 = (x3 + x4) / 2, (y3 + y4) / 2
    return math.sqrt((mx1 - mx2) ** 2 + (my1 - my2) ** 2)


def lines_same_orientation(l1_orient, l2_orient):
    return l1_orient == l2_orient


def line_length(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def merge_collinear_segments(lines, gap_threshold=15):
    """Merge collinear segments that are close together."""
    merged = []
    used = set()

    for i, (l1, o1) in enumerate(lines):
        if i in used:
            continue
        current = list(l1)
        orient = o1
        used.add(i)

        changed = True
        while changed:
            changed = False
            for j, (l2, o2) in enumerate(lines):
                if j in used or o1 != o2:
                    continue
                if orient == "horizontal":
                    if abs(current[1] - l2[1]) < 8:
                        min_x = min(current[0], current[2], l2[0], l2[2])
                        max_x = max(current[0], current[2], l2[0], l2[2])
                        # Check gap
                        seg1_max = max(current[0], current[2])
                        seg1_min = min(current[0], current[2])
                        seg2_max = max(l2[0], l2[2])
                        seg2_min = min(l2[0], l2[2])
                        gap = max(seg2_min - seg1_max, seg1_min - seg2_max)
                        if gap < gap_threshold:
                            current = [min_x, current[1], max_x, current[1]]
                            used.add(j)
                            changed = True
                elif orient == "vertical":
                    if abs(current[0] - l2[0]) < 8:
                        min_y = min(current[1], current[3], l2[1], l2[3])
                        max_y = max(current[1], current[3], l2[1], l2[3])
                        seg1_max = max(current[1], current[3])
                        seg1_min = min(current[1], current[3])
                        seg2_max = max(l2[1], l2[3])
                        seg2_min = min(l2[1], l2[3])
                        gap = max(seg2_min - seg1_max, seg1_min - seg2_max)
                        if gap < gap_threshold:
                            current = [current[0], min_y, current[0], max_y]
                            used.add(j)
                            changed = True

        merged.append((tuple(current), orient))

    return merged


def deduplicate_lines(lines, distance_threshold=8):
    """Remove near-duplicate lines, keeping the longer one."""
    result = []
    used = set()

    sorted_lines = sorted(lines, key=lambda l: line_length(*l[0]), reverse=True)

    for i, (l1, o1) in enumerate(sorted_lines):
        if i in used:
            continue
        result.append((l1, o1))
        for j, (l2, o2) in enumerate(sorted_lines):
            if j <= i or j in used:
                continue
            if o1 == o2 and line_distance(l1, l2) < distance_threshold:
                used.add(j)

    return result


def detect_openings_in_wall(wall_line, orientation, binary_img, config):
    """Detect gaps (doors/windows) in a wall segment by scanning for white pixels."""
    openings = []
    x1, y1, x2, y2 = wall_line

    if orientation == "horizontal":
        y = int(y1)
        start_x, end_x = int(min(x1, x2)), int(max(x1, x2))
        if y < 0 or y >= binary_img.shape[0]:
            return openings
        scan_line = binary_img[max(0, y-2):min(binary_img.shape[0], y+3),
                               start_x:end_x]
        if scan_line.size == 0:
            return openings
        col_means = np.mean(scan_line, axis=0)
        in_gap = False
        gap_start = 0
        for px_idx, val in enumerate(col_means):
            if val < 128 and not in_gap:
                in_gap = True
                gap_start = px_idx
            elif val >= 128 and in_gap:
                in_gap = False
                gap_width = px_idx - gap_start
                if gap_width >= config["window_gap_min_px"]:
                    gap_cx = start_x + gap_start + gap_width // 2
                    if gap_width >= config["door_gap_min_px"]:
                        openings.append({
                            "position": [gap_cx, y],
                            "width_px": gap_width,
                            "type": "door" if gap_width >= config["door_gap_min_px"] else "window"
                        })
                    else:
                        openings.append({
                            "position": [gap_cx, y],
                            "width_px": gap_width,
                            "type": "window"
                        })
    else:  # vertical
        x = int(x1)
        start_y, end_y = int(min(y1, y2)), int(max(y1, y2))
        if x < 0 or x >= binary_img.shape[1]:
            return openings
        scan_line = binary_img[start_y:end_y,
                               max(0, x-2):min(binary_img.shape[1], x+3)]
        if scan_line.size == 0:
            return openings
        row_means = np.mean(scan_line, axis=1)
        in_gap = False
        gap_start = 0
        for px_idx, val in enumerate(row_means):
            if val < 128 and not in_gap:
                in_gap = True
                gap_start = px_idx
            elif val >= 128 and in_gap:
                in_gap = False
                gap_width = px_idx - gap_start
                if gap_width >= config["window_gap_min_px"]:
                    gap_cy = start_y + gap_start + gap_width // 2
                    openings.append({
                        "position": [x, gap_cy],
                        "width_px": gap_width,
                        "type": "door" if gap_width >= config["door_gap_min_px"] else "window"
                    })

    return openings


def calculate_bounding_box_area(rooms, walls):
    """Calculate bounding box area from all walls and room polygons."""
    all_x = []
    all_y = []
    for wall in walls:
        all_x.extend([wall[0][0], wall[0][2]])
        all_y.extend([wall[0][1], wall[0][3]])
    if not all_x:
        return 1  # Avoid division by zero
    return (max(all_x) - min(all_x)) * (max(all_y) - min(all_y))


def snap_to_grid(coordinates, grid_size_px=5.0):
    """Round all coordinates to nearest grid_size_px to eliminate gaps."""
    return [[round(x / grid_size_px) * grid_size_px for x in coord]
            for coord in coordinates]


# ---------------------------------------------------------------------------
# Fallback loader
# ---------------------------------------------------------------------------
def load_fallback(plan_id: Optional[str], image_path: str) -> dict:
    """Load manually-defined coordinates when CV parsing fails."""
    if plan_id:
        fb_path = os.path.join(FALLBACK_DIR, f"{plan_id}_coords.json")
        if os.path.exists(fb_path):
            with open(fb_path, "r") as f:
                data = json.load(f)
            data["fallback_used"] = True
            data["fallback_reason"] = "CV parsing failed — loaded manual coordinates"
            return data

    # Try to match by filename
    basename = os.path.splitext(os.path.basename(image_path))[0]
    for suffix in ["_coords.json", ".json"]:
        fb_path = os.path.join(FALLBACK_DIR, basename + suffix)
        if os.path.exists(fb_path):
            with open(fb_path, "r") as f:
                data = json.load(f)
            data["fallback_used"] = True
            data["fallback_reason"] = f"CV parsing failed — loaded fallback from {basename}"
            return data

    # Ultimate fallback: plan_a
    fb_path = os.path.join(FALLBACK_DIR, "plan_a_coords.json")
    if os.path.exists(fb_path):
        with open(fb_path, "r") as f:
            data = json.load(f)
        data["fallback_used"] = True
        data["fallback_reason"] = "CV parsing failed — loaded default plan_a fallback"
        return data

    # If truly nothing found, return empty structure
    return {
        "walls": [], "rooms": [], "openings": [],
        "scale_factor": CV_CONFIG["default_scale_factor"],
        "image_dimensions": [800, 600],
        "fallback_used": True,
        "fallback_reason": "No fallback file found"
    }


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------
def parse_floor_plan(image_path: str, plan_id: str = None) -> dict:
    """
    Parse a floor plan image to extract walls, rooms, and openings.

    Args:
        image_path: Path to floor plan image (PNG/JPG)
        plan_id: Optional plan identifier for fallback matching

    Returns:
        Structured dict with walls, rooms, openings, scale_factor, etc.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return load_fallback(plan_id, image_path)

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Step 1: Binarize
        _, binary = cv2.threshold(
            gray, CV_CONFIG["binary_threshold"], 255, cv2.THRESH_BINARY_INV
        )

        # Step 2: Edge detection
        edges = cv2.Canny(
            binary,
            CV_CONFIG["canny_low"],
            CV_CONFIG["canny_high"],
            apertureSize=3,
        )

        # Step 3: Hough line detection
        raw_lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=CV_CONFIG["hough_threshold"],
            minLineLength=CV_CONFIG["hough_min_line_length"],
            maxLineGap=CV_CONFIG["hough_max_line_gap"],
        )

        if raw_lines is None or len(raw_lines) < 4:
            return load_fallback(plan_id, image_path)

        # Step 4: Snap lines to orthogonal grid
        snapped_lines = []
        for line in raw_lines:
            x1, y1, x2, y2 = line[0]
            result = snap_angle(
                x1, y1, x2, y2, CV_CONFIG["angle_snap_tolerance_deg"]
            )
            if result is not None:
                sx1, sy1, sx2, sy2, orient = result
                snapped_lines.append(
                    ((sx1, sy1, sx2, sy2), orient)
                )

        if len(snapped_lines) < 4:
            return load_fallback(plan_id, image_path)

        # Step 5: Deduplicate near-identical lines
        deduped = deduplicate_lines(
            snapped_lines, CV_CONFIG["line_dedup_distance_px"]
        )

        # Step 6: Merge collinear nearby segments
        merged = merge_collinear_segments(deduped, gap_threshold=15)

        # Step 7: Build Shapely lines and polygonize for rooms
        shapely_lines = []
        for (x1, y1, x2, y2), orient in merged:
            shapely_lines.append(LineString([(x1, y1), (x2, y2)]))

        multi_line = MultiLineString(shapely_lines)
        rooms = list(polygonize(unary_union(multi_line)))
        rooms = [r for r in rooms if r.area > CV_CONFIG["min_room_area_px2"]]

        # Step 8: Area heuristic fallback check
        total_room_area = sum(r.area for r in rooms)
        bb_area = calculate_bounding_box_area(merged, merged)

        if (len(rooms) < CV_CONFIG["min_rooms_before_fallback"] or
                (bb_area > 0 and total_room_area < CV_CONFIG["area_coverage_threshold"] * bb_area)):
            return load_fallback(plan_id, image_path)

        # Step 9: Build output structure
        scale_factor = CV_CONFIG["default_scale_factor"]

        # Walls
        wall_list = []
        for i, ((x1, y1, x2, y2), orient) in enumerate(merged):
            length_px = line_length(x1, y1, x2, y2)
            wall_list.append({
                "id": f"w{i+1}",
                "start": [round(x1), round(y1)],
                "end": [round(x2), round(y2)],
                "length_px": round(length_px, 1),
                "length_m": round(length_px / scale_factor, 2),
                "orientation": orient,
            })

        # Rooms
        room_list = []
        room_labels = [
            "BEDROOM 1", "BEDROOM 2", "BEDROOM 3", "BEDROOM 4",
            "LIVING ROOM", "KITCHEN", "BATHROOM 1", "BATHROOM 2",
            "FOYER", "LAUNDRY", "HALLWAY", "DINING ROOM",
        ]
        for i, room_poly in enumerate(rooms):
            centroid = room_poly.centroid
            coords = list(room_poly.exterior.coords[:-1])
            snapped_coords = snap_to_grid(coords)
            label = room_labels[i] if i < len(room_labels) else f"ROOM {i+1}"
            room_list.append({
                "id": f"r{i+1}",
                "label": label,
                "polygon": [[round(c[0]), round(c[1])] for c in snapped_coords],
                "area_m2": round(room_poly.area / (scale_factor ** 2), 1),
                "centroid": [round(centroid.x), round(centroid.y)],
            })

        # Step 10: Detect openings
        opening_list = []
        oid = 1
        for wall in wall_list:
            x1, y1 = wall["start"]
            x2, y2 = wall["end"]
            orient = wall["orientation"]
            detected = detect_openings_in_wall(
                (x1, y1, x2, y2), orient, binary, CV_CONFIG
            )
            for op in detected:
                op["id"] = f"o{oid}"
                op["wall_id"] = wall["id"]
                op["width_m"] = round(op["width_px"] / scale_factor, 2)
                if op["type"] == "door":
                    op["height_m"] = 2.1
                else:
                    op["height_m"] = 1.2
                    op["sill_m"] = 0.9
                opening_list.append(op)
                oid += 1

        result = {
            "walls": wall_list,
            "rooms": room_list,
            "openings": opening_list,
            "scale_factor": scale_factor,
            "image_dimensions": [w, h],
            "fallback_used": False,
        }

        return result

    except Exception as e:
        print(f"[Parser Error] {e}")
        return load_fallback(plan_id, image_path)
