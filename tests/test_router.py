"""Tests for router.py — uses a mock RouteGraph so no data files are needed."""
import pytest
from unittest.mock import MagicMock

from src.api.router import get_routes


def _make_graph(path_len_m=1200):
    rg = MagicMock()
    rg.nearest_node.side_effect = lambda lat, lng: int(lat * 1000) % 100
    rg.route_fastest.return_value  = [0, 1, 2, 3]
    rg.route_safest.return_value   = [0, 4, 5, 3]
    rg.route_balanced.return_value = [0, 1, 5, 3]
    rg.path_length_m.return_value  = float(path_len_m)
    return rg


class TestGetRoutes:
    def test_returns_three_modes(self):
        rg = _make_graph()
        result = get_routes((32.71, -117.16), (32.73, -117.14), rg, is_night=False)
        assert set(result["routes"].keys()) == {"fastest", "safest", "balanced"}

    def test_length_type_short(self):
        rg = _make_graph(path_len_m=300)
        result = get_routes((32.71, -117.16), (32.73, -117.14), rg, is_night=False)
        assert result["lt"] == "short"

    def test_length_type_medium(self):
        rg = _make_graph(path_len_m=1000)
        result = get_routes((32.71, -117.16), (32.73, -117.14), rg, is_night=False)
        assert result["lt"] == "medium"

    def test_length_type_long(self):
        rg = _make_graph(path_len_m=5000)
        result = get_routes((32.71, -117.16), (32.73, -117.14), rg, is_night=False)
        assert result["lt"] == "long"

    def test_is_night_passed_through(self):
        rg = _make_graph()
        result = get_routes((32.71, -117.16), (32.73, -117.14), rg, is_night=True)
        assert result["is_night"] is True

    def test_paths_are_lists(self):
        rg = _make_graph()
        result = get_routes((32.71, -117.16), (32.73, -117.14), rg, is_night=False)
        for mode, path in result["routes"].items():
            assert isinstance(path, list), f"{mode} path should be a list"

    def test_nearest_node_called_for_both_endpoints(self):
        rg = _make_graph()
        start, end = (32.71, -117.16), (32.73, -117.14)
        get_routes(start, end, rg, is_night=False)
        calls = [c[0] for c in rg.nearest_node.call_args_list]
        assert (32.71, -117.16) in calls
        assert (32.73, -117.14) in calls
