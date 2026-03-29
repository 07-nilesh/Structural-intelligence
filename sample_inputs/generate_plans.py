"""
generate_plans.py — Programmatically generates clean digital floor plan PNGs
for testing the CV pipeline. Each plan matches its fallback coordinates file.
"""

import cv2
import numpy as np
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FALLBACK_DIR = os.path.join(SCRIPT_DIR, "..", "backend", "fallback")
OUTPUT_DIR = SCRIPT_DIR

WALL_THICKNESS = 6  # px for drawing
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.45
FONT_THICKNESS = 1
LABEL_COLOR = (80, 80, 80)
WALL_COLOR = (0, 0, 0)
DOOR_COLOR = (255, 255, 255)
BG_COLOR = (255, 255, 255)
OPENING_MARK_COLOR = (180, 180, 180)


def draw_floor_plan(plan_data: dict, output_path: str):
    """Draw a clean orthogonal floor plan from coordinate data."""
    w, h = plan_data["image_dimensions"]
    img = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Draw walls
    for wall in plan_data["walls"]:
        pt1 = tuple(wall["start"])
        pt2 = tuple(wall["end"])
        cv2.line(img, pt1, pt2, WALL_COLOR, WALL_THICKNESS)

    # Draw openings (gaps in walls)
    for opening in plan_data.get("openings", []):
        pos = opening["position"]
        width_px = opening.get("width_px", 40)
        wall_id = opening["wall_id"]

        # Find the wall to determine orientation
        wall = next((w for w in plan_data["walls"] if w["id"] == wall_id), None)
        if wall is None:
            continue

        if wall["orientation"] == "horizontal":
            # Horizontal wall: opening is a gap along x
            x1 = pos[0] - width_px // 2
            x2 = pos[0] + width_px // 2
            y = pos[1]
            cv2.line(img, (x1, y), (x2, y), BG_COLOR, WALL_THICKNESS + 2)
            if opening["type"] == "door":
                # Draw door arc indicator
                cv2.ellipse(img, (x1, y), (width_px, width_px), 0, -90, 0, OPENING_MARK_COLOR, 1)
            else:
                # Window: draw double line
                cv2.line(img, (x1, y - 2), (x2, y - 2), OPENING_MARK_COLOR, 1)
                cv2.line(img, (x1, y + 2), (x2, y + 2), OPENING_MARK_COLOR, 1)
        else:
            # Vertical wall: opening is a gap along y
            x = pos[0]
            y1 = pos[1] - width_px // 2
            y2 = pos[1] + width_px // 2
            cv2.line(img, (x, y1), (x, y2), BG_COLOR, WALL_THICKNESS + 2)
            if opening["type"] == "door":
                cv2.ellipse(img, (x, y1), (width_px, width_px), 0, 0, 90, OPENING_MARK_COLOR, 1)
            else:
                cv2.line(img, (x - 2, y1), (x - 2, y2), OPENING_MARK_COLOR, 1)
                cv2.line(img, (x + 2, y1), (x + 2, y2), OPENING_MARK_COLOR, 1)

    # Draw room labels
    for room in plan_data["rooms"]:
        cx, cy = room["centroid"]
        label = room["label"]
        text_size = cv2.getTextSize(label, FONT, FONT_SCALE, FONT_THICKNESS)[0]
        text_x = cx - text_size[0] // 2
        text_y = cy + text_size[1] // 2
        cv2.putText(img, label, (text_x, text_y), FONT, FONT_SCALE, LABEL_COLOR, FONT_THICKNESS)

        # Area label below
        area_str = f"{room['area_m2']} m2"
        area_size = cv2.getTextSize(area_str, FONT, FONT_SCALE * 0.8, FONT_THICKNESS)[0]
        cv2.putText(img, area_str, (cx - area_size[0] // 2, text_y + 18),
                    FONT, FONT_SCALE * 0.8, (120, 120, 120), FONT_THICKNESS)

    cv2.imwrite(output_path, img)
    print(f"Generated: {output_path}")


def main():
    for plan_name in ["plan_a", "plan_b", "plan_c"]:
        coords_path = os.path.join(FALLBACK_DIR, f"{plan_name}_coords.json")
        output_path = os.path.join(OUTPUT_DIR, f"{plan_name}.png")

        if not os.path.exists(coords_path):
            print(f"Skipping {plan_name}: coords file not found at {coords_path}")
            continue

        with open(coords_path, "r") as f:
            plan_data = json.load(f)

        draw_floor_plan(plan_data, output_path)

    print("\nAll floor plans generated successfully!")


if __name__ == "__main__":
    main()
