"""
Data loader for SafePath — Streamlit Community Cloud deployment.

Setup (run once locally in scoring-engine.ipynb):
    import shutil
    shutil.make_archive("data/processed/fast_graph", "zip", "data/processed/fast_graph")

Upload fast_graph.zip and crime_final_gdf.gpkg to Google Drive (public share links).

Local development — add to .streamlit/secrets.toml (never commit this file):
    GDRIVE_FAST_GRAPH_ID = "your_file_id_here"
    GDRIVE_CRIME_ID      = "your_file_id_here"

Streamlit Cloud — add the same keys in App Settings → Secrets.
"""

import os
import zipfile
import geopandas as gpd

_FAST_GRAPH_DIR = "data/processed/fast_graph"
_MARKER         = f"{_FAST_GRAPH_DIR}/node_ids.npy"
_ZIP_PATH       = "data/processed/fast_graph.zip"
_CRIME_PATH     = "data/processed/crime_final_gdf.gpkg"

# Module-level singletons — loaded once, reused for every request.
_graph = None
_crime = None


def _get_secret(key: str) -> str:
    """Read a secret from st.secrets (Streamlit Cloud) or os.environ (fallback)."""
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        val = os.environ.get(key, "")
        if not val:
            raise EnvironmentError(
                f"Missing secret: '{key}'. "
                f"Add it to .streamlit/secrets.toml for local dev, "
                f"or App Settings → Secrets on Streamlit Cloud."
            )
        return val


def _gdrive_download(file_id: str, output: str) -> None:
    """Download a file from Google Drive using gdown."""
    try:
        import gdown
    except ImportError:
        raise ImportError("gdown is required. Run: pip install gdown")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    url = f"https://drive.google.com/uc?id={file_id}&confirm=t"
    gdown.download(url, output=output, quiet=False, fuzzy=True)


def download_data() -> None:
    """Download missing data files from Google Drive.

    Secrets required (set in .streamlit/secrets.toml or Streamlit Cloud):
      GDRIVE_FAST_GRAPH_ID  →  fast_graph.zip
      GDRIVE_CRIME_ID       →  crime_final_gdf.gpkg
    """
    graph_id = _get_secret("GDRIVE_FAST_GRAPH_ID")
    crime_id = _get_secret("GDRIVE_CRIME_ID")

    # Download and unzip fast graph
    if not os.path.exists(_MARKER):
        if not os.path.exists(_ZIP_PATH):
            print("Downloading fast_graph.zip from Google Drive...")
            _gdrive_download(graph_id, _ZIP_PATH)
        print("Extracting fast_graph.zip...")
        with zipfile.ZipFile(_ZIP_PATH, "r") as z:
            z.extractall(_FAST_GRAPH_DIR)
        print("Fast graph ready.")

    # Download crime points
    if not os.path.exists(_CRIME_PATH):
        print("Downloading crime_final_gdf.gpkg from Google Drive...")
        _gdrive_download(crime_id, _CRIME_PATH)
        print("Crime data ready.")


def load_graph():
    """Load RouteGraph from pre-built numpy files. ~300-500ms. Singleton."""
    global _graph
    if _graph is not None:
        return _graph
    from src.api.graph_store import RouteGraph
    _graph = RouteGraph.load(_FAST_GRAPH_DIR)
    return _graph


def load_crime_points() -> dict:
    """Load crime points pre-split into day/night lists. Singleton.

    Returns {"day": [(lat, lng), ...], "night": [(lat, lng), ...]}.
    """
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
