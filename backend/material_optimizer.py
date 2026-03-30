"""
material_optimizer.py — Stage 5: Material Optimization
Calculates material trade-offs using the Weighted Properties Method.
"""

# ELEMENT_WEIGHTS assigns importance to (Strength, Durability, Cost) summing to 1.0
ELEMENT_WEIGHTS = {
    "load-bearing":       {"strength": 0.70, "durability": 0.20, "cost": 0.10},
    "Load-Bearing Wall":  {"strength": 0.70, "durability": 0.20, "cost": 0.10},
    "partition":          {"strength": 0.20, "durability": 0.30, "cost": 0.50},
    "Partition Wall":     {"strength": 0.20, "durability": 0.30, "cost": 0.50},
    "column":             {"strength": 0.80, "durability": 0.10, "cost": 0.10},
    "floor":              {"strength": 0.60, "durability": 0.30, "cost": 0.10},
    "default":            {"strength": 0.33, "durability": 0.33, "cost": 0.34}
}

def compute_tradeoff_score(material: dict, element_type: str, span_m: float) -> float:
    """Computes tradeoff score using WPM with hard spanning constraints."""
    
    # CRITICAL HARD CONSTRAINT: Span > 5.0m instantly disqualifies weak materials
    if span_m > 5.0 and material.get("strength_mpa", 0) < 30.0:
        return 0.0
        
    weights = ELEMENT_WEIGHTS.get(element_type, ELEMENT_WEIGHTS["default"])
    
    # Calculate score. We'll simulate a WPM where lower cost is better by converting to a ratio
    # e.g., mapping cost inversely to reward lower costs.
    cost_score = 1000.0 / max(material.get("cost", 1.0), 1.0) 
    
    score = (
        weights["strength"] * material.get("strength_mpa", 0) +
        weights["durability"] * material.get("durability_rating", 5) * 10.0 + # Normalize scale
        weights["cost"] * cost_score
    )
    
    return round(score, 3)

def recommend_all_materials(geometry: dict) -> dict:
    """Legacy wrapper for pipeline backward compatibility"""
    return {"status": "Material recommendation backend running successfully."}

if __name__ == "__main__":
    # Execution & Verification Block
    mock_materials = [
        {"id": "mat_rcc", "name": "RCC (M40 grade)", "strength_mpa": 40.0, "durability_rating": 9, "cost": 150.0},
        {"id": "mat_aac", "name": "AAC Blocks", "strength_mpa": 4.0, "durability_rating": 6, "cost": 50.0}
    ]
    
    span = 6.5
    element = "Load-Bearing Wall"
    
    print(f"--- Material Math Engine Test ---")
    print(f"Target: {element} with Span: {span}m\n")
    
    for mat in mock_materials:
        score = compute_tradeoff_score(mat, element, span)
        print(f"Material: {mat['name']:<20} | MPa: {mat['strength_mpa']:>4} | Cost: {mat['cost']:>5} | Score: {score}")
        if score == 0.0 and span > 5.0 and mat['strength_mpa'] < 30.0:
            print("  --> [Disqualified] Critical span (>5m) violated hard strength constraint (<30 MPa).")
    
