"""
material_optimizer.py — Stage 4: Cost-Strength Tradeoff Scoring

Recommends optimal construction materials for each structural element
using element-type-specific weight ratios with hard constraint enforcement.
"""

import json
import os
from typing import Dict, List

# ---------------------------------------------------------------------------
# Load material database
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load_materials() -> list:
    path = os.path.join(DATA_DIR, "materials.json")
    with open(path, "r") as f:
        return json.load(f)["materials"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_STRENGTH = 250.0
MAX_COST = 18000.0
MAX_DURABILITY = 10.0

ELEMENT_WEIGHTS = {
    "load_bearing_wall": {"cost": 0.25, "strength": 0.50, "durability": 0.25},
    "partition_wall":    {"cost": 0.55, "strength": 0.15, "durability": 0.30},
    "slab":              {"cost": 0.20, "strength": 0.55, "durability": 0.25},
    "column":            {"cost": 0.15, "strength": 0.60, "durability": 0.25},
    "long_span":         {"cost": 0.10, "strength": 0.70, "durability": 0.20},
}

ELIGIBLE_MATERIALS = {
    "load_bearing_wall": ["red_brick", "fly_ash_brick", "rcc", "precast_panel", "steel_frame"],
    "partition_wall":    ["aac_block", "hollow_concrete_block", "fly_ash_brick", "red_brick"],
    "slab":              ["rcc", "precast_panel"],
    "column":            ["rcc", "steel_frame"],
    "long_span":         ["rcc", "steel_frame"],
}

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def compute_tradeoff_score(material: dict, element_type: str, span_m: float = 0) -> float:
    """Compute composite score 0-100. Higher = better for this element type."""
    # Hard constraint: long spans >5m exclude weak materials
    if element_type == "long_span" and span_m > 5.0:
        if material["compressive_strength_mpa"] < 30:
            return 0.0
    if span_m > 4.0 and material["compressive_strength_mpa"] < 10:
        return 0.0

    cost_norm = 1 - (material["cost_per_m3_inr"] / MAX_COST)
    strength_norm = material["compressive_strength_mpa"] / MAX_STRENGTH
    durability_norm = material["durability_score"] / MAX_DURABILITY

    w = ELEMENT_WEIGHTS.get(element_type, ELEMENT_WEIGHTS["partition_wall"])
    score = (w["cost"] * cost_norm + w["strength"] * strength_norm + w["durability"] * durability_norm) * 100
    return round(max(0.0, score), 1)


def get_eligible_materials(element_type: str) -> list:
    return ELIGIBLE_MATERIALS.get(element_type, ELIGIBLE_MATERIALS["partition_wall"])


def recommend_materials(element: dict, all_materials: list) -> dict:
    """Return top 3 ranked materials for a structural element."""
    etype = element["type"]
    span = element.get("span_m", 0)
    eligible_ids = get_eligible_materials(etype)

    scored = []
    for mat in all_materials:
        score = compute_tradeoff_score(mat, etype, span)
        is_eligible = mat["id"] in eligible_ids
        exclusion = None
        if not is_eligible:
            exclusion = f"{mat['name']} not in best-use list for {etype}"
        if score == 0.0 and span > 5.0:
            exclusion = f"Compressive strength {mat['compressive_strength_mpa']} MPa insufficient for {span}m span"

        scored.append({
            "material_id": mat["id"],
            "material_name": mat["name"],
            "score": score,
            "eligible": is_eligible,
            "exclusion_reason": exclusion,
            "cost_per_m3_inr": mat["cost_per_m3_inr"],
            "strength_mpa": mat["compressive_strength_mpa"],
            "durability_score": mat["durability_score"],
            "weight_kg_m3": mat["weight_kg_m3"],
        })

    # Sort: eligible first, then by score
    scored.sort(key=lambda x: (not x["eligible"], -x["score"]))

    # Assign ranks to top 3
    top3 = scored[:3]
    for i, item in enumerate(top3):
        item["rank"] = i + 1
        w = ELEMENT_WEIGHTS.get(etype, ELEMENT_WEIGHTS["partition_wall"])
        item["weight_rationale"] = (
            f"strength={int(w['strength']*100)}%, cost={int(w['cost']*100)}%, "
            f"durability={int(w['durability']*100)}% for {etype.replace('_', ' ')}"
        )

    return {
        "element_id": element["element_id"],
        "element_type": etype,
        "element_label": element.get("element_label", ""),
        "span_m": span,
        "top_3_materials": top3,
        "all_scored": scored,
        "structural_flags": element.get("flags", []),
    }


# ---------------------------------------------------------------------------
# Pipeline function
# ---------------------------------------------------------------------------
def recommend_all_materials(geometry_data: dict) -> dict:
    """Generate material recommendations for every structural element."""
    materials = load_materials()
    classified = geometry_data["classified_walls"]
    walls = geometry_data["walls"]
    concerns = geometry_data.get("structural_concerns", [])
    rooms = geometry_data.get("rooms", [])

    # Build concern lookup
    room_concerns = {c["room_id"]: c for c in concerns}

    recommendations = []
    total_cost = 0

    for cw in classified:
        wall = next((w for w in walls if w["id"] == cw["wall_id"]), None)
        if not wall:
            continue

        etype = "load_bearing_wall" if cw["type"] == "load-bearing" else "partition_wall"
        span = wall.get("length_m", 0)

        # Check if this wall borders a room with structural concerns
        flags = []
        for concern in concerns:
            if concern["span_m"] > 5.0:
                flags.append(f"Adjacent room {concern['room_label']} has {concern['span_m']}m span")

        if span > 5.0:
            etype = "long_span"

        element = {
            "element_id": wall["id"],
            "type": etype,
            "element_label": f"Wall {wall['id']} ({wall['orientation']}, {wall['length_m']}m)",
            "span_m": span,
            "flags": flags,
            "location_description": f"{wall['orientation']} wall from {wall['start']} to {wall['end']}",
            "is_load_bearing": cw["type"] == "load-bearing",
            "area_m2": round(wall["length_m"] * 3.0, 2),
        }

        rec = recommend_materials(element, materials)
        recommendations.append(rec)

        # Estimate cost using top material
        if rec["top_3_materials"]:
            top_mat = rec["top_3_materials"][0]
            vol = wall["length_m"] * 3.0 * 0.23  # length * height * thickness
            total_cost += top_mat["cost_per_m3_inr"] * vol

    # Add column recommendations
    for col in geometry_data.get("columns_required", []):
        element = {
            "element_id": f"col_{col['room_id']}",
            "type": "column",
            "element_label": f"Column for {col['reason']}",
            "span_m": 0,
            "flags": [col["reason"]],
            "location_description": f"Position {col['position']}",
            "is_load_bearing": True,
            "area_m2": 0.3 * 0.3,
        }
        rec = recommend_materials(element, materials)
        recommendations.append(rec)
        if rec["top_3_materials"]:
            vol = 0.3 * 0.3 * 3.0
            total_cost += rec["top_3_materials"][0]["cost_per_m3_inr"] * vol

    # Structural warnings
    warnings = []
    for concern in concerns:
        if concern["severity"] == "critical":
            warnings.append(
                f"Room {concern['room_label']} has {concern['span_m']}m span — "
                f"RCC beam or steel frame mandatory"
            )
        elif concern["severity"] == "high":
            warnings.append(
                f"Room {concern['room_label']} has {concern['span_m']}m span — "
                f"RCC beam recommended"
            )

    return {
        "recommendations": recommendations,
        "total_cost_estimate_inr": round(total_cost, 0),
        "structural_warnings": warnings,
    }
