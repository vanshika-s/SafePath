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

    from datetime import datetime
    from zoneinfo import ZoneInfo
    from astral import LocationInfo
    from astral.sun import sun

    _sd_tz    = ZoneInfo("America/Los_Angeles")
    _now      = datetime.now(_sd_tz)
    _s        = sun(LocationInfo(latitude=32.8801, longitude=-117.234).observer,
                    date=_now.date(), tzinfo=_sd_tz)
    dawn_hour = _s["dawn"].hour + _s["dawn"].minute / 60
    dusk_hour = _s["dusk"].hour + _s["dusk"].minute / 60

    gdf      = gpd.read_file(_CRIME_PATH)
    hours    = gdf["HOUR"].values
    day_mask = ((hours >= dawn_hour) & (hours < dusk_hour))
    lats     = gdf.geometry.y.values
    lngs     = gdf.geometry.x.values

    _crime = {
        "day":   [(float(la), float(lo)) for la, lo in zip(lats[day_mask],  lngs[day_mask])],
        "night": [(float(la), float(lo)) for la, lo in zip(lats[~day_mask], lngs[~day_mask])],
    }
    return _crime
