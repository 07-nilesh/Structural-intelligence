import cv2
import numpy as np
import sys
import json

def test_colors(img_path):
    img = cv2.imread(img_path)
    if img is None:
        print("Could not load image")
        return

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Yellow (Windows)
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    contours_y, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    windows = []
    for cnt in contours_y:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 5 and h > 5:
            windows.append({"type": "window", "x": x, "y": y, "w": w, "h": h})
            
    # Blue (Doors)
    lower_blue = np.array([100, 150, 0])
    upper_blue = np.array([140, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    contours_b, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    doors = []
    for cnt in contours_b:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 5 and h > 5:
            doors.append({"type": "door", "x": x, "y": y, "w": w, "h": h})
            
    # Red (Door arc)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_red = mask_red1 + mask_red2
    
    contours_r, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    door_arcs = []
    for cnt in contours_r:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 5 and h > 5:
            door_arcs.append({"type": "door_arc", "x": x, "y": y, "w": w, "h": h})

    out = {"windows": windows, "doors": doors, "door_arcs": door_arcs}
    with open("test_color_out.json", "w") as f:
        json.dump(out, f, indent=2)

test_colors(sys.argv[1])
