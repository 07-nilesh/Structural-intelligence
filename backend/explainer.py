"""
explainer.py — Stage 5: LLM-Powered Explainability

Generates plain-English, evidence-backed explanations for every
material recommendation using Google Gemini 2.5 Flash (Free Tier)
with a span-aware local caching layer for offline reliability.

Cache Key Fix: The span_m is injected into the cache key, so if you
stretch a wall during testing, the cache auto-invalidates and the LLM
generates a fresh, dimensionally accurate explanation.
"""

import os
import json
import hashlib
from typing import Dict, Optional
from pathlib import Path

# ---------------------------------------------------------------------------
# Cache layer (span-aware)
# ---------------------------------------------------------------------------
CACHE_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "explanation_cache"


def get_cache_key(element_id: str, material_id: str, span_m: float) -> str:
    """Include span_m so geometric changes invalidate stale caches."""
    return hashlib.md5(f"{element_id}:{material_id}:{span_m:.2f}".encode()).hexdigest()


def load_cache() -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "cache.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / "cache.json"
    cache_path.write_text(json.dumps(cache, indent=2))


# ---------------------------------------------------------------------------
# Gemini API call (Free Tier — Google AI Studio)
# ---------------------------------------------------------------------------
def call_gemini_api(prompt: str) -> Optional[str]:
    """
    Call Google Gemini 2.5 Flash API.
    Falls back to template if no API key or import fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None  # Will trigger template fallback

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except ImportError:
        print("[Explainer] google-generativeai not installed — using template fallback")
        return None
    except Exception as e:
        print(f"[Explainer] Gemini API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Template-based fallback (for offline / no API key scenarios)
# ---------------------------------------------------------------------------
def generate_template_explanation(element: dict, recommendation: dict,
                                   alternatives: list, concerns: list) -> str:
    """Generate structured explanation using templates with real numbers."""
    mat = recommendation
    mat_name = mat["material_name"]
    strength = mat["strength_mpa"]
    cost = mat["cost_per_m3_inr"]
    durability = mat.get("durability_score", "N/A")
    score = mat["score"]
    etype = element.get("type", "wall")
    label = element.get("element_label", "this element")
    span = element.get("span_m", 0)
    is_lb = element.get("is_load_bearing", False)

    # Build weight context
    from material_optimizer import ELEMENT_WEIGHTS
    weights = ELEMENT_WEIGHTS.get(etype, ELEMENT_WEIGHTS["partition_wall"])
    strength_pct = int(weights["strength"] * 100)
    cost_pct = int(weights["cost"] * 100)
    durability_pct = int(weights["durability"] * 100)

    # Get runner-up info
    runner_up = alternatives[0] if alternatives else None
    runner_text = ""
    if runner_up:
        runner_text = (
            f"{runner_up['material_name']} was not selected despite "
            f"{'higher' if runner_up['strength_mpa'] > strength else 'comparable'} "
            f"strength ({runner_up['strength_mpa']} MPa) because its cost "
            f"(₹{runner_up['cost_per_m3_inr']:,}/m³) "
            f"{'exceeds' if runner_up['cost_per_m3_inr'] > cost else 'provides no benefit over'} "
            f"the recommended option at this span length."
        )

    # Build main explanation
    parts = []

    # WHY this material
    parts.append(
        f"{mat_name} ({strength} MPa, ₹{cost:,}/m³) is recommended for "
        f"{label} because it achieved the highest tradeoff score of {score}/100 "
        f"among eligible materials."
    )

    # WHAT tradeoff
    if is_lb:
        parts.append(
            f"Since this is a load-bearing element, "
            f"strength was weighted at {strength_pct}% in the scoring formula — "
            f"structural failure risk takes priority over cost savings "
            f"(weighted at {cost_pct}%)."
        )
    else:
        parts.append(
            f"As a partition wall with no structural load, cost was weighted at "
            f"{cost_pct}% while strength needed only {strength_pct}% — "
            f"prioritizing economy without compromising room division integrity."
        )

    # Structural concern
    if span > 5.0:
        parts.append(
            f"CRITICAL: This element spans {span}m, exceeding the 5m threshold. "
            f"Only materials with ≥30 MPa compressive strength are structurally eligible — "
            f"lighter materials (AAC blocks, hollow blocks) were automatically excluded."
        )
    elif span > 4.0:
        parts.append(
            f"Note: This element spans {span}m, exceeding the 4m threshold where "
            f"RCC beam support is recommended for adequate load distribution."
        )
    elif concerns:
        concern_text = concerns[0] if isinstance(concerns[0], str) else concerns[0].get("concern", "")
        if concern_text:
            parts.append(concern_text)

    # Runner-up
    if runner_text:
        parts.append(runner_text)

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main explanation generator
# ---------------------------------------------------------------------------
def generate_explanation(element: dict, recommendation: dict,
                          geometry: dict) -> str:
    """Generate a plain-English explanation for a material recommendation."""
    cache = load_cache()
    cache_key = get_cache_key(
        element.get("element_id", ""),
        recommendation.get("material_id", ""),
        element.get("span_m", 0)
    )

    if cache_key in cache:
        return cache[cache_key]

    # Get alternatives (materials ranked 2-3)
    alternatives = element.get("alternatives", [])
    concerns = element.get("flags", [])

    # Build alternatives text
    alternatives_text = "\n".join([
        f"  - {a['material_name']}: score {a['score']}/100, "
        f"{a['strength_mpa']} MPa, ₹{a['cost_per_m3_inr']:,}/m³"
        for a in alternatives
    ]) if alternatives else "None"

    # Build structural flags
    structural_flags = ""
    if element.get("span_m", 0) > 5.0:
        structural_flags = (
            f"\nCRITICAL: This element has a span of {element['span_m']}m — "
            f"exceeds 5m threshold. Materials under 30 MPa are structurally ineligible."
        )

    # Build LLM prompt — forces specific number citation
    prompt = f"""You are a structural engineering consultant explaining a material recommendation to a non-expert client.

ELEMENT: {element.get('element_label', 'Wall')} ({element.get('type', 'wall')})
Location in plan: {element.get('location_description', 'Interior')}
Span: {element.get('span_m', 0):.1f}m | Area: {element.get('area_m2', 0):.1f}m² | Load-bearing: {element.get('is_load_bearing', False)}
{structural_flags}

RECOMMENDED: {recommendation.get('material_name', '')}
  Compressive strength: {recommendation.get('strength_mpa', 0)} MPa
  Cost: ₹{recommendation.get('cost_per_m3_inr', 0):,}/m³
  Durability: {recommendation.get('durability_score', 0)}/10
  Composite score: {recommendation.get('score', 0)}/100

ALTERNATIVES CONSIDERED:
{alternatives_text}

STRUCTURAL CONTEXT:
{json.dumps(concerns, indent=2) if concerns else 'No concerns'}

Write exactly 3-4 sentences:
1. WHY this material — cite the actual MPa and ₹/m³ numbers
2. WHAT tradeoff — explain why strength/cost weighting was set as it was for this element type
3. STRUCTURAL concern if any — cite span in meters if relevant, be specific
4. WHY the runner-up was not chosen — cite a specific number that made the difference

Rules:
- Always cite numbers (MPa, ₹/m³, metres) — never use vague words like "good"
- Be specific to THIS element, not generic
- If span exceeds 5m, state that lighter materials are structurally ineligible"""

    # Try Gemini API first
    response = call_gemini_api(prompt)

    # Fall back to template if API unavailable
    if not response:
        response = generate_template_explanation(
            element, recommendation, alternatives, concerns
        )

    # Cache the result
    cache[cache_key] = response
    save_cache(cache)

    return response


def generate_all_explanations(geometry_data: dict, material_results: dict) -> list:
    """Generate explanations for every material recommendation."""
    explanations = []
    recommendations = material_results.get("recommendations", [])

    for rec in recommendations:
        top3 = rec.get("top_3_materials", [])
        if not top3:
            continue

        top_mat = top3[0]
        alternatives = top3[1:] if len(top3) > 1 else []

        element = {
            "element_id": rec["element_id"],
            "element_label": rec["element_label"],
            "type": rec["element_type"],
            "span_m": rec.get("span_m", 0),
            "is_load_bearing": rec["element_type"] in ["load_bearing_wall", "column", "long_span"],
            "location_description": rec.get("element_label", ""),
            "area_m2": 0,
            "alternatives": alternatives,
            "flags": rec.get("structural_flags", []),
        }

        explanation = generate_explanation(element, top_mat, geometry_data)

        explanations.append({
            "element_id": rec["element_id"],
            "element_label": rec["element_label"],
            "recommended_material": top_mat["material_name"],
            "explanation": explanation,
        })

    return explanations
