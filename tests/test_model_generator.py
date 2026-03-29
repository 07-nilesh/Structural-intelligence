"""Tests for Stage 3: 3D Model Generator"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from model_generator import (
    generate_3d_model, _create_box_mesh, _wall_mesh_from_px,
    _split_wall_at_openings, _create_floor_slab, _create_column_mesh,
    WALL_HEIGHT_M, WALL_THICKNESS_M, COLORS,
)

FALLBACK_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fallback")


def load_plan(name):
    with open(os.path.join(FALLBACK_DIR, f"{name}_coords.json"), "r") as f:
        return json.load(f)


def fake_geometry(plan_name):
    """Build a minimal geometry dict by running Stage 2 logic."""
    from geometry import reconstruct_geometry
    data = load_plan(plan_name)
    return reconstruct_geometry(data)


class TestBoxMeshCreation:
    def test_basic_box_mesh(self):
        mesh = _create_box_mesh(1.0, 1.5, 2.0, 3.0, 3.0, 0.23, "#ff0000", "w1", "load-bearing")
        assert mesh["type"] == "box"
        assert mesh["position"] == [1.0, 1.5, 2.0]
        assert mesh["dimensions"] == [3.0, 3.0, 0.23]
        assert mesh["color"] == "#ff0000"
        assert mesh["wall_id"] == "w1"

    def test_dimensions_never_zero(self):
        mesh = _create_box_mesh(0, 0, 0, 0, 0, 0, "#000")
        assert all(d >= 0.01 for d in mesh["dimensions"])


class TestWallMeshFromPixels:
    def test_horizontal_wall(self):
        mesh = _wall_mesh_from_px(
            50, 50, 750, 50, "horizontal", 50.0,
            0, 3.0, "#3b82f6", "w1", "load-bearing"
        )
        assert mesh is not None
        assert mesh["dimensions"][0] == 14.0  # 700px / 50 = 14m width
        assert mesh["dimensions"][1] == 3.0   # wall height
        assert mesh["dimensions"][2] == WALL_THICKNESS_M  # thickness

    def test_vertical_wall(self):
        mesh = _wall_mesh_from_px(
            750, 50, 750, 550, "vertical", 50.0,
            0, 3.0, "#10b981", "w2", "partition"
        )
        assert mesh is not None
        assert mesh["dimensions"][0] == WALL_THICKNESS_M  # thickness
        assert mesh["dimensions"][2] == 10.0  # 500px / 50 = 10m depth

    def test_zero_length_wall_returns_none(self):
        mesh = _wall_mesh_from_px(100, 50, 100, 50, "horizontal", 50.0, 0, 3.0, "#000", "w1", "p")
        assert mesh is None


class TestOpeningSegmentation:
    def test_wall_with_door_splits_into_segments(self):
        wall = {
            "id": "w5",
            "start": [400, 50],
            "end": [400, 550],
            "orientation": "vertical",
        }
        openings = [{
            "id": "o1", "wall_id": "w5",
            "position": [400, 175],
            "width_px": 45, "width_m": 0.9,
            "type": "door", "height_m": 2.1,
        }]
        segments = _split_wall_at_openings(wall, openings, 50.0, "#3b82f6", "load-bearing")
        # Should have: bottom segment, header above door, top segment
        assert len(segments) >= 2  # At minimum header + at least one side

    def test_wall_with_window_has_sill(self):
        wall = {
            "id": "w1",
            "start": [50, 50],
            "end": [750, 50],
            "orientation": "horizontal",
        }
        openings = [{
            "id": "o5", "wall_id": "w1",
            "position": [225, 50],
            "width_px": 60, "width_m": 1.2,
            "type": "window", "height_m": 1.2, "sill_m": 0.9,
        }]
        segments = _split_wall_at_openings(wall, openings, 50.0, "#3b82f6", "load-bearing")
        # Should have sill segment
        sill_segments = [s for s in segments if s["segment_type"] == "sill"]
        assert len(sill_segments) >= 1

    def test_wall_without_openings_returns_full_wall(self):
        wall = {
            "id": "w3",
            "start": [750, 550],
            "end": [50, 550],
            "orientation": "horizontal",
        }
        segments = _split_wall_at_openings(wall, [], 50.0, "#10b981", "partition")
        # With no openings, the function creates the full wall as one right/top segment
        assert len(segments) == 1


class TestFloorSlab:
    def test_floor_slab_created(self):
        walls = [
            {"start": [50, 50], "end": [750, 50]},
            {"start": [750, 50], "end": [750, 550]},
        ]
        slab = _create_floor_slab(walls, 50.0)
        assert slab["element_type"] == "floor"
        assert slab["position"][1] < 0  # Below ground level


class TestColumnMesh:
    def test_column_created(self):
        col = {"position": [575, 300], "room_id": "r4"}
        mesh = _create_column_mesh(col, 50.0)
        assert mesh["element_type"] == "column"
        assert mesh["color"] == COLORS["column"]


class TestFullModelGeneration:
    def test_plan_a_generates_meshes(self):
        geometry = fake_geometry("plan_a")
        model = generate_3d_model(geometry)
        assert "meshes" in model
        assert "labels" in model
        assert "metadata" in model
        assert len(model["meshes"]) > 0
        assert model["metadata"]["wall_height_m"] == WALL_HEIGHT_M

    def test_plan_b_generates_meshes(self):
        geometry = fake_geometry("plan_b")
        model = generate_3d_model(geometry)
        assert len(model["meshes"]) > 0
        # Should have at least 1 floor slab
        floors = [m for m in model["meshes"] if m["element_type"] == "floor"]
        assert len(floors) >= 1

    def test_all_meshes_have_valid_structure(self):
        geometry = fake_geometry("plan_a")
        model = generate_3d_model(geometry)
        for mesh in model["meshes"]:
            assert "type" in mesh
            assert "position" in mesh
            assert "dimensions" in mesh
            assert "color" in mesh
            assert len(mesh["position"]) == 3
            assert len(mesh["dimensions"]) == 3
            assert all(d > 0 for d in mesh["dimensions"])

    def test_labels_match_rooms(self):
        geometry = fake_geometry("plan_a")
        model = generate_3d_model(geometry)
        room_count = len(geometry["rooms"])
        assert len(model["labels"]) == room_count
