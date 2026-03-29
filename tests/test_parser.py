"""Tests for Stage 1: Floor Plan Parser"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from parser import (
    parse_floor_plan, load_fallback, snap_angle,
    deduplicate_lines, merge_collinear_segments, CV_CONFIG
)


class TestLineSnapping:
    def test_horizontal_snap(self):
        result = snap_angle(0, 0, 100, 3, tolerance_deg=5)
        assert result is not None
        _, sy1, _, sy2, orient = result
        assert orient == "horizontal"
        assert sy1 == sy2

    def test_vertical_snap(self):
        result = snap_angle(50, 0, 52, 100, tolerance_deg=5)
        assert result is not None
        sx1, _, sx2, _, orient = result
        assert orient == "vertical"
        assert sx1 == sx2

    def test_diagonal_rejected(self):
        result = snap_angle(0, 0, 100, 100, tolerance_deg=5)
        assert result is None

    def test_near_threshold(self):
        # 4.5 degrees should snap
        import math
        dx = 100
        dy = dx * math.tan(math.radians(4.5))
        result = snap_angle(0, 0, dx, dy, tolerance_deg=5)
        assert result is not None
        assert result[4] == "horizontal"


class TestDeduplication:
    def test_removes_near_duplicates(self):
        lines = [
            ((0, 50, 200, 50), "horizontal"),
            ((0, 52, 200, 52), "horizontal"),
            ((0, 100, 200, 100), "horizontal"),
        ]
        result = deduplicate_lines(lines, distance_threshold=8)
        assert len(result) == 2

    def test_keeps_distant_lines(self):
        lines = [
            ((0, 50, 200, 50), "horizontal"),
            ((0, 150, 200, 150), "horizontal"),
        ]
        result = deduplicate_lines(lines, distance_threshold=8)
        assert len(result) == 2


class TestMergeCollinear:
    def test_merges_nearby_segments(self):
        lines = [
            ((0, 50, 100, 50), "horizontal"),
            ((110, 50, 200, 50), "horizontal"),
        ]
        result = merge_collinear_segments(lines, gap_threshold=15)
        assert len(result) == 1
        assert result[0][0][0] == 0
        assert result[0][0][2] == 200

    def test_no_merge_with_gap(self):
        lines = [
            ((0, 50, 100, 50), "horizontal"),
            ((150, 50, 250, 50), "horizontal"),
        ]
        result = merge_collinear_segments(lines, gap_threshold=15)
        assert len(result) == 2


class TestFallback:
    def test_fallback_loads_plan_a(self):
        result = load_fallback("plan_a", "nonexistent.png")
        assert result["fallback_used"] is True
        assert len(result["walls"]) > 0
        assert len(result["rooms"]) > 0

    def test_fallback_by_filename(self):
        result = load_fallback(None, "plan_b.png")
        assert result["fallback_used"] is True

    def test_fallback_default(self):
        result = load_fallback(None, "unknown_anything.png")
        assert result["fallback_used"] is True


class TestFullParser:
    def test_parse_nonexistent_image(self):
        result = parse_floor_plan("nonexistent_image.png", "plan_a")
        assert result["fallback_used"] is True
        assert len(result["walls"]) > 0

    def test_parse_with_plan_id(self):
        result = parse_floor_plan("fake.png", "plan_b")
        assert result["fallback_used"] is True
        assert len(result["rooms"]) >= 5
