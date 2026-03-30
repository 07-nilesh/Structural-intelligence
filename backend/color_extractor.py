import cv2
import numpy as np
import os
import json
from geometry_utils import point_to_line_distance


def extract_structural_openings(image_path: str, wall_segments: list | None = None, debug: bool = False) -> list:
    """Extract windows, door panels, and door swing arcs from a color‑coded floor plan.

    Parameters
    ----------
    image_path: str
        Path to the **edited** floor‑plan image (with yellow, blue, red annotations).
    wall_segments: list | None
        Optional list of wall line dictionaries as returned by ``wall_extractor.load_wall_segments``.
        If provided, each opening will be associated with the nearest wall (added as ``wall_id``).
    debug: bool
        When ``True``, a debug overlay image ``<basename>_debug.png`` is saved next to the input.

    Returns
    -------
    list of dict
        Each dict follows the naming convention:
        {
            "id": int,
            "type": "window" | "door_panel" | "door_swing",
            "center_px": [x, y],
            "size_px": [w, h] (for windows/door panels),
            "metadata": {"radius": ..., "start_angle": ..., "end_angle": ..., "swing_type": ...} (for door_swing),
            "wall_id": int (optional)
        }
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"[Color Extractor] WARNING: Could not read {image_path}")
        return []

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    openings = []
    uid = 0

    # ---------- 1. WINDOWS (Yellow) ----------
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    contours_y, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_y:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 5 and h > 5:
            opening = {
                "id": uid,
                "type": "window",
                "center_px": [x + w / 2, y + h / 2],
                "size_px": [w, h]
            }
            openings.append(opening)
            uid += 1

    # ---------- 2. DOOR PANELS (Blue straight lines) ----------
    lower_blue = np.array([100, 150, 0])
    upper_blue = np.array([140, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    contours_b, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_b:
        epsilon = 0.02 * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        if len(approx) == 2:  # Straight line
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 5 and h > 5:
                opening = {
                    "id": uid,
                    "type": "door_panel",
                    "center_px": [x + w / 2, y + h / 2],
                    "size_px": [w, h]
                }
                openings.append(opening)
                uid += 1

    # ---------- 3. DOOR SWING TRAJECTORIES (Red arcs) ----------
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
    contours_r, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours_r:
        if cnt.shape[0] < 5:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        pts = cnt.squeeze()
        if pts.ndim != 2:
            continue
        
        # Robust span calculation
        angles = np.degrees(np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx)) % 360
        angles.sort()
        
        # Find the largest gap to calculate circular span
        gaps = np.diff(angles)
        max_gap = np.max(gaps)
        # Check gap between last and first
        dist_last_first = (angles[0] - angles[-1]) % 360
        if dist_last_first > max_gap:
            max_gap = dist_last_first
            
        span = 360 - max_gap
        
        # Determine swing side: if span is around 90, it's a standard quarter-circle
        swing_type = "inswing" if span < 180 else "outswing"
        
        opening = {
            "id": uid,
            "type": "door_swing",
            "center_px": [cx, cy],
            "metadata": {
                "radius": float(radius),
                "start_angle": float(np.min(angles)),
                "end_angle": float(np.max(angles)),
                "span": float(span),
                "swing_type": swing_type
            }
        }
        openings.append(opening)
        uid += 1

    # ---------- 4. GROUP DOOR PANELS WITH SWINGS ----------
    # Often a blue line (panel) and red arc (swing) belong to the same door.
    grouped_openings = []
    consumed_swings = set()
    
    panels = [o for o in openings if o["type"] == "door_panel"]
    swings = [o for o in openings if o["type"] == "door_swing"]
    windows = [o for o in openings if o["type"] == "window"]
    
    for p in panels:
        px, py = p["center_px"]
        best_swing = None
        min_s_dist = 50.0 # Pixel threshold for grouping
        
        for s in swings:
            if s["id"] in consumed_swings: continue
            sx, sy = s["center_px"]
            dist = np.sqrt((px - sx)**2 + (py - sy)**2)
            if dist < min_s_dist:
                min_s_dist = dist
                best_swing = s
        
        if best_swing:
            # Merge swing into panel metadata
            p["type"] = "door" # Standardize to 'door' for the final pipeline
            p["metadata"] = best_swing["metadata"]
            consumed_swings.add(best_swing["id"])
        else:
            p["type"] = "door" # Even if no swing found, it's a door
            
        grouped_openings.append(p)
        
    # Add remaining swings and windows
    for s in swings:
        if s["id"] not in consumed_swings:
            grouped_openings.append(s)
    for w in windows:
        grouped_openings.append(w)

    openings = grouped_openings

    # ---------- 5. OPTIONAL WALL ASSOCIATION ----------
    if wall_segments is not None:
        for opening in openings:
            cx, cy = opening["center_px"]
            min_dist = float('inf')
            nearest_id = None
            for wall in wall_segments:
                dist = point_to_line_distance(cx, cy, wall["x1"], wall["y1"], wall["x2"], wall["y2"])
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = wall["id"]
            opening["wall_id"] = nearest_id

    # ---------- 5. DEBUG OVERLAY (if requested) ----------
    if debug:
        overlay = img.copy()
        for o in openings:
            if o["type"] == "window":
                cx, cy = map(int, o["center_px"])
                w, h = map(int, o["size_px"])
                top_left = (int(cx - w / 2), int(cy - h / 2))
                bottom_right = (int(cx + w / 2), int(cy + h / 2))
                cv2.rectangle(overlay, top_left, bottom_right, (0, 255, 255), 2)
            elif o["type"] == "door_panel":
                cx, cy = map(int, o["center_px"])
                w, h = map(int, o["size_px"])
                pt1 = (int(cx - w / 2), int(cy - h / 2))
                pt2 = (int(cx + w / 2), int(cy + h / 2))
                cv2.rectangle(overlay, pt1, pt2, (255, 0, 0), 2)
            elif o["type"] == "door_swing":
                cx, cy = map(int, o["center_px"])
                radius = int(o["metadata"]["radius"])
                # For debug drawing, we use the min/max but drawing might be off if it wraps
                start = int(o["metadata"]["start_angle"])
                end = int(o["metadata"]["end_angle"])
                cv2.ellipse(overlay, (int(cx), int(cy)), (radius, radius), 0, start, end, (0, 0, 255), 2)
        debug_path = os.path.splitext(image_path)[0] + "_debug.png"
        cv2.imwrite(debug_path, overlay)
        print(f"[Color Extractor] Debug overlay saved to {debug_path}")

    return openings
