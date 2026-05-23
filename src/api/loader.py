import os
import geopandas as gpd
import osmnx as ox

GDRIVE_IDS = {
    "data/processed/sd_walk_graph_scored.graphml": "1a8dHYJQ_gtTop0rR2IICNbxDy2lORQdA",
    "data/processed/crime_final_gdf.gpkg":         "1xD35hpR1NM5Sry_7Mxr0-gJRN-BllVEr",
}

_FAST_GRAPH_DIR = "data/processed/fast_graph"
_MARKER         = f"{_FAST_GRAPH_DIR}/node_ids.npy"

# Module-level singletons — loaded once, reused for every request.
_graph = None
_crime = None


def _fresh(marker: str, src: str) -> bool:
    try:
        return (os.path.exists(marker) and
                os.path.getmtime(marker) >= os.path.getmtime(src))
    except OSError:
        return False


def download_data():
    """Download any missing data files from Google Drive using gdown."""
    try:
        import gdown
    except ImportError:
        raise ImportError("gdown is required. Run: pip install gdown")
    for path, file_id in GDRIVE_IDS.items():
        if os.path.exists(path):
            continue
        if not file_id:
            raise ValueError(f"No Google Drive ID set for {path}.")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        gdown.download(id=file_id, output=path, quiet=False)


def load_graph():
    """Load the RouteGraph (fast numpy format). Singleton — loads once per process.

    First-ever run  : parses GraphML (~20-30 s) → converts + saves fast format.
    Every restart   : loads ~30 .npy files + rebuilds KDTree + CSR (~300-500 ms).
    Stale detection : if graphml is newer than saved files, rebuilds automatically.
    """
    global _graph
    if _graph is not None:
        return _graph

    from src.api.graph_store import RouteGraph
    src = "data/processed/sd_walk_graph_scored.graphml"

    if _fresh(_MARKER, src):
        _graph = RouteGraph.load(_FAST_GRAPH_DIR)
    else:
        G_nx   = ox.load_graphml(src)
        _graph = RouteGraph.from_nx(G_nx)
        _graph.save(_FAST_GRAPH_DIR)

    return _graph


def load_crime_points() -> dict:
    """Load crime points pre-split into day/night coordinate arrays.

    Returns {"day": [(lat, lng), ...], "night": [(lat, lng), ...]}.
    All values are Python floats (JSON-serialisable).
    """
    global _crime
    if _crime is not None:
        return _crime

    gdf      = gpd.read_file("data/processed/crime_final_gdf.gpkg")
    day_mask = ((gdf["HOUR"] >= 6) & (gdf["HOUR"] < 20)).values
    lats     = gdf.geometry.y.values
    lngs     = gdf.geometry.x.values

    _crime = {
        "day":   [(float(la), float(lo)) for la, lo in zip(lats[day_mask],  lngs[day_mask])],
        "night": [(float(la), float(lo)) for la, lo in zip(lats[~day_mask], lngs[~day_mask])],
    }
    return _crime
