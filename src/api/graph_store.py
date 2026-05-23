"""
Fast numpy/scipy graph representation for SafePath routing.

Replaces the NetworkX/pickle graph storage with numpy .npy arrays and
scipy sparse matrices. Loading drops from ~3-5 s (Python dict pickle)
to ~300-500 ms (raw C-array deserialisation + sparse-matrix rebuild).
"""

import math
import heapq
import os
import pickle

import numpy as np
from scipy.sparse import csr_matrix
from scipy.spatial import KDTree


# All 6 (length_type, is_night) combinations we pre-compute.
_COMBOS = [
    ("short",  False), ("short",  True),
    ("medium", False), ("medium", True),
    ("long",   False), ("long",   True),
]


class RouteGraph:
    """Lightweight graph built from numpy arrays — no NetworkX at runtime."""

    # ── Construction from NetworkX ─────────────────────────────────────────────

    @classmethod
    def from_nx(cls, G_nx) -> "RouteGraph":
        """Convert an OSMnx MultiDiGraph to RouteGraph (one-time, slow path)."""
        rg = cls.__new__(cls)

        # ── Nodes ──────────────────────────────────────────────────────────────
        node_list   = list(G_nx.nodes())
        N           = len(node_list)
        # Sorted for fast binary-search lookup (OSMnx ID → array index)
        sort_order  = np.argsort(node_list)
        rg.node_ids     = np.array(node_list, dtype=np.int64)
        rg.node_lats    = np.array([G_nx.nodes[n]["y"] for n in node_list], dtype=np.float64)
        rg.node_lngs    = np.array([G_nx.nodes[n]["x"] for n in node_list], dtype=np.float64)
        rg._sorted_ids  = rg.node_ids[sort_order]
        rg._sort_order  = sort_order.astype(np.int32)

        # ── Edges ──────────────────────────────────────────────────────────────
        raw = []
        id2i = {nid: i for i, nid in enumerate(node_list)}  # temp build dict
        for u, v, data in G_nx.edges(data=True):
            raw.append((
                id2i[u], id2i[v],
                float(data.get("length",               0)),
                float(data.get("grade",                0)),
                _name(data),
                float(data.get("walk_score",           0.5)),
                float(data.get("infrastructure_score", 0.5)),
                float(data.get("crime_score_short_day",    0.5)),
                float(data.get("crime_score_short_night",  0.5)),
                float(data.get("crime_score_medium_day",   0.5)),
                float(data.get("crime_score_medium_night", 0.5)),
                float(data.get("crime_score_long_day",     0.5)),
                float(data.get("crime_score_long_night",   0.5)),
            ))

        rg.edge_from   = np.array([e[0]  for e in raw], dtype=np.int32)
        rg.edge_to     = np.array([e[1]  for e in raw], dtype=np.int32)
        rg.edge_length = np.array([e[2]  for e in raw], dtype=np.float32)
        rg.edge_grade  = np.array([e[3]  for e in raw], dtype=np.float32)
        rg.edge_names  = [e[4]            for e in raw]
        rg.edge_walk   = np.array([e[5]  for e in raw], dtype=np.float32)
        rg.edge_infra  = np.array([e[6]  for e in raw], dtype=np.float32)

        crimes = {
            ("short",  False): np.array([e[7]  for e in raw], dtype=np.float32),
            ("short",  True):  np.array([e[8]  for e in raw], dtype=np.float32),
            ("medium", False): np.array([e[9]  for e in raw], dtype=np.float32),
            ("medium", True):  np.array([e[10] for e in raw], dtype=np.float32),
            ("long",   False): np.array([e[11] for e in raw], dtype=np.float32),
            ("long",   True):  np.array([e[12] for e in raw], dtype=np.float32),
        }

        # Sorted edge lookup arrays (replaces a large Python dict)
        lex = np.lexsort((rg.edge_to, rg.edge_from))
        rg._esort_from  = rg.edge_from[lex]
        rg._esort_to    = rg.edge_to[lex]
        rg._esort_eidx  = lex.astype(np.int32)  # original edge index at sorted position

        # ── Pre-compute scores / costs ─────────────────────────────────────────
        rg._scores = {}
        rg._safe_costs     = {}
        rg._balanced_costs = {}
        for (lt, night) in _COMBOS:
            W_C, W_W, W_S = (0.45, 0.25, 0.30) if night else (0.50, 0.25, 0.25)
            sc = W_C * crimes[(lt, night)] + W_W * rg.edge_walk + W_S * rg.edge_infra
            rg._scores[(lt, night)]         = sc.astype(np.float32)
            rg._safe_costs[(lt, night)]     = (rg.edge_length * (1 + 4 * (1 - sc))).astype(np.float32)
            rg._balanced_costs[(lt, night)] = (rg.edge_length * (1 + 2 * (1 - sc))).astype(np.float32)

        rg._N = N
        rg._build_runtime(N)
        return rg

    # ── Serialisation ──────────────────────────────────────────────────────────

    def save(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)

        # Nodes
        np.save(f"{directory}/node_ids.npy",   self.node_ids)
        np.save(f"{directory}/node_lats.npy",  self.node_lats)
        np.save(f"{directory}/node_lngs.npy",  self.node_lngs)
        np.save(f"{directory}/sorted_ids.npy", self._sorted_ids)
        np.save(f"{directory}/sort_order.npy", self._sort_order)

        # Edges (numerical)
        np.save(f"{directory}/edge_from.npy",   self.edge_from)
        np.save(f"{directory}/edge_to.npy",     self.edge_to)
        np.save(f"{directory}/edge_length.npy", self.edge_length)
        np.save(f"{directory}/edge_grade.npy",  self.edge_grade)
        np.save(f"{directory}/edge_walk.npy",   self.edge_walk)
        np.save(f"{directory}/edge_infra.npy",  self.edge_infra)

        # Edge lookup (sorted arrays — no large Python dict)
        np.save(f"{directory}/esort_from.npy",  self._esort_from)
        np.save(f"{directory}/esort_to.npy",    self._esort_to)
        np.save(f"{directory}/esort_eidx.npy",  self._esort_eidx)

        # Edge names (strings — must pickle, but small relative to the graph)
        with open(f"{directory}/edge_names.pkl", "wb") as f:
            pickle.dump(self.edge_names, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Pre-computed score / cost arrays
        for (lt, night) in _COMBOS:
            tod = "night" if night else "day"
            np.save(f"{directory}/score_{lt}_{tod}.npy",   self._scores[(lt, night)])
            np.save(f"{directory}/safecost_{lt}_{tod}.npy",self._safe_costs[(lt, night)])
            np.save(f"{directory}/balcost_{lt}_{tod}.npy", self._balanced_costs[(lt, night)])

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
        for (lt, night) in _COMBOS:
            tod = "night" if night else "day"
            rg._scores[(lt, night)]         = np.load(f"{directory}/score_{lt}_{tod}.npy")
            rg._safe_costs[(lt, night)]     = np.load(f"{directory}/safecost_{lt}_{tod}.npy")
            rg._balanced_costs[(lt, night)] = np.load(f"{directory}/balcost_{lt}_{tod}.npy")

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
        scores = self._scores[(lt, night)]
        result = []
        for u, v in zip(path[:-1], path[1:]):
            ei = self._edge_idx(u, v)
            result.append({
                "street":         self.edge_names[ei],
                "safety_score":   round(float(scores[ei]),          3),
                "infrastructure": round(float(self.edge_infra[ei]), 3),
                "walk_score":     round(float(self.edge_walk[ei]),   3),
                "length_m":       round(float(self.edge_length[ei]), 1),
            })
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


def _name(data: dict) -> str:
    n = data.get("name")
    if isinstance(n, list):
        n = n[0] if n else None
    return n or "Unnamed Road"
