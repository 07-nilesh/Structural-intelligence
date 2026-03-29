"""Tests for Stage 5: Explainer (Gemini + Template Fallback)"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from explainer import (
    get_cache_key, generate_template_explanation,
    generate_all_explanations, load_cache, save_cache,
)

FALLBACK_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fallback")


def load_plan(name):
    with open(os.path.join(FALLBACK_DIR, f"{name}_coords.json"), "r") as f:
        return json.load(f)


def build_test_data():
    """Build test data by running stages 1-4."""
    from geometry import reconstruct_geometry
    from material_optimizer import recommend_all_materials
    data = load_plan("plan_a")
    geometry = reconstruct_geometry(data)
    materials = recommend_all_materials(geometry)
    return geometry, materials


class TestCacheKey:
    def test_same_inputs_same_key(self):
        k1 = get_cache_key("w1", "rcc", 5.0)
        k2 = get_cache_key("w1", "rcc", 5.0)
        assert k1 == k2

    def test_different_span_different_key(self):
        k1 = get_cache_key("w1", "rcc", 5.0)
        k2 = get_cache_key("w1", "rcc", 6.0)
        assert k1 != k2, "Cache key must change when span changes"

    def test_different_material_different_key(self):
        k1 = get_cache_key("w1", "rcc", 5.0)
        k2 = get_cache_key("w1", "steel_frame", 5.0)
        assert k1 != k2

    def test_different_element_different_key(self):
        k1 = get_cache_key("w1", "rcc", 5.0)
        k2 = get_cache_key("w2", "rcc", 5.0)
        assert k1 != k2


class TestTemplateExplanation:
    def test_generates_text_for_load_bearing(self):
        element = {
            "type": "load_bearing_wall",
            "element_label": "Wall w1 (horizontal, 14.0m)",
            "span_m": 3.0,
            "is_load_bearing": True,
        }
        recommendation = {
            "material_name": "Fly Ash Brick",
            "strength_mpa": 10,
            "cost_per_m3_inr": 4000,
            "durability_score": 8,
            "score": 62.5,
        }
        text = generate_template_explanation(element, recommendation, [], [])
        assert "Fly Ash Brick" in text
        assert "10" in text  # MPa cited
        assert "4,000" in text or "4000" in text  # Cost cited
        assert "load-bearing" in text

    def test_generates_text_for_partition(self):
        element = {
            "type": "partition_wall",
            "element_label": "Wall w6 (horizontal, 7.0m)",
            "span_m": 2.0,
            "is_load_bearing": False,
        }
        recommendation = {
            "material_name": "AAC Blocks",
            "strength_mpa": 4,
            "cost_per_m3_inr": 4500,
            "durability_score": 8,
            "score": 71.2,
        }
        text = generate_template_explanation(element, recommendation, [], [])
        assert "AAC Blocks" in text
        assert "partition" in text

    def test_critical_span_warning(self):
        element = {
            "type": "long_span",
            "element_label": "Wall w5 (vertical, 10.0m)",
            "span_m": 6.0,
            "is_load_bearing": True,
        }
        recommendation = {
            "material_name": "Steel Frame",
            "strength_mpa": 250,
            "cost_per_m3_inr": 18000,
            "durability_score": 9,
            "score": 85.0,
        }
        text = generate_template_explanation(element, recommendation, [], [])
        assert "6.0m" in text or "6m" in text
        assert "5m" in text  # Threshold mentioned
        assert "CRITICAL" in text

    def test_runner_up_mentioned(self):
        element = {
            "type": "load_bearing_wall",
            "element_label": "Wall w1",
            "span_m": 3.0,
            "is_load_bearing": True,
        }
        recommendation = {
            "material_name": "Fly Ash Brick",
            "strength_mpa": 10,
            "cost_per_m3_inr": 4000,
            "durability_score": 8,
            "score": 62.5,
        }
        alternatives = [{
            "material_name": "RCC",
            "strength_mpa": 30,
            "cost_per_m3_inr": 12000,
            "durability_score": 10,
            "score": 55.0,
        }]
        text = generate_template_explanation(element, recommendation, alternatives, [])
        assert "RCC" in text


class TestFullExplanationPipeline:
    def test_generates_explanations_for_all_elements(self):
        geometry, materials = build_test_data()
        # Ensure no GEMINI_API_KEY so template fallback is used
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            explanations = generate_all_explanations(geometry, materials)
            assert len(explanations) > 0
            for exp in explanations:
                assert "element_id" in exp
                assert "explanation" in exp
                assert len(exp["explanation"]) > 20  # Not empty
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key

    def test_explanations_have_required_fields(self):
        geometry, materials = build_test_data()
        old_key = os.environ.pop("GEMINI_API_KEY", None)
        try:
            explanations = generate_all_explanations(geometry, materials)
            for exp in explanations:
                assert "element_id" in exp
                assert "element_label" in exp
                assert "recommended_material" in exp
                assert "explanation" in exp
        finally:
            if old_key:
                os.environ["GEMINI_API_KEY"] = old_key
