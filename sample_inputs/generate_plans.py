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

WALL_THICKNESS = 8
FONT = cv2.FONT_HERSHEY_DUPLEX
FONT_SCALE = 0.5
FONT_THICKNESS = 1
LABEL_COLOR = (100, 100, 100) # Dark grey BGR
WALL_COLOR = (20, 20, 20)     # Near black BGR
ROOM_BG = (235, 240, 245)     # Cream BGR (OpenCV uses BGR) #f5f0eb -> BGR (235, 240, 245)
BATH_BG = (210, 225, 230)     # Darker Beige BGR #e6e1d2 -> BGR (210, 225, 230)
BG_COLOR = (255, 255, 255)
OPENING_MARK_COLOR = (0, 0, 0)

# Titles for specific plans
PLAN_METADATA = {
    "plan_a": {"title": "HOUSE FLOOR PLAN — PLAN A", "subtitle": "2 Bedrooms / 1 Bathroom"},
    "plan_b": {"title": "HOUSE FLOOR PLAN — PLAN B", "subtitle": "4 Bedrooms / 3 Bathrooms"},
    "plan_c": {"title": "HOUSE FLOOR PLAN — PLAN C (L-SHAPED)", "subtitle": "3 Bedrooms / 2 Bathrooms (L-Shaped)"}
}

def draw_floor_plan(plan_data: dict, output_path: str, plan_name: str):
    w, h = plan_data["image_dimensions"]
    # Add padding for headers and footers
    pad_top = 80
    pad_bot = 80
    pad_sides = 40
    
    # We will scale everything slightly to fit nicely
    scale = 1.0
    img = np.ones((h + pad_top + pad_bot, w + pad_sides * 2, 3), dtype=np.uint8) * 255

    # 1. Fill Rooms First
    for room in plan_data["rooms"]:
        # Find walls that bound this room (Rough approximation by filling rectangle if we had bbox)
        # We don't have exact polygons, but we can assume generic rectangular fills.
        # Actually, let's just draw the background rects based on the room's centroid and neighbors?
        pass # Too complex to auto-deduce exact polygon without geometry bounding box from JSON
        
    # Hack for room background: Let's fill the entire bounding box of all walls with ROOM_BG, 
    # then we draw the walls.
    min_x = min([min(w["start"][0], w["end"][0]) for w in plan_data["walls"]])
    min_y = min([min(w["start"][1], w["end"][1]) for w in plan_data["walls"]])
    max_x = max([max(w["start"][0], w["end"][0]) for w in plan_data["walls"]])
    max_y = max([max(w["start"][1], w["end"][1]) for w in plan_data["walls"]])
    
    cv2.rectangle(img, (min_x + pad_sides, min_y + pad_top), (max_x + pad_sides, max_y + pad_top), ROOM_BG, -1)
    
    # Overlay BATH_BG manually for bathrooms by drawing a filled rect around its centroid
    for room in plan_data["rooms"]:
        if "BATH" in room["label"].upper():
            cx, cy = room["centroid"]
            # Approximate the bathroom bounds (a 120x120px box around centroid)
            b_w = 120
            cv2.rectangle(img, (int(cx) - b_w + pad_sides, int(cy) - b_w + pad_top), 
                               (int(cx) + b_w + pad_sides, int(cy) + b_w + pad_top), BATH_BG, -1)

    # 2. Draw Walls
    for wall in plan_data["walls"]:
        pt1 = (wall["start"][0] + pad_sides, wall["start"][1] + pad_top)
        pt2 = (wall["end"][0] + pad_sides, wall["end"][1] + pad_top)
        cv2.line(img, pt1, pt2, WALL_COLOR, WALL_THICKNESS)

    # 3. Draw Openings
    for op in plan_data.get("openings", []):
        pos = op["position"]
        width_px = op.get("width_px", 40)
        wall_id = op["wall_id"]
        wall = next((w for w in plan_data["walls"] if w["id"] == wall_id), None)
        if not wall: continue

        px = pos[0] + pad_sides
        py = pos[1] + pad_top

        if wall["orientation"] == "horizontal":
            x1 = px - width_px // 2
            x2 = px + width_px // 2
            # Clear wall gap
            cv2.line(img, (x1, py), (x2, py), ROOM_BG, WALL_THICKNESS + 2)
            
            if op["type"] == "door":
                # Door arc
                cv2.ellipse(img, (x1, py), (width_px, width_px), 0, -90, 0, OPENING_MARK_COLOR, 1)
                cv2.line(img, (x1, py), (x1, py - width_px), OPENING_MARK_COLOR, 1) # Door panel
            else:
                # Window
                cv2.line(img, (x1, py), (x2, py), WALL_COLOR, WALL_THICKNESS) # Restore wall
                cv2.rectangle(img, (x1, py - 3), (x2, py + 3), BG_COLOR, -1)   # White inner glass
                cv2.rectangle(img, (x1, py - 3), (x2, py + 3), WALL_COLOR, 1)  # Frame
        
        else: # Vertical
            y1 = py - width_px // 2
            y2 = py + width_px // 2
            
            # Since vertical bath walls might border room backgrounds, just clear with ROOM_BG for now
            cv2.line(img, (px, y1), (px, y2), ROOM_BG, WALL_THICKNESS + 2)
            
            if op["type"] == "door":
                cv2.ellipse(img, (px, y1), (width_px, width_px), 0, 0, 90, OPENING_MARK_COLOR, 1)
                cv2.line(img, (px, y1), (px + width_px, y1), OPENING_MARK_COLOR, 1) # Door panel
            else:
                cv2.line(img, (px, y1), (px, y2), WALL_COLOR, WALL_THICKNESS)
                cv2.rectangle(img, (px - 3, y1), (px + 3, y2), BG_COLOR, -1)
                cv2.rectangle(img, (px - 3, y1), (px + 3, y2), WALL_COLOR, 1)

    # Clean up outer borders slightly to look sharp
    cv2.rectangle(img, (min_x + pad_sides, min_y + pad_top), (max_x + pad_sides, max_y + pad_top), WALL_COLOR, WALL_THICKNESS)


    # 4. Draw Room Labels (Bold simple text)
    for room in plan_data["rooms"]:
        cx = int(room["centroid"][0]) + pad_sides
        cy = int(room["centroid"][1]) + pad_top
        label = room["label"]
        text_size = cv2.getTextSize(label, FONT, FONT_SCALE, 2)[0] # Bold
        cv2.putText(img, label, (cx - text_size[0] // 2, cy + text_size[1] // 2), 
                    FONT, FONT_SCALE, LABEL_COLOR, 2)

    # 5. Add Headers and Footers
    meta = PLAN_METADATA.get(plan_name, {"title": "HOUSE FLOOR PLAN", "subtitle": ""})
    
    # Title
    t_size = cv2.getTextSize(meta["title"], cv2.FONT_HERSHEY_DUPLEX, 0.7, 2)[0]
    cv2.putText(img, meta["title"], (img.shape[1]//2 - t_size[0]//2, 45), 
                cv2.FONT_HERSHEY_DUPLEX, 0.7, WALL_COLOR, 2)
                
    # Footer
    s_size = cv2.getTextSize(meta["subtitle"], cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    cv2.putText(img, meta["subtitle"], (img.shape[1]//2 - s_size[0]//2, img.shape[0] - 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 50), 1)

    # 6. Scale bar
    s_x, s_y = pad_sides, img.shape[0] - 30
    cv2.line(img, (s_x, s_y), (s_x + 100, s_y), WALL_COLOR, 1)
    cv2.line(img, (s_x, s_y - 3), (s_x, s_y + 3), WALL_COLOR, 1)
    cv2.line(img, (s_x + 100, s_y - 3), (s_x + 100, s_y + 3), WALL_COLOR, 1)
    
    sc_size = cv2.getTextSize("~4 m", cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
    cv2.putText(img, "~4 m", (s_x + 50 - sc_size[0]//2, s_y + 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80, 80, 80), 1)

    cv2.imwrite(output_path, img)
    print(f"Generated visually-identical style: {output_path}")


def main():
    for plan_name in ["plan_a", "plan_b", "plan_c"]:
        coords_path = os.path.join(FALLBACK_DIR, f"{plan_name}_coords.json")
        output_path = os.path.join(OUTPUT_DIR, f"{plan_name}.png")

        if not os.path.exists(coords_path):
            continue

        with open(coords_path, "r") as f:
            plan_data = json.load(f)

        draw_floor_plan(plan_data, output_path, plan_name)

if __name__ == "__main__":
    main()
