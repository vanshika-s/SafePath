"""Download City of San Diego streetlight data from the ArcGIS REST endpoint.

Source: City of San Diego Street Lights (ArcGIS Feature Layer, Planning/PLN_Mobility/1)
        https://webmaps.sandiego.gov/arcgis/rest/services/Planning/PLN_Mobility/MapServer/1
License: City of San Diego Open Data (verify license text on download day).

Usage:
    python src/data/get_streetlights.py --out data/raw/streetlights/

What this script does:
    1. Hits the layer descriptor (?f=pjson) to record fields and record count.
    2. Pages /query with outSR=4326, f=geojson, until exceededTransferLimit becomes false.
    3. Writes a single FeatureCollection GeoJSON file named streetlights_YYYYMMDD.geojson.
    4. Writes SOURCE_METADATA.yaml alongside it.

What this script DOES NOT do:
    - Clean the data. That happens in a separate notebook (Phase 3+).
    - Filter on STATUS or MAPNG_STAT_CD. Raw means raw.
    - Reproject. We request EPSG:4326 from the server.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import getpass
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

LAYER_DESCRIPTOR_URL = (
    "https://webmaps.sandiego.gov/arcgis/rest/services/Planning/PLN_Mobility/MapServer/1"
)
QUERY_URL = LAYER_DESCRIPTOR_URL + "/query"

DEFAULT_PAGE_SIZE = 2000
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (2, 4, 8)
POLITENESS_SLEEP_SECONDS = 0.25
USER_AGENT = "SafePath-streetlight-downloader/0.1 (DS3 student project)"


def _http_get_json(url: str, params: dict[str, Any] | None = None) -> Any:
    """GET a URL with retries; expect JSON back."""
    full = url + ("?" + urlencode(params) if params else "")
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(full, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=30) as resp:
                body = resp.read()
            return json.loads(body.decode("utf-8"))
        except HTTPError as exc:
            # Do not retry 4xx; those are our problem.
            if 400 <= exc.code < 500:
                raise
            last_error = exc
        except (URLError, json.JSONDecodeError) as exc:
            last_error = exc
        wait = RETRY_BACKOFF_SECONDS[attempt]
        print(f"  request failed ({last_error}); retrying in {wait}s", file=sys.stderr)
        time.sleep(wait)
    raise RuntimeError(f"giving up after {MAX_RETRIES} retries on {full}: {last_error}")


def fetch_layer_descriptor() -> dict:
    """Hit /1?f=pjson and return the layer descriptor dict."""
    return _http_get_json(LAYER_DESCRIPTOR_URL, {"f": "pjson"})


def fetch_page(offset: int, page_size: int) -> dict:
    """Fetch one page of features as a GeoJSON FeatureCollection dict."""
    params = {
        "where": "1=1",
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
        "resultOffset": offset,
        "resultRecordCount": page_size,
    }
    return _http_get_json(QUERY_URL, params)


def fetch_all_features(page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Page through the layer and return one merged FeatureCollection.

    Stops when:
      - a page has zero features, OR
      - the server flag exceededTransferLimit is False, OR
      - we have iterated more than 200 pages (sanity cap).
    """
    all_features: list = []
    offset = 0
    page_count = 0
    sanity_cap = 200

    while page_count < sanity_cap:
        page = fetch_page(offset, page_size)
        features = page.get("features", [])
        n = len(features)
        if n == 0:
            print(f"  page {page_count}: 0 features; stopping")
            break
        all_features.extend(features)
        page_count += 1
        offset += page_size
        more = bool(page.get("exceededTransferLimit") or page.get("properties", {}).get("exceededTransferLimit"))
        print(f"  page {page_count}: {n} features (running total {len(all_features)}; more={more})")
        if not more and n < page_size:
            break
        time.sleep(POLITENESS_SLEEP_SECONDS)
    else:
        raise RuntimeError(
            f"hit sanity cap of {sanity_cap} pages without finishing; check the loop"
        )

    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": all_features,
    }
    return fc


def observed_fields(feature_collection: dict) -> list[str]:
    """Pull the union of property keys across the first 100 features."""
    seen: set[str] = set()
    for feat in feature_collection.get("features", [])[:100]:
        seen.update((feat.get("properties") or {}).keys())
    return sorted(seen)


def write_outputs(out_dir: Path, descriptor: dict, fc: dict, fetched_by: str) -> None:
    """Write the data file, layer descriptor copy, and SOURCE_METADATA.yaml."""
    out_dir.mkdir(parents=True, exist_ok=True)
    today = _dt.datetime.now(_dt.timezone.utc)
    stamp = today.strftime("%Y%m%d")
    iso = today.strftime("%Y-%m-%dT%H:%M:%SZ")

    data_path = out_dir / f"streetlights_{stamp}.geojson"
    desc_path = out_dir / f"streetlights_layer_desc_{stamp}.json"
    meta_path = out_dir / "SOURCE_METADATA.yaml"

    with data_path.open("w", encoding="utf-8") as f:
        json.dump(fc, f)
    with desc_path.open("w", encoding="utf-8") as f:
        json.dump(descriptor, f, indent=2)

    record_count = len(fc.get("features", []))
    fields = observed_fields(fc)

    yaml_text = (
        "dataset: streetlights\n"
        f"source_url: {LAYER_DESCRIPTOR_URL}\n"
        "download_method: ArcGIS REST /query, paged GeoJSON\n"
        "download_query:\n"
        '  where: "1=1"\n'
        '  outFields: "*"\n'
        "  outSR: 4326\n"
        "  f: geojson\n"
        f"  resultRecordCount: {DEFAULT_PAGE_SIZE}\n"
        f"download_timestamp_utc: {iso}\n"
        "publisher: City of San Diego, Department of Transportation & Storm Water\n"
        "license: City of San Diego Open Data — see catalog page\n"
        "license_text_copied: |\n"
        "  <paste from catalog page on the day of download>\n"
        "fields_observed:\n" + "".join(f"  - {fn}\n" for fn in fields) +
        f"record_count: {record_count}\n"
        "crs_in_file: EPSG:4326\n"
        f"fetched_by: {fetched_by}\n"
        "notes: |\n"
        "  Replace this line with anything anomalous from the download.\n"
    )
    meta_path.write_text(yaml_text, encoding="utf-8")

    print(f"\nwrote: {data_path}  ({record_count} features)")
    print(f"wrote: {desc_path}")
    print(f"wrote: {meta_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/raw/streetlights"),
        help="output directory (default: data/raw/streetlights)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=f"records per page (default: {DEFAULT_PAGE_SIZE})",
    )
    parser.add_argument(
        "--fetched-by",
        type=str,
        default=getpass.getuser(),
        help="name to record in SOURCE_METADATA.yaml (defaults to OS user)",
    )
    args = parser.parse_args()

    print("1) fetching layer descriptor")
    descriptor = fetch_layer_descriptor()
    print(f"   layer name: {descriptor.get('name')!r}")
    print(f"   geometry:   {descriptor.get('geometryType')!r}")
    print(f"   maxRecord:  {descriptor.get('maxRecordCount')}")
    print(f"   field count: {len(descriptor.get('fields', []))}")

    print("\n2) paging /query for features")
    fc = fetch_all_features(page_size=args.page_size)

    print("\n3) writing outputs")
    write_outputs(args.out, descriptor, fc, fetched_by=args.fetched_by)

    n = len(fc.get("features", []))
    if n == 0:
        print("\nWARNING: zero features written. That probably means the query failed.")
        return 2
    print(f"\nDONE. {n} streetlights saved to {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
