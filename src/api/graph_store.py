"""
Fast numpy/scipy graph representation for SafePath routing.

Only contains code used at runtime by the app. Build-time logic
(from_nx, save, _name) lives in notebooks/safety-score-edge.ipynb.
"""

import math
import heapq
import os
import pickle

import numpy as np
from scipy.sparse import csr_matrix
from scipy.spatial import KDTree


_COMBOS = [
    ("short",  False), ("short",  True),
    ("medium", False), ("medium", True),
    ("long",   False), ("long",   True),
]


class RouteGraph:
    """Lightweight graph built from numpy arrays — no NetworkX at runtime."""

    @classmethod
    def load(cls, directory: str) -> "RouteGraph":
        """Load from numpy files — no Python dict reconstruction."""
        rg = cls.__new__(cls)

        rg.node_ids    = np.load(f"{directory}/node_ids.npy")
        rg.node_lats   = np.load(f"{directory}/node_lats.npy")
        rg.node_lngs   = np.load(f"{directory}/node_lngs.npy")
        rg._sorted_ids = np.load(f"{directory}/sorted_ids.npy")
        rg._sort_order = np.load(f"{directory}/sort_order.npy")

        rg.edge_from   = np.load(f"{directory}/edge_from.npy")
        rg.edge_to     = np.load(f"{directory}/edge_to.npy")
        rg.edge_length = np.load(f"{directory}/edge_length.npy")
        rg.edge_grade  = np.load(f"{directory}/edge_grade.npy")
        rg.edge_walk   = np.load(f"{directory}/edge_walk.npy")
        rg.edge_infra  = np.load(f"{directory}/edge_infra.npy")

        rg._esort_from = np.load(f"{directory}/esort_from.npy")
        rg._esort_to   = np.load(f"{directory}/esort_to.npy")
        rg._esort_eidx = np.load(f"{directory}/esort_eidx.npy")

        with open(f"{directory}/edge_names.pkl", "rb") as f:
            rg.edge_names = pickle.load(f)

        rg._scores         = {}
        rg._safe_costs     = {}
        rg._balanced_costs = {}
        rg._crime_scores   = {}
        for (lt, night) in _COMBOS:
            tod = "night" if night else "day"
            rg._scores[(lt, night)]         = np.load(f"{directory}/score_{lt}_{tod}.npy")
            rg._safe_costs[(lt, night)]     = np.load(f"{directory}/safecost_{lt}_{tod}.npy")
            rg._balanced_costs[(lt, night)] = np.load(f"{directory}/balcost_{lt}_{tod}.npy")
            crime_path = f"{directory}/crime_{lt}_{tod}.npy"
            rg._crime_scores[(lt, night)]   = np.load(crime_path) if os.path.exists(crime_path) else None

        rg._N = len(rg.node_ids)
        rg._build_runtime(rg._N)
        return rg

    def _build_runtime(self, N: int) -> None:
        """Build KDTree + CSR matrices from the loaded arrays. ~200-400 ms total."""
        # KDTree for nearest-node lookup
        self._kdtree = KDTree(np.column_stack([self.node_lats, self.node_lngs]))

        # CSR weight matrices for Dijkstra (built from arrays, no large Python dicts)
        fr, to = self.edge_from, self.edge_to
        self._csr_length   = csr_matrix((self.edge_length, (fr, to)), shape=(N, N))
        self._csr_safe     = {k: csr_matrix((v, (fr, to)), shape=(N, N))
                              for k, v in self._safe_costs.items()}
        self._csr_balanced = {k: csr_matrix((v, (fr, to)), shape=(N, N))
                              for k, v in self._balanced_costs.items()}

    # ── Public routing API ─────────────────────────────────────────────────────

    def nearest_node(self, lat: float, lng: float) -> int:
        _, idx = self._kdtree.query([lat, lng])
        return int(idx)

    def route_fastest(self, orig: int, dest: int) -> list[int]:
        return _dijkstra(self._csr_length, orig, dest)

    def route_safest(self, orig: int, dest: int, lt: str, night: bool) -> list[int]:
        return _dijkstra(self._csr_safe[(lt, night)], orig, dest)

    def route_balanced(self, orig: int, dest: int, lt: str, night: bool) -> list[int]:
        return _dijkstra(self._csr_balanced[(lt, night)], orig, dest)

    def path_length_m(self, path: list[int]) -> float:
        return float(sum(
            self.edge_length[self._edge_idx(u, v)]
            for u, v in zip(path[:-1], path[1:])
        ))

    def path_time_min(self, path: list[int]) -> int:
        import numpy as np
        total = 0.0
        for u, v in zip(path[:-1], path[1:]):
            ei = self._edge_idx(u, v)
            length = float(self.edge_length[ei])
            grade  = float(self.edge_grade[ei])
            speed  = 1.4 * np.exp(-3.5 * abs(grade + 0.05))
            if speed > 0:
                total += length / speed
        return max(1, round(total / 60))

    def path_coords(self, path: list[int]) -> list[tuple[float, float]]:
        return [(float(self.node_lats[i]), float(self.node_lngs[i])) for i in path]

    def path_edge_scores(self, path: list[int], lt: str, night: bool) -> list[dict]:
        scores  = self._scores[(lt, night)]
        cost    = self._safe_costs[(lt, night)]
        crimes  = self._crime_scores.get((lt, night))
        result  = []
        for u, v in zip(path[:-1], path[1:]):
            ei  = self._edge_idx(u, v)
            row = {
                "street":         self.edge_names[ei],
                "safety_score":   round(float(scores[ei]),          3),
                "safety_cost":    round(float(cost[ei]),            3),
                "infrastructure": round(float(self.edge_infra[ei]), 3),
                "walk_score":     round(float(self.edge_walk[ei]),  3),
                "length_m":       round(float(self.edge_length[ei]),1),
            }
            if crimes is not None:
                row["crime_score"] = round(float(crimes[ei]), 3)
            result.append(row)
        return result

    def path_steps(self, path: list[int]) -> list[dict]:
        if len(path) < 2:
            return []

        segs = []
        for u, v in zip(path[:-1], path[1:]):
            ei = self._edge_idx(u, v)
            segs.append({
                "name": self.edge_names[ei],
                "length": float(self.edge_length[ei]),
                "u": u, "v": v,
            })

        # Merge consecutive same-name segments
        merged = [dict(segs[0])]
        for s in segs[1:]:
            if s["name"] == merged[-1]["name"]:
                merged[-1]["length"] += s["length"]
                merged[-1]["v"]       = s["v"]
            else:
                merged.append(dict(s))

        def _brg(n1, n2):
            la1 = math.radians(self.node_lats[n1])
            la2 = math.radians(self.node_lats[n2])
            dl  = math.radians(self.node_lngs[n2] - self.node_lngs[n1])
            x = math.sin(dl) * math.cos(la2)
            y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dl)
            return (math.degrees(math.atan2(x, y)) + 360) % 360

        def _cardinal(deg):
            return ["north","northeast","east","southeast",
                    "south","southwest","west","northwest"][round(deg / 45) % 8]

        def _turn(b1, b2):
            d = (b2 - b1 + 360) % 360
            if   d < 25 or d > 335: return "straight",    "↑"
            elif d < 75:             return "slight right", "↗"
            elif d < 150:            return "right",        "→"
            elif d < 210:            return "u-turn",       "↩"
            elif d < 285:            return "left",         "←"
            else:                    return "slight left",  "↖"

        def _fmt(m):
            ft = m * 3.28084
            return f"{int(round(ft / 50) * 50)} ft" if ft < 500 else f"{m * 0.000621371:.2f} mi"

        b0 = _brg(merged[0]["u"], merged[0]["v"])
        steps = [{"icon": "↑",
                  "instruction": f"Head {_cardinal(b0)} on {merged[0]['name']}",
                  "distance":    _fmt(merged[0]["length"])}]

        for i in range(1, len(merged)):
            b_in  = _brg(merged[i-1]["u"], merged[i-1]["v"])
            b_out = _brg(merged[i]["u"],   merged[i]["v"])
            turn, icon = _turn(b_in, b_out)
            instr = (f"Continue onto {merged[i]['name']}" if turn == "straight"
                     else f"Turn {turn} onto {merged[i]['name']}")
            steps.append({"icon": icon, "instruction": instr, "distance": _fmt(merged[i]["length"])})

        steps.append({"icon": "📍", "instruction": "Arrive at destination", "distance": ""})
        return steps

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _edge_idx(self, u: int, v: int) -> int:
        """Binary-search edge lookup — O(log E), no Python dict."""
        lo = int(np.searchsorted(self._esort_from, u))
        hi = int(np.searchsorted(self._esort_from, u + 1))
        if lo >= hi:
            return 0
        sub = int(np.searchsorted(self._esort_to[lo:hi], v))
        pos = lo + sub
        if pos < hi and self._esort_to[pos] == v:
            return int(self._esort_eidx[pos])
        return 0  # fallback


# ── Dijkstra (single-source single-target, early stopping) ────────────────────

def _dijkstra(csr: csr_matrix, orig: int, dest: int) -> list[int]:
    indptr = csr.indptr
    cols   = csr.indices
    data   = csr.data
    n      = csr.shape[0]

    dist = np.full(n, np.inf, dtype=np.float64)
    pred = np.full(n, -1,     dtype=np.int32)
    dist[orig] = 0.0
    heap = [(0.0, orig)]

    while heap:
        d, u = heapq.heappop(heap)
        if u == dest:
            break
        if d > dist[u]:
            continue
        for ptr in range(int(indptr[u]), int(indptr[u + 1])):
            v  = int(cols[ptr])
            nd = d + float(data[ptr])
            if nd < dist[v]:
                dist[v] = nd
                pred[v] = u
                heapq.heappush(heap, (nd, v))

    if np.isinf(dist[dest]):
        raise ValueError(f"No walking path found between these locations.")

    path, node = [], dest
    while node != -1:
        path.append(node)
        node = int(pred[node])
    return path[::-1]


