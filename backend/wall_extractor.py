"""
wall_extractor.py — Stage 2: High-Precision Wall Segmentation
OpenCV Morphological Operations + segmentation_models_pytorch U-Net refinement.
"""

import cv2
import numpy as np
import torch
import segmentation_models_pytorch as smp
import os

def extract_wall_mask(image_path: str) -> np.ndarray:
    """Isolate solid thick walls, stripping away thin lines, doors, and text."""
    # a. Load image
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    # b. Strict Thresholding
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # In the generated plans, walls are near black BGR (20, 20, 20) against a cream background.
    # Text and open doors might also be dark, but windows are white with black borders.
    # We apply a strict binary threshold to capture only the darkest pixels as foreground (255)
    _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)

    # c. Morphological Filtering
    # Strip away text (usually 1-2 chars thick) and thin lines (door arcs, window edges) -> ~1-2px
    # Thick structural walls are 8px as defined in generate_plans.py.
    # A 5x5 morphological opening kernel will erase any line thinner than 5px.
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    cleaned_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_open, iterations=1)
    
    # Now that thin lines are gone, morphological closing fills in 
    # any tiny gaps or chips taken out of the thick structural walls.
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, kernel_close, iterations=1)

    # d. Deep Learning Refinement (U-Net) Scaffolding
    # Initialize a U-Net with a ResNet backbone as requested
    model = smp.Unet(
        encoder_name="resnet34",       
        encoder_weights=None,           # Use 'imagenet' later when weights are needed
        in_channels=1,                  # 1 channel for the grayscale segmentation mask input
        classes=1,                      # Binary classification (wall / no wall)
    )
    
    model.eval()
    with torch.no_grad():
        # Scaffolding: Convert physical mask to PyTorch tensor format [B, C, H, W] in [0, 1] range
        input_tensor = torch.from_numpy(cleaned_mask).float().unsqueeze(0).unsqueeze(0) / 255.0
        
        # When pre-trained weights are available:
        # output = model(input_tensor)
        # refined_mask = (torch.sigmoid(output).squeeze().numpy() * 255).astype(np.uint8)
        
        # For now, we bypass the neural network prediction and return the cleaned morphological mask
        refined_mask = cleaned_mask
        
    return refined_mask

def extract_wall_coordinates(wall_mask: np.ndarray) -> list:
    """Extract exact (x1, y1, x2, y2) coordinates using probabilistic Hough transform."""
    lines_extracted = []
    
    # Run HoughLinesP on the cleaned binary mask
    lines = cv2.HoughLinesP(
        wall_mask,
        rho=1,
        theta=np.pi / 180,
        threshold=50,
        minLineLength=30,
        maxLineGap=10
    )
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            lines_extracted.append({"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)})
            
    return lines_extracted

def load_wall_segments(image_path: str) -> list:
    """
    High-level wrapper to get a list of wall dictionaries with unique IDs.
    """
    mask = extract_wall_mask(image_path)
    coords = extract_wall_coordinates(mask)
    
    # Assign IDs
    walls = []
    for i, coord in enumerate(coords):
        wall = coord.copy()
        wall["id"] = i
        walls.append(wall)
        
    return walls

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_image = os.path.join(project_root, "sample_inputs", "plan_b.png")
    output_image = os.path.join(project_root, "debug_cleaned_walls.png")
    
    print(f"[Extractor] Initializing Wall Segmentation Pipeline on {test_image}")
    
    if os.path.exists(test_image):
        # 1. Pipeline mask generation
        mask = extract_wall_mask(test_image)
        
        # 2. Extract coordinates
        coords = extract_wall_coordinates(mask)
        
        # 3. Validation output
        cv2.imwrite(output_image, mask)
        print(f"[Success] Extracted {len(coords)} architectural wall segments.")
        print(f"[Output] Mask saved to {output_image}. Please verify doors/text are stripped.")
    else:
        print(f"[Error] Test image not found at {test_image}. Please check the sample inputs directory.")
