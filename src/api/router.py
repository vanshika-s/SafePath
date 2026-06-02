"""Routing API — thin wrappers over RouteGraph that pipeline.py calls."""

from src.api.graph_store import RouteGraph


def get_routes(start: tuple, end: tuple, rg: RouteGraph, is_night: bool) -> dict:
    """Compute fastest, safest, and balanced routes between start and end (lat, lng).

    Returns {"routes": {mode: path}, "lt": length_type, "is_night": bool}.
    All weight lookups read from pre-computed numpy arrays — zero scoring cost.
    """
    orig = rg.nearest_node(start[0], start[1])
    dest = rg.nearest_node(end[0],   end[1])

    path_fast = rg.route_fastest(orig, dest)

    total_m     = rg.path_length_m(path_fast)
    lt          = "short" if total_m < 500 else "medium" if total_m <= 2000 else "long"

    path_safe = rg.route_safest(orig, dest, lt, is_night)
    path_bal  = rg.route_balanced(orig, dest, lt, is_night)

    return {
        "routes":   {"fastest": path_fast, "safest": path_safe, "balanced": path_bal},
        "lt":       lt,
        "is_night": is_night,
    }
