"""Clean City of San Diego streetlight data: raw GeoJSON -> interim + processed.

Source: data/raw/streetlights/streetlights_YYYYMMDD.geojson  (output of get_streetlights.py)
Output: data/interim/streetlights/streetlights_active_wgs84.geojson
        data/processed/streetlights/streetlights_processed.geojson

Cleaning rules (matches docs/data/streetlights/CLEANING_AND_VALIDATION.md):
  1. Drop rows where geometry is null or coords are outside SD bbox
     (-117.4, 32.4, -116.8, 33.2). In the 2026-04-30 snapshot this dropped 0 rows.
  2. Filter active set: STATUS == "A" AND MAPNG_STAT_CD in {"AB", "OP"}.
     (Codes confirmed by layer descriptor:
        STATUS:        A=Active, I=Inactive
        MAPNG_STAT_CD: AB=AS BUILT, OP=OPERATIONAL,
                       RM=REMOVED, AN=ABANDONED, NM=NOT MAPPED, PR=PROPOSED.)
  3. Flag (don't drop) duplicate SAPOBJNR with column dup_sapobjnr_flag.
  4. Add data_quality_flag = "ok".
  5. Interim keeps all original fields. Processed trims to scoring-relevant columns.

No external dependencies. Reads/writes GeoJSON directly via stdlib json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SD_BBOX = (-117.4, 32.4, -116.8, 33.2)
KEEP_MAPNG = {"AB", "OP"}


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def in_bbox(lon: float, lat: float) -> bool:
    return SD_BBOX[0] <= lon <= SD_BBOX[2] and SD_BBOX[1] <= lat <= SD_BBOX[3]


def clean(raw_fc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    raw_features = raw_fc.get("features", [])
    interim_features: list[dict[str, Any]] = []
    processed_features: list[dict[str, Any]] = []
    sapobj_seen: dict[str, bool] = {}

    counts = {
        "raw": len(raw_features),
        "dropped_null_geometry": 0,
        "dropped_out_of_bbox": 0,
        "dropped_status_not_a": 0,
        "dropped_mapng_not_kept": 0,
        "kept": 0,
        "dup_sapobjnr_flagged": 0,
    }

    for ft in raw_features:
        geom = ft.get("geometry")
        if geom is None:
            counts["dropped_null_geometry"] += 1
            continue
        coords = geom.get("coordinates")
        if not coords or len(coords) < 2:
            counts["dropped_null_geometry"] += 1
            continue
        lon, lat = coords[0], coords[1]
        if not in_bbox(lon, lat):
            counts["dropped_out_of_bbox"] += 1
            continue

        props = ft.get("properties") or {}
        status = props.get("STATUS")
        mapng = props.get("MAPNG_STAT_CD")
        if status != "A":
            counts["dropped_status_not_a"] += 1
            continue
        if mapng not in KEEP_MAPNG:
            counts["dropped_mapng_not_kept"] += 1
            continue

        # row passes — keep in interim with all original fields
        interim_features.append(ft)

        # processed: trimmed columns + dup flag + quality flag
        sap = props.get("SAPOBJNR")
        dup_flag = 0
        if sap is not None:
            if sap in sapobj_seen:
                dup_flag = 1
                counts["dup_sapobjnr_flagged"] += 1
            sapobj_seen[sap] = True

        processed_features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": {
                "sap_obj_nr": sap,
                "status": status,
                "mapng_stat_cd": mapng,
                "drawing_date": props.get("DRAWING_DATE"),
                "dup_sapobjnr_flag": dup_flag,
                "data_quality_flag": "ok",
            },
        })

    counts["kept"] = len(interim_features)

    crs = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}
    interim_fc = {"type": "FeatureCollection", "crs": crs, "features": interim_features}
    processed_fc = {"type": "FeatureCollection", "crs": crs, "features": processed_features}
    return interim_fc, processed_fc, counts


def write(fc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(fc, f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw",
        type=Path,
        required=True,
        help="path to raw GeoJSON (e.g. data/raw/streetlights/streetlights_20260430.geojson)",
    )
    parser.add_argument(
        "--interim",
        type=Path,
        default=Path("data/interim/streetlights/streetlights_active_wgs84.geojson"),
        help="output path for interim file",
    )
    parser.add_argument(
        "--processed",
        type=Path,
        default=Path("data/processed/streetlights/streetlights_processed.geojson"),
        help="output path for processed file",
    )
    args = parser.parse_args()

    if not args.raw.exists():
        print(f"raw file not found: {args.raw}", file=sys.stderr)
        return 2

    print(f"loading {args.raw}")
    raw_fc = load(args.raw)

    interim_fc, processed_fc, counts = clean(raw_fc)

    print(f"writing {args.interim}")
    write(interim_fc, args.interim)
    print(f"writing {args.processed}")
    write(processed_fc, args.processed)

    print()
    print("counts:")
    for k, v in counts.items():
        print(f"  {k:<28} {v:>8}")
    print()
    print(f"tie-out: raw {counts['raw']} - {counts['raw'] - counts['kept']} dropped = {counts['kept']} kept")
    return 0


if __name__ == "__main__":
    sys.exit(main())
