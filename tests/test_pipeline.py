"""Integration-style tests for pipeline.py — all external calls are mocked."""
import pytest
from unittest.mock import patch, MagicMock


def _mock_rg():
    rg = MagicMock()
    rg.nearest_node.side_effect = lambda lat, lng: 0
    rg.route_fastest.return_value  = [0, 1, 2]
    rg.route_safest.return_value   = [0, 3, 2]
    rg.route_balanced.return_value = [0, 1, 2]
    rg.path_length_m.return_value  = 1500.0
    rg.path_time_min.return_value  = 18
    rg.path_coords.return_value    = [(32.71, -117.16), (32.72, -117.15)]
    rg.path_edge_scores.return_value = [
        {"safety_score": 0.75, "crime_score": 0.80, "infrastructure": 0.70, "walk_score": 0.65, "safety_cost": 600.0, "length_m": 750.0}
    ]
    rg.path_steps.return_value = [
        {"icon": "↑", "instruction": "Head north on Example St", "distance": "500 ft"},
        {"icon": "📍", "instruction": "Arrive at destination",    "distance": ""},
    ]
    return rg


class TestPipelineRun:
    def _run(self, is_night=False):
        rg   = _mock_rg()
        crime = {"day": [(32.71, -117.16)], "night": [(32.72, -117.15)]}
        with patch("src.api.pipeline.loader.load_graph",        return_value=rg), \
             patch("src.api.pipeline.loader.load_crime_points", return_value=crime), \
             patch("src.api.pipeline.day_night.is_night_now",   return_value=is_night), \
             patch("src.api.pipeline.geocoder.address_to_latlng",
                   side_effect=[(32.71, -117.16), (32.73, -117.14)]):
            from src.api import pipeline
            return pipeline.run("UCSD", "Balboa Park")

    def test_result_has_required_keys(self):
        result = self._run()
        assert {"routes", "is_night", "origin_coords", "destination_coords", "crime_pts"} <= result.keys()

    def test_three_route_modes(self):
        result = self._run()
        assert set(result["routes"].keys()) == {"fastest", "safest", "balanced"}

    def test_each_route_has_required_fields(self):
        result = self._run()
        for mode, r in result["routes"].items():
            for field in ("coords", "edge_scores", "steps", "distance_mi", "time_min"):
                assert field in r, f"{mode} missing '{field}'"

    def test_distance_is_positive(self):
        result = self._run()
        for mode, r in result["routes"].items():
            assert r["distance_mi"] > 0

    def test_crime_pts_uses_day_when_not_night(self):
        result = self._run(is_night=False)
        assert (32.71, -117.16) in result["crime_pts"]

    def test_crime_pts_uses_night_when_night(self):
        result = self._run(is_night=True)
        assert (32.72, -117.15) in result["crime_pts"]

    def test_origin_dest_coords_correct(self):
        result = self._run()
        assert result["origin_coords"] == (32.71, -117.16)
        assert result["destination_coords"] == (32.73, -117.14)
