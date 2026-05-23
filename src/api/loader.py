import os
import zipfile
import geopandas as gpd

_FAST_GRAPH_DIR = "data/processed/fast_graph"
_MARKER         = f"{_FAST_GRAPH_DIR}/node_ids.npy"
_ZIP_PATH       = "data/processed/fast_graph.zip"
_CRIME_PATH     = "data/processed/crime_final_gdf.gpkg"

_GDRIVE_FAST_GRAPH_ID = "1LTBFmsWq0YpY8GGColvX3lLxhUhumLyH"
_GDRIVE_CRIME_ID      = "1xD35hpR1NM5Sry_7Mxr0-gJRN-BllVEr"

_graph = None
_crime = None


def _gdrive_download(file_id: str, output: str) -> None:
    try:
        import gdown
    except ImportError:
        raise ImportError("gdown is required. Run: pip install gdown")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    url = f"https://drive.google.com/uc?id={file_id}&confirm=t"
    gdown.download(url, output=output, quiet=False)


def download_data() -> None:
    if not os.path.exists(_MARKER):
        if not os.path.exists(_ZIP_PATH):
            print("Downloading fast_graph.zip from Google Drive...")
            _gdrive_download(_GDRIVE_FAST_GRAPH_ID, _ZIP_PATH)
        print("Extracting fast_graph.zip...")
        with zipfile.ZipFile(_ZIP_PATH, "r") as z:
            z.extractall(_FAST_GRAPH_DIR)
        print("Fast graph ready.")

    if not os.path.exists(_CRIME_PATH):
        print("Downloading crime_final_gdf.gpkg from Google Drive...")
        _gdrive_download(_GDRIVE_CRIME_ID, _CRIME_PATH)
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
