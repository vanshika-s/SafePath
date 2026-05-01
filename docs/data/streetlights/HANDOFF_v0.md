# Streetlight HANDOFF v0

**Status:** Raw downloaded, interim + processed files written, validation + tie-out PASS. Feature engineering (L1–L5 route-level features) not started.
**Snapshot date:** 2026-04-30.
**Read time:** ~2 min.
**Sister docs (only 3, in this folder):** `DATA_SOURCE_AND_ACQUISITION.md`, `CLEANING_AND_VALIDATION.md`, `FEATURE_CONTRACT.md`.

## What this is

The City of San Diego streetlight dataset workstream. The goal is route-level lighting features that future scoring code can consume. The source data is now downloaded and cleaned; route-level features still need to be computed (they depend on the OSM walking graph, which is a separate workstream).

## What is done

- Source identified and cited → `DATA_SOURCE_AND_ACQUISITION.md`.
- **Raw data downloaded** → `data/raw/streetlights/streetlights_20260430.geojson` (56,049 features, 54 MB), plus `streetlights_layer_desc_20260430.json` and `SOURCE_METADATA.yaml`.
- **Interim file** → `data/interim/streetlights/streetlights_active_wgs84.geojson` (55,506 features after `STATUS == "A"` AND `MAPNG_STAT_CD ∈ {"AB","OP"}` filter; all original fields preserved).
- **Processed file** → `data/processed/streetlights/streetlights_processed.geojson` (55,506 features; trimmed to scoring-relevant columns: `sap_obj_nr`, `status`, `mapng_stat_cd`, `drawing_date`, `dup_sapobjnr_flag`, `data_quality_flag`, geometry).
- Cleaning, tie-out, and validation **all PASS** with zero FAIL → `CLEANING_AND_VALIDATION.md`.
- Candidate route-level features (L1–L5) defined → `FEATURE_CONTRACT.md`. Source data is now ready to feed them; the spatial-join step against OSM edges is the remaining work.

## What is not done

- Route-level features L1–L5 themselves haven't been computed (needs the OSM walking graph + a UCSD campus polygon).
- UCSD campus polygon source still open (SANGIS layer vs. hand-built bbox). This blocks L4.
- The optional `notebooks/streetlights-eda-and-cleaning.ipynb` was not committed; the EDA + cleaning ran as a one-shot script and the results live in `CLEANING_AND_VALIDATION.md`. If a teammate wants a notebook, the script's logic is reproducible from that doc.

Until L1–L5 are actually computed, **no lighting feature value exists per OSM edge** and **route rankings using lighting are still not meaningful**.

## Next steps (concrete, in order)

1. Decide UCSD campus polygon source (SANGIS vs. hand-built bbox). Required for L4.
2. Implement L1 (`streetlight_count_50m`) — buffer + sjoin processed lights against OSM walking edges. Pseudocode in `FEATURE_CONTRACT.md` §3.
3. Implement L4 (`lighting_data_quality_flag`) once the polygon is decided.
4. Implement L5 (`lighting_score`) — wraps L1 with p95 normalization and L4 fallback.
5. Sanity-check on 5–10 hand-picked OSM edges (UCSD-perimeter, UCSD-interior, downtown, residential, one corridor).

## Teammate-facing summary

Drop into `#safepath`:

```
quick update — streetlight dataset is downloaded, cleaned, and validated. branch is `docs/streetlight-workflow-v0`.

raw: 56,049 city-maintained streetlights (City of SD ArcGIS layer, snapshot 2026-04-30).
processed: 55,506 active lights (filtered STATUS=A and MAPNG_STAT_CD in {AB, OP}). 543 STATUS=I rows excluded. zero null geometries, zero SAPOBJNR duplicates. all validation + tie-out checks PASS.

3 surprises worth knowing:
1. UCSD campus interior actually has 229 city-maintained lights in this layer (more than i expected). still recommending the neutral-fallback rule for `lighting_score` because coverage is uneven.
2. WHERE_INSTALLED is 96% null. LOC_DESC is the real human-readable location field (99.94% populated).
3. ~10 of the 39 raw fields are 100% null. processed file drops them.

next is computing L1–L5 against OSM edges — but that's blocked on the UCSD-polygon decision. see FEATURE_CONTRACT.md if you want to weigh in. nothing to pick up unless you want.
```

## Reading path

| If you have | Read |
| - | - |
| 2 minutes | this file |
| 5 more minutes | `FEATURE_CONTRACT.md` (what the data is meant to feed) |
| about to download | `DATA_SOURCE_AND_ACQUISITION.md` |
| about to clean / validate | `CLEANING_AND_VALIDATION.md` |

## Beginner notes

- **Raw / interim / processed**: three folders with one-way flow. Raw is the original download, never edited. Interim is intermediate, reproducible. Processed is what feature engineering reads after validation passes.
- **Feature contract**: a short doc that pins down feature names, units, and ranges. The agreed *shape*, not the agreed *values*.
- **Tie-out**: confirms two independent reads of the data agree on foundational metrics.
- **Validation**: structured pass/fail of structural and logical checks. Not "ready" until zero FAIL.

## Limitations (read before pitching SafePath)

- The City layer covers **city-maintained** streetlights. The UCSD campus interior bbox does contain 229 lights in this snapshot, but coverage is uneven; campus-interior edges still fall back to a neutral lighting score, never zero. (Original assumption A-3 was too pessimistic; the fallback rule is still the right call because of uneven coverage, not zero coverage.)
- `STATUS == "A"` means "administratively active," not "energized right now." The data cannot tell us about real-time outages.
- No wattage / fixture weighting in v0. All operational lights count equally. (`POLE_HEIGHT_FT` is 100% null in this snapshot anyway.)
- Snapshot date is 2026-04-30; we do not refresh during the quarter.

When pitching: "lighting score reflects city-maintained streetlight density along the route" — not "we know which streets are well-lit."
