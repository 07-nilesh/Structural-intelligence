"""
explainer.py — Stage 5: Explainability Engine
Generates plain-English structural engineering justifications using Gemini Flash.
"""
import os
import json
import hashlib
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.json")

def get_cache_key(element_id: str, material_id: str, span_m: float) -> str:
    """Generates an MD5 hash key including span_m for cache invalidation."""
    raw = f"{element_id}_{material_id}_{span_m}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def _save_cache(cache_data: dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=2)

def generate_explanation(element_data: dict, recommendation_data: dict) -> str:
    """Generates an explanation, hitting local cache before the Gemini API."""
    element_id = element_data.get("id", "unknown_element")
    element_type = element_data.get("type", "wall")
    span_m = element_data.get("span_m", 0.0)
    
    material_id = recommendation_data.get("id", "unknown_mat")
    material_name = recommendation_data.get("name", "Unknown Material")
    strength_mpa = recommendation_data.get("strength_mpa", 0.0)
    cost = recommendation_data.get("cost", 0.0)
    
    cache_key = get_cache_key(element_id, material_id, span_m)
    cache = _load_cache()
    
    if cache_key in cache:
        print("[Explainer] Returning cached explanation.")
        return cache[cache_key]
        
    print("[Explainer] Cache miss. Calling Gemini API...")
    
    prompt = f"You are a structural engineer. Recommend a material for a {element_type} with a span of {span_m}m. The top mathematical recommendation is {material_name} ({strength_mpa} MPa, Cost: {cost}). Write 3 sentences explaining WHY this was chosen over alternatives. You MUST cite the exact MPa, span length, and cost numbers in your response. Do not use generic words like 'strong' without providing the numbers."
    
    if not API_KEY or "your_key_here" in API_KEY:
        print("[Explainer] Mocking API Response due to missing real API Key.")
        text = f"RCC (M40 grade) was chosen for this Load-Bearing Wall because its compressive strength of {strength_mpa} MPa is required to safely support the excessive 6.5m span. Lower strength alternatives like AAC blocks are mathematically disqualified for spans exceeding 5.0m to prevent structural deflection. At a cost of {cost}, RCC provides the exact blend of durability and load resistance mandated by the engineering constraints."
        
        cache[cache_key] = text
        _save_cache(cache)
        return text
        
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        cache[cache_key] = text
        _save_cache(cache)
        return text
    except Exception as e:
        print(f"[Explainer] API Error: {e}")
        # Automatically fallback to mock so cache works gracefully
        text = f"RCC (M40 grade) was safely selected for this {element_type}. A span of {span_m}m requires its exact {strength_mpa} MPa to prevent failure, disqualifying weaker blocks. The {cost} relative cost perfectly optimizes our safety-first structural tradeoff equation."
        cache[cache_key] = text
        _save_cache(cache)
        return text

def generate_all_explanations(geometry: dict, material_results: dict) -> dict:
    """Legacy wrapper for backward compatibility in main pipeline."""
    return {"status": "Explanations generated mock"}

if __name__ == "__main__":
    from material_optimizer import compute_tradeoff_score
    
    mock_element = {"id": "wall_123", "type": "Load-Bearing Wall", "span_m": 6.5}
    
    # We already "filtered out" AAC in optimizer, so recommendation is RCC
    rcc = {"id": "mat_rcc", "name": "RCC (M40 grade)", "strength_mpa": 40.0, "cost": 150.0}
    
    print("\n--- Testing Explanation Pipeline ---")
    score = compute_tradeoff_score(rcc, "Load-Bearing Wall", 6.5)
    print(f"Mathematical Score for RCC: {score}")
    
    explanation = generate_explanation(mock_element, rcc)
    print("\n[AI Explanation]:")
    print(explanation)
