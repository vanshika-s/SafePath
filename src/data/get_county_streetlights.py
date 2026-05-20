import json
import time
from pathlib import Path

import requests


BASE_URL = "https://gis-public.sandiegocounty.gov/arcgis/rest/services/DPW/TRANSPORTATION20250106/MapServer/8/query"

OUT_PATH = Path("data/raw/county_dpw_streetlights.geojson")
PAGE_SIZE = 1000


def fetch_page(offset: int) -> list[dict]:
    """Fetch one page of County DPW streetlight records."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
    }

    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data.get("features", [])


def arcgis_feature_to_geojson(feature: dict):
    """Convert one ArcGIS point feature into GeoJSON."""
    geometry = feature.get("geometry", {})
    attributes = feature.get("attributes", {})

    x = geometry.get("x")
    y = geometry.get("y")

    if x is None or y is None:
        return None

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [x, y],
        },
        "properties": attributes,
    }


def main() -> None:
    all_geojson_features = []
    offset = 0

    while True:
        print(f"Fetching records starting at offset {offset}...")
        page = fetch_page(offset)

        if not page:
            break

        for feature in page:
            geojson_feature = arcgis_feature_to_geojson(feature)
            if geojson_feature is not None:
                all_geojson_features.append(geojson_feature)

        print(f"Total saved so far: {len(all_geojson_features)}")

        if len(page) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.2)

    geojson = {
        "type": "FeatureCollection",
        "name": "county_dpw_streetlights",
        "features": all_geojson_features,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(geojson, f)

    print(f"Done. Saved {len(all_geojson_features)} streetlights to {OUT_PATH}")


if __name__ == "__main__":
    main()