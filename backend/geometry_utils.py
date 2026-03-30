import numpy as np
import cv2

def point_to_line_distance(px, py, x1, y1, x2, y2):
    """
    Compute the perpendicular distance from a point (px, py) to a line segment (x1, y1, x2, y2).
    """
    line_vec = np.array([x2 - x1, y2 - y1])
    p_vec = np.array([px - x1, py - y1])
    line_len_sq = np.sum(line_vec**2)
    
    if line_len_sq == 0:
        return np.sqrt(np.sum(p_vec**2))
    
    # Projection of p_vec onto line_vec
    t = np.dot(p_vec, line_vec) / line_len_sq
    t = max(0, min(1, t))  # Clamp to segment
    
    projection = np.array([x1, y1]) + t * line_vec
    dist = np.sqrt(np.sum((np.array([px, py]) - projection)**2))
    
    return float(dist)

def fit_circle_to_contour(cnt):
    """
    Fit a minimum enclosing circle to a contour.
    """
    (cx, cy), radius = cv2.minEnclosingCircle(cnt)
    return (cx, cy), radius
