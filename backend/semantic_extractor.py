"""
semantic_extractor.py — Phase 1 & Stage 1: Semantic Extraction via VLM
Uses google-generativeai and gemini-2.5-flash to extract structural topology
and room boundaries directly from a floor plan image.
"""

import os
import json
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the API key
API_KEY = os.environ.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

def extract_floorplan_semantics(image_path: str) -> dict:
    """
    Extracts floorplan semantic data (rooms, spans, load-bearing walls)
    from an image using Google Gemini 2.5 Flash.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Initialize the model with JSON output enforcement
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    # Open the image file using Pillow
    img = Image.open(image_path)

    system_prompt = """You are an Expert Architectural AI and Structural Engineer. Analyze the provided 2D digital floor plan image.

Locate the "~4 m" scale bar at the bottom left to establish the pixel-to-meter ratio.

Scan all enclosed rooms. Calculate approximate dimensions. For each room, provide the (center_x_px, center_y_px) coordinates of its geometric center in the image. If any room has an unsupported span exceeding 5.0 meters, flag it as a span_concern.

Identify Load-Bearing Walls (outer perimeter walls and central structural spines).

Identify Partition Walls (short, internal dividers).

Output a STRICT JSON object matching this schema:
{
  "scale_calibration": {
    "pixel_to_meter_ratio": float,
    "confidence_score": float
  },
  "rooms": [
    {
      "id": "string",
      "label": "string",
      "center_x_px": integer,
      "center_y_px": integer,
      "approx_area_m2": float,
      "span_concern": boolean
    }
  ],
  "structural_analysis": {
    "perimeter_walls_detected": integer,
    "structural_spines_identified": "string",
    "re_entrant_corners": boolean
  }
}"""

    try:
        # Generate content by passing both the instruction and the image
        response = model.generate_content([system_prompt, img])
        
        # Parse and return the JSON dictionary
        result_dict = json.loads(response.text)
        return result_dict
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Raw response: {response.text}")
        return {}
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return {}


if __name__ == "__main__":
    # Test block using sample_inputs/plan_a.png
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_image = os.path.join(project_root, "sample_inputs", "plan_a.png")
    
    print(f"Testing Semantic Extractor on: {test_image}")
    
    if os.path.exists(test_image):
        result = extract_floorplan_semantics(test_image)
        print("\n--- Extracted Semantic JSON ---")
        print(json.dumps(result, indent=2))
    else:
        print(f"Test image not found at {test_image}. Please ensure the sample exists.")
