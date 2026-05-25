import os
import zipfile
import requests
import geopandas as gpd

_FAST_GRAPH_DIR = "data/processed/fast_graph"
_MARKER         = f"{_FAST_GRAPH_DIR}/node_ids.npy"
_ZIP_PATH       = "data/processed/fast_graph.zip"
_CRIME_PATH     = "data/processed/crime_final_gdf.gpkg"

_GCS_BASE       = "https://storage.googleapis.com/safepath-sd-data"
_GCS_GRAPH_URL  = f"{_GCS_BASE}/fast_graph.zip"
_GCS_CRIME_URL  = f"{_GCS_BASE}/crime_final_gdf.gpkg"

_graph = None
_crime = None


def _gcs_download(url: str, output: str) -> None:
    os.makedirs(os.path.dirname(output), exist_ok=True)
    print(f"Downloading {url} ...")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(output, "wb") as f:
            for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                f.write(chunk)
    print(f"Saved to {output}")


def download_data() -> None:
    if not os.path.exists(_MARKER):
        if not os.path.exists(_ZIP_PATH):
            _gcs_download(_GCS_GRAPH_URL, _ZIP_PATH)
        print("Extracting fast_graph.zip...")
        with zipfile.ZipFile(_ZIP_PATH, "r") as z:
            z.extractall(_FAST_GRAPH_DIR)
        print("Fast graph ready.")

    if not os.path.exists(_CRIME_PATH):
        _gcs_download(_GCS_CRIME_URL, _CRIME_PATH)
        print("Crime data ready.")


def load_graph():
    global _graph
    if _graph is not None:
        return _graph
    from src.api.graph_store import RouteGraph
    _graph = RouteGraph.load(_FAST_GRAPH_DIR)
    return _graph


def load_crime_points() -> dict:
    global _crime
    if _crime is not None:
        return _crime

    gdf      = gpd.read_file(_CRIME_PATH)
    day_mask = ((gdf["HOUR"] >= 6) & (gdf["HOUR"] < 20)).values
    lats     = gdf.geometry.y.values
    lngs     = gdf.geometry.x.values

    _crime = {
        "day":   [(float(la), float(lo)) for la, lo in zip(lats[day_mask],  lngs[day_mask])],
        "night": [(float(la), float(lo)) for la, lo in zip(lats[~day_mask], lngs[~day_mask])],
    }
    return _crime
