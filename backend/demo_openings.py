import os
import json
import argparse
from color_extractor import extract_structural_openings
from wall_extractor import load_wall_segments

# Filenames as specified by the user
RAW_IMAGES = ["plan_a.png", "plan_b.png", "plan_c.png"]
EDITED_IMAGES = ["plan1_a.png", "plan1_b.png", "plan1_c.png"]

def run_demo(debug=False):
    # Base directory for sample_inputs
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sample_inputs"))
    
    # Check if the directory exists
    if not os.path.exists(base_dir):
        print(f"[Demo] Error: Uploads directory not found at {base_dir}")
        return

    print(f"[Demo] Starting Analysis on {len(EDITED_IMAGES)} pairs...\n")

    results = {}

    for raw, edited in zip(RAW_IMAGES, EDITED_IMAGES):
        raw_path = os.path.join(base_dir, raw)
        edited_path = os.path.join(base_dir, edited)

        # Check if files exist
        if not os.path.exists(raw_path):
            print(f"[Demo] Skipping {raw}: File not found.")
            continue
        if not os.path.exists(edited_path):
            print(f"[Demo] Skipping {edited}: File not found.")
            continue

        print(f"--- Processing {edited} ---")
        
        # 1. Load walls from the raw image (Stage 2)
        try:
            walls = load_wall_segments(raw_path)
            print(f"  [Walls] Extracted {len(walls)} segments from {raw}.")
        except Exception as e:
            print(f"  [Error] Failed to load walls from {raw}: {e}")
            walls = None

        # 2. Extract colored structural openings (Stage 2.5)
        try:
            openings = extract_structural_openings(edited_path, wall_segments=walls, debug=debug)
            print(f"  [Openings] Identified {len(openings)} structural elements (Windows/Doors/Swings).")
            
            # Save results indexed by edited image name
            results[edited] = {
                "raw_source": raw,
                "wall_count": len(walls) if walls else 0,
                "openings": openings
            }
        except Exception as e:
            print(f"  [Error] Failed to extract openings from {edited}: {e}")

    # Output JSON results to a file for audit
    output_json = os.path.join(base_dir, "opening_analysis_results.json")
    with open(output_json, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[Success] Analysis complete. Full results saved to: {output_json}")
    if debug:
        print("[Info] Debug overlay images have been generated in the uploads folder.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo Structural Opening Extraction Pipeline")
    parser.add_argument("--debug", action="store_true", help="Generate and save debug overlay images")
    args = parser.parse_args()
    
    run_demo(debug=args.debug)
