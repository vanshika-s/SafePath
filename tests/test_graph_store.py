"""Tests for graph_store.py — builds a tiny synthetic RouteGraph in memory."""
import math
import pickle
import tempfile
import os
import pytest
import numpy as np
from scipy.sparse import csr_matrix

from src.api.graph_store import RouteGraph, _dijkstra

# ---------------------------------------------------------------------------
# Helpers — build a minimal 4-node, 5-edge graph without touching disk
# ---------------------------------------------------------------------------
#
#  Layout (indices 0-3):
#
#    0 --(A)--> 1 --(B)--> 3
#    |          |
#   (C)        (D)
#    |          |
#    2 --(E)--> 3
#
#  Node coords (lat, lng):
#    0: (32.70, -117.20)
#    1: (32.71, -117.19)
#    2: (32.70, -117.19)
#    3: (32.71, -117.18)
#
#  Edges (from, to, length_m):
#    0 → 1  (A)  500
#    1 → 3  (B)  400
#    0 → 2  (C)  300
#    1 → 2  (D)  200   ← only exists in both directions for turn test
#    2 → 3  (E)  600
# ---------------------------------------------------------------------------

_N = 4

_FR  = np.array([0, 1, 0, 1, 2], dtype=np.int32)
_TO  = np.array([1, 3, 2, 2, 3], dtype=np.int32)
_LEN = np.array([500, 400, 300, 200, 600], dtype=np.float64)
_GRD = np.zeros(5, dtype=np.float64)   # flat grade
_WLK = np.ones(5,  dtype=np.float64)   # walk score 1.0
_INF = np.ones(5,  dtype=np.float64)   # infra score 1.0

_LATS = np.array([32.70, 32.71, 32.70, 32.71])
_LNGS = np.array([-117.20, -117.19, -117.19, -117.18])
_IDS  = np.array([0, 1, 2, 3], dtype=np.int64)

_NAMES = ["Street A", "Street B", "Street C", "Street D", "Street E"]

# Pre-sort edges by (from, to) for _edge_idx binary search
_sort = np.lexsort((_TO, _FR))
_ESORT_FROM = _FR[_sort]
_ESORT_TO   = _TO[_sort]
_ESORT_EIDX = _sort


def _make_rg() -> RouteGraph:
    """Construct a RouteGraph from numpy arrays — no files, no load()."""
    rg = RouteGraph.__new__(RouteGraph)

    rg.node_ids  = _IDS.copy()
    rg.node_lats = _LATS.copy()
    rg.node_lngs = _LNGS.copy()
    rg._sorted_ids = np.sort(_IDS)
    rg._sort_order = np.argsort(_IDS)

    rg.edge_from   = _FR.copy()
    rg.edge_to     = _TO.copy()
    rg.edge_length = _LEN.copy()
    rg.edge_grade  = _GRD.copy()
    rg.edge_walk   = _WLK.copy()
    rg.edge_infra  = _INF.copy()
    rg.edge_names  = list(_NAMES)

    rg._esort_from = _ESORT_FROM.copy()
    rg._esort_to   = _ESORT_TO.copy()
    rg._esort_eidx = _ESORT_EIDX.copy()

    dummy = np.ones(5, dtype=np.float64)
    rg._scores         = {}
    rg._safe_costs     = {}
    rg._balanced_costs = {}
    rg._crime_scores   = {}
    from src.api.graph_store import _COMBOS
    for key in _COMBOS:
        rg._scores[key]         = dummy.copy()
        rg._safe_costs[key]     = dummy.copy()
        rg._balanced_costs[key] = dummy.copy()
        rg._crime_scores[key]   = dummy.copy()

    rg._N = _N
    rg._build_runtime(_N)
    return rg


# ---------------------------------------------------------------------------
# Tests for _dijkstra
# ---------------------------------------------------------------------------

def _simple_csr():
    """4-node graph: 0→1 (1), 1→3 (1), 0→2 (5), 2→3 (1)."""
    fr   = [0, 1, 0, 2]
    to_  = [1, 3, 2, 3]
    data = [1.0, 1.0, 5.0, 1.0]
    return csr_matrix((data, (fr, to_)), shape=(4, 4))


class TestDijkstra:
    def test_shortest_path_found(self):
        csr  = _simple_csr()
        path = _dijkstra(csr, 0, 3)
        assert path == [0, 1, 3]

    def test_path_starts_at_origin(self):
        path = _dijkstra(_simple_csr(), 0, 3)
        assert path[0] == 0

    def test_path_ends_at_dest(self):
        path = _dijkstra(_simple_csr(), 0, 3)
        assert path[-1] == 3

    def test_same_origin_and_dest(self):
        path = _dijkstra(_simple_csr(), 2, 2)
        assert path == [2]

    def test_no_path_raises(self):
        # Disconnected: node 0 has no edges at all (4 → 0 direction)
        csr = csr_matrix(np.zeros((4, 4)))
        with pytest.raises(ValueError, match="No walking path"):
            _dijkstra(csr, 3, 0)

    def test_avoids_more_expensive_route(self):
        # 0→2 costs 5 then 2→3 costs 1 = 6 total; 0→1 costs 1 then 1→3 costs 1 = 2
        path = _dijkstra(_simple_csr(), 0, 3)
        assert 2 not in path, "Should not go through node 2 (expensive route)"


# ---------------------------------------------------------------------------
# Tests for RouteGraph methods
# ---------------------------------------------------------------------------

class TestNearestNode:
    def test_exact_match(self):
        rg = _make_rg()
        # Node 0 is at (32.70, -117.20)
        idx = rg.nearest_node(32.70, -117.20)
        assert idx == 0

    def test_nearest_to_node_3(self):
        rg  = _make_rg()
        idx = rg.nearest_node(32.71, -117.18)
        assert idx == 3

    def test_returns_int(self):
        rg = _make_rg()
        assert isinstance(rg.nearest_node(32.70, -117.20), int)


class TestPathLengthM:
    def test_single_edge_length(self):
        rg = _make_rg()
        # Edge 0→1 has length 500
        assert rg.path_length_m([0, 1]) == pytest.approx(500.0)

    def test_two_edge_length(self):
        rg = _make_rg()
        # 0→1 (500) + 1→3 (400) = 900
        assert rg.path_length_m([0, 1, 3]) == pytest.approx(900.0)

    def test_single_node_path_is_zero(self):
        rg = _make_rg()
        assert rg.path_length_m([0]) == pytest.approx(0.0)


class TestPathTimeMin:
    def test_returns_positive_int(self):
        rg  = _make_rg()
        t   = rg.path_time_min([0, 1, 3])
        assert isinstance(t, int)
        assert t >= 1

    def test_longer_path_takes_more_time(self):
        rg = _make_rg()
        t_short = rg.path_time_min([1, 3])      # 400 m
        t_long  = rg.path_time_min([0, 1, 3])   # 900 m
        assert t_long >= t_short


class TestPathCoords:
    def test_length_matches_path(self):
        rg    = _make_rg()
        path  = [0, 1, 3]
        coords = rg.path_coords(path)
        assert len(coords) == len(path)

    def test_coords_are_tuples(self):
        rg     = _make_rg()
        coords = rg.path_coords([0, 1])
        for c in coords:
            assert isinstance(c, tuple)
            assert len(c) == 2

    def test_first_coord_matches_node_0(self):
        rg     = _make_rg()
        coords = rg.path_coords([0, 1])
        assert coords[0] == pytest.approx((32.70, -117.20), abs=1e-6)


class TestPathEdgeScores:
    def test_returns_one_dict_per_edge(self):
        rg     = _make_rg()
        scores = rg.path_edge_scores([0, 1, 3], "short", False)
        assert len(scores) == 2   # two edges in 3-node path

    def test_each_dict_has_required_keys(self):
        rg     = _make_rg()
        scores = rg.path_edge_scores([0, 1], "medium", True)
        for key in ("street", "safety_score", "crime_score", "infrastructure",
                    "walk_score", "length_m", "safety_cost"):
            assert key in scores[0], f"missing key: {key}"

    def test_length_m_is_positive(self):
        rg     = _make_rg()
        scores = rg.path_edge_scores([0, 1], "long", False)
        assert scores[0]["length_m"] > 0


class TestPathSteps:
    def test_empty_for_single_node(self):
        rg = _make_rg()
        assert rg.path_steps([0]) == []

    def test_last_step_is_arrive(self):
        rg    = _make_rg()
        steps = rg.path_steps([0, 1, 3])
        assert steps[-1]["instruction"] == "Arrive at destination"

    def test_first_step_heads_direction(self):
        rg    = _make_rg()
        steps = rg.path_steps([0, 1, 3])
        assert steps[0]["instruction"].startswith("Head ")

    def test_steps_contain_required_keys(self):
        rg    = _make_rg()
        steps = rg.path_steps([0, 1, 3])
        for s in steps:
            for key in ("icon", "instruction", "distance"):
                assert key in s, f"step missing key: {key}"

    def test_two_node_path_has_two_steps(self):
        rg    = _make_rg()
        steps = rg.path_steps([0, 1])
        # "Head X on ..." + "Arrive at destination"
        assert len(steps) == 2

    def test_consecutive_same_street_merged(self):
        """Two edges with the same name should be merged into one step."""
        rg = _make_rg()
        # Rename edge 0→1 and 1→3 to the same name so they'll merge
        rg.edge_names[0] = "Main St"   # edge 0→1
        rg.edge_names[1] = "Main St"   # edge 1→3
        steps = rg.path_steps([0, 1, 3])
        street_steps = [s for s in steps if "Main St" in s["instruction"]]
        assert len(street_steps) == 1, "Same-name segments should be merged"
