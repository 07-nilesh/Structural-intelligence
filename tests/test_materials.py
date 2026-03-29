"""Tests for Stage 4: Material Optimizer"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from material_optimizer import (
    compute_tradeoff_score, load_materials, recommend_materials,
    get_eligible_materials, ELEMENT_WEIGHTS, MAX_STRENGTH
)


@pytest.fixture
def materials():
    return load_materials()


class TestTradeoffScoring:
    def test_scores_are_bounded(self, materials):
        for mat in materials:
            for etype in ELEMENT_WEIGHTS:
                score = compute_tradeoff_score(mat, etype, span_m=3.0)
                assert 0.0 <= score <= 100.0

    def test_long_span_excludes_weak_materials(self, materials):
        aac = next(m for m in materials if m["id"] == "aac_block")
        score = compute_tradeoff_score(aac, "long_span", span_m=6.0)
        assert score == 0.0, "AAC blocks must be excluded for >5m spans"

    def test_steel_scores_well_for_long_span(self, materials):
        steel = next(m for m in materials if m["id"] == "steel_frame")
        score = compute_tradeoff_score(steel, "long_span", span_m=6.0)
        assert score > 50.0

    def test_rcc_scores_well_for_columns(self, materials):
        rcc = next(m for m in materials if m["id"] == "rcc")
        score = compute_tradeoff_score(rcc, "column", span_m=0)
        assert score > 30.0

    def test_weights_differ_by_element_type(self):
        lb = ELEMENT_WEIGHTS["load_bearing_wall"]
        part = ELEMENT_WEIGHTS["partition_wall"]
        assert lb["strength"] > part["strength"]
        assert part["cost"] > lb["cost"]

    def test_weight_percentages_sum_to_1(self):
        for etype, weights in ELEMENT_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"{etype} weights don't sum to 1.0"


class TestEligibility:
    def test_aac_eligible_for_partition(self):
        eligible = get_eligible_materials("partition_wall")
        assert "aac_block" in eligible

    def test_aac_not_eligible_for_column(self):
        eligible = get_eligible_materials("column")
        assert "aac_block" not in eligible

    def test_rcc_eligible_for_slab(self):
        eligible = get_eligible_materials("slab")
        assert "rcc" in eligible


class TestRecommendations:
    def test_top3_returned(self, materials):
        element = {
            "element_id": "w1",
            "type": "load_bearing_wall",
            "span_m": 3.0,
        }
        result = recommend_materials(element, materials)
        assert len(result["top_3_materials"]) == 3

    def test_rankings_descending(self, materials):
        element = {"element_id": "w1", "type": "partition_wall", "span_m": 2.0}
        result = recommend_materials(element, materials)
        scores = [m["score"] for m in result["top_3_materials"]]
        assert scores == sorted(scores, reverse=True)

    def test_long_span_only_strong_materials(self, materials):
        element = {"element_id": "w1", "type": "long_span", "span_m": 6.0}
        result = recommend_materials(element, materials)
        for mat in result["top_3_materials"]:
            if mat["score"] > 0:
                assert mat["strength_mpa"] >= 30

    def test_weight_rationale_present(self, materials):
        element = {"element_id": "w1", "type": "load_bearing_wall", "span_m": 3.0}
        result = recommend_materials(element, materials)
        for mat in result["top_3_materials"]:
            assert "weight_rationale" in mat
            assert "strength=" in mat["weight_rationale"]
