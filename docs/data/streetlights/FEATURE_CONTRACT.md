# Streetlight FEATURE_CONTRACT

> **Status:** `CLEANING_AND_VALIDATION.md` PASSes (zero FAIL, 2026-04-30). The processed source file is ready. L1–L5 themselves still need to run against the OSM walking graph — see §7 below for current state.

This file is consistent with the broader `docs/data-prep/handoff_v0/FEATURE_CONTRACT_v0.md`. Where they disagree, propose the change upstream.

## 1. Proposed route-level features (per OSM walking edge `(u, v, key)`)

| # | Feature | Definition | Unit | Required input columns | Calculation | Expected range | Validation status |
| - | - | - | - | - | - | - | - |
| L1 | `streetlight_count_50m` | operational streetlights within 50 m of edge | count | `geometry`, `status`, `mapng_stat_cd` | reproject edge to `EPSG:3857`; buffer 50 m; sjoin with active points; count | residential 2–10 | not-yet-supported |
| L2 | `streetlight_density_per_km` | lights per km of edge length | lights/km | L1 + `length_m` | `L1 / (length_m / 1000)` | residential 30–100, commercial 50–150 | not-yet-supported |
| L3 | `percent_route_with_nearby_lighting` | fraction of edge length with a light within 50 m | percent | edge `geometry`, lights | sample edge midline every ~10 m; for each, "any light within 50 m"; mean | 0–1 | not-yet-supported |
| L4 | `lighting_data_quality_flag` | regime tag for the edge | enum | `is_on_ucsd_campus` (from upstream contract F11) | rule-based | `{"city_layer", "ucsd_uncovered", "out_of_city"}` | always supported once F11 exists |
| L5 | `lighting_score` | normalized comfort score | unitless 0–1 | L1 + `length_m` + L4 | `clip((L1/length_m * 100) / lights_per_100m_p95, 0, 1)`; if L4 == `ucsd_uncovered`, force `0.5` | 0–1 (1 = best) | not-yet-supported |

## 2. Required input columns (from the processed file)

The processed file must expose these for L1–L5 to compute:

| Column | From | Why needed |
| - | - | - |
| `geometry` | streetlight processed | spatial join with edges |
| `status` | streetlight processed | sanity check (already filtered to `A`) |
| `mapng_stat_cd` | streetlight processed | sanity check |
| `data_quality_flag` | streetlight processed | downstream filtering |

The processed file must **not** carry rows with null geometry. The validation report enforces that.

## 3. Calculation method (pseudocode)

```
# inputs
processed_lights = read_geo("data/processed/streetlights/streetlights_processed.geojson")  # EPSG:4326
osm_edges = build_or_load_osm_walking_edges()                                              # EPSG:4326

# project for distance math
lights_3857 = processed_lights.to_crs(3857)
edges_3857  = osm_edges.to_crs(3857)
edges_3857["length_m"] = edges_3857.geometry.length

# L1
edges_buf = edges_3857.assign(geometry=edges_3857.buffer(50))
joined = sjoin(edges_buf, lights_3857, how="left", predicate="contains")
edges_3857["streetlight_count_50m"] = joined.groupby(level=0).size()

# L2
edges_3857["streetlight_density_per_km"] = (
    edges_3857["streetlight_count_50m"] / (edges_3857["length_m"] / 1000)
)

# L3 (sketch — sample midline, test buffer membership)
# left as an implementation detail in feature engineering

# L4
edges_3857["lighting_data_quality_flag"] = where_rule(
    is_on_ucsd_campus=edges_3857["is_on_ucsd_campus"]
)

# L5
p95 = (edges_3857["streetlight_count_50m"] / edges_3857["length_m"] * 100).quantile(0.95)
raw_score = (edges_3857["streetlight_count_50m"] / edges_3857["length_m"] * 100) / p95
edges_3857["lighting_score"] = raw_score.clip(0, 1)
edges_3857.loc[edges_3857["lighting_data_quality_flag"] == "ucsd_uncovered", "lighting_score"] = 0.5
```

## 4. Hard rules

1. Every feature is gated on `CLEANING_AND_VALIDATION.md` showing zero FAIL. No exceptions.
2. L4 must compute before L5; L5 depends on the regime tag.
3. `ucsd_uncovered` always falls back to neutral 0.5, never 0. Underweighting campus interior would push routes off campus.
4. No wattage / fixture-type weighting in v0. All operational lights count equally.
5. Open the optional sample CSV (`data/processed/streetlights/sample_lighting_features.csv`) only after Phase 5 PASS, and tag every row `data_status = REAL_PILOT_SAMPLE` (or `SCHEMA_TEST_ONLY_FAKE_VALUES` if shape-only). The bundle's `sample_route_features_v0.csv` already has a `lighting_score` column shaped like L5.

## 5. What each feature can and cannot answer

- **L1 / L2** — "how dense is the city's lighting infrastructure here." Not "how bright at midnight."
- **L3** — most useful for tooltip explanations ("87 % of this segment has a light within 50 m"). Not for ranking — use L5.
- **L4** — protects the routing engine from ranking dim-but-recorded above well-lit-but-unrecorded campus walks.
- **L5** — the field scoring code reads. Don't expose L1–L3 directly to routing weights; keep them for explanations.

## 6. Open feature questions

1. Is 50 m the right buffer? Sensitivity test on real data after validation passes.
2. Should L3 sample every 10 m or every edge node?
3. Should `STATUS == "W"` (warranty) lights count toward L1? Default yes; logged as open.
4. Should L4 distinguish `ucsd_uncovered` from `unknown_outside_city`? In v0 only the campus distinction is needed.

## 7. Validation status (real, as of 2026-04-30)

`CLEANING_AND_VALIDATION.md` is PASS. The processed source file (`data/processed/streetlights/streetlights_processed.geojson`, 55,506 features) is ready to feed L1–L5. The features themselves still require the OSM walking graph to compute, so they're "data-ready, computation pending" rather than "validated end-to-end."

| Feature | Source-data status | Computation status | Note |
| - | - | - | - |
| L1 `streetlight_count_50m` | data-ready (PASS) | not yet computed | needs OSM walking edges + buffer/sjoin |
| L2 `streetlight_density_per_km` | data-ready (PASS) | not yet computed | trivially derived once L1 + `length_m` exist |
| L3 `percent_route_with_nearby_lighting` | data-ready (PASS) | not yet computed | needs midline-sampling implementation |
| L4 `lighting_data_quality_flag` | rule-ready | not yet computed | **blocked on UCSD polygon decision** (SANGIS layer vs. hand-built bbox) |
| L5 `lighting_score` | data-ready (PASS) | not yet computed | depends on L1 + L4; p95 normalization requires the full edge set, so it's a single-pass step after L1 |

The "not-yet-supported" labels in §1's table reflect end-to-end status (data + computation). They flip to "supported" only after L1–L5 actually run against real OSM edges and a feature-feasibility sanity check passes.
