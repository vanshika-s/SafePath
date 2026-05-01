# 02. Data cleaning

> **TL;DR.** Crime, walkability, and street lights are cleaned and ready. Bike lanes are next (Max). Each cleaned file gets a validation checklist before the next step uses it.

## What is done

| Output file | Created by | Owner |
| - | - | - |
| `data/processed/crime_final_gdf.gpkg` | [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb) | done |
| `data/processed/walkability_final_gdf.gpkg` | [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb) | done |
| `data/processed/streetlights/streetlights_processed.geojson` | [`src/data/clean_streetlights.py`](../src/data/clean_streetlights.py) | done |
| `data/processed/geocode_cache.json` | crime notebook (auto written) | do not delete |

Crime + walkability files are shared in the team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing). See the [README data setup](../README.md#data-setup-one-time). Streetlight files are committed directly to the repo under `data/`.

## Crime cleaning pipeline

> **In one line.** Filter SDPD calls to confirmed pedestrian relevant incidents, geocode each address, save as a GeoPackage of points.

The full reasoning is in the markdown cells of [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb). Short version:

1. Load SDPD Calls for Service CSV from `data/raw/`.
2. Filter rows by `DISPOSITION` to keep confirmed outcomes (arrest, report taken, officer action). Drops false alarms and unfounded calls.
3. Filter `CALL_TYPE` to pedestrian relevant categories: violent crime, active threats, weapons, public safety hazards, in progress incidents.
4. Drop rows with missing road name.
5. Build `full_address` from address parts plus `, San Diego, CA`.
6. Geocode each unique address through [Nominatim](https://nominatim.openstreetmap.org) at 1 request per second. Cache results in `geocode_cache.json` so reruns skip lookups already done.
7. Drop rows where geocoding failed.
8. Save with point geometry to `crime_final_gdf.gpkg` in `EPSG:4326`.

### Validation checklist (crime)

Run these in a fresh notebook before trusting the file.

| Check | How |
| - | - |
| Loads without error | `gpd.read_file("data/processed/crime_final_gdf.gpkg")` |
| CRS is set | `gdf.crs` should be `EPSG:4326` |
| Every row has geometry | `gdf.geometry.notnull().all()` |
| Lat in plausible range | roughly 32.5 to 33.1 |
| Lon in plausible range | roughly -117.4 to -116.9 |
| Points cluster inside SD | `gdf.explore()` and look |
| 10 random addresses match Google Maps | manual spot check |
| Top call types match the safety definition | inspect `gdf['CALL_TYPE'].value_counts()` |

## Walkability cleaning pipeline

> **In one line.** Filter EPA index to San Diego County, fix the block group ID format, merge with Census TIGER polygons.

Full reasoning in [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb). Short version:

1. Load EPA Walkability Index CSV from `data/raw/`.
2. Filter to San Diego County (`STATEFP == 6`, `COUNTYFP == 73`).
3. Standardize `GEOID10` to a 12 character zero padded string. Pandas often loads it as a float, which loses leading zeros.
4. Load [Census TIGER block group shapefile](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip) from `data/raw/tl_2020_06_bg/`.
5. Merge EPA scores with TIGER polygons on `GEOID10`.
6. Save to `walkability_final_gdf.gpkg`.

### Validation checklist (walkability)

| Check | Expected |
| - | - |
| Loads without error | `gpd.read_file(...)` works |
| CRS is set | not None |
| Geometry is polygons | not points |
| Row count | around 2,058 (San Diego block groups) |
| `NatWalkInd` exists | column present |
| `NatWalkInd` range | 1 to 20 |
| Few or no nulls in `NatWalkInd` | `gdf['NatWalkInd'].isna().sum()` small |
| Polygons cover SD | `gdf.explore()` shows the city |
| Merge did not drop rows | `len(merged) == len(walk_sd)` |

## Streetlight cleaning pipeline

> **In one line.** Page the City of San Diego ArcGIS streetlight layer, filter to active operational lights, save as GeoJSON.

Full report: [`docs/data/streetlights/CLEANING_AND_VALIDATION.md`](data/streetlights/CLEANING_AND_VALIDATION.md). Short version:

1. Download raw GeoJSON via [`src/data/get_streetlights.py`](../src/data/get_streetlights.py) → `data/raw/streetlights/streetlights_YYYYMMDD.geojson` (snapshot 2026-04-30: 56,049 features).
2. Run [`src/data/clean_streetlights.py`](../src/data/clean_streetlights.py):
   - Drop null geometry / out-of-SD-bbox rows (0 dropped this snapshot).
   - Filter `STATUS == "A"` AND `MAPNG_STAT_CD ∈ {"AB","OP"}` (drops 543 inactive rows).
   - Flag (don't drop) duplicate `SAPOBJNR` (0 duplicates this snapshot).
   - Trim to scoring-relevant columns and write `data/processed/streetlights/streetlights_processed.geojson` (55,506 features).
3. Tie-out: `56,049 raw − 543 filtered = 55,506 processed` ✓.

### Validation checklist (streetlights)

All PASS as of 2026-04-30. See `docs/data/streetlights/CLEANING_AND_VALIDATION.md` §3.

| Check | Expected | Result |
| - | - | - |
| Schema present | `sap_obj_nr, status, mapng_stat_cd, dup_sapobjnr_flag, data_quality_flag, geometry` | PASS |
| `status` value domain | only `A` in processed file | PASS |
| `mapng_stat_cd` value domain | `{AB, OP}` only | PASS |
| Coord plausibility | lon ∈ [−117.4, −116.8], lat ∈ [32.4, 33.2] | PASS |
| Null geometry | 0 | PASS |
| Row count | 55,506 | PASS |
| `SAPOBJNR` uniqueness | 56,048 distinct in raw, 0 duplicates flagged | PASS |

## What is not done yet (Max's task)

### Buffered bike + scooter lanes

1. Find and download the buffered bike + scooter lane layer.
2. Load and inspect column meanings.
3. Filter to lanes that are actually buffered (not sharrows or unbuffered routes), unless we decide all lanes are useful.
4. Reproject to a consistent CRS.
5. Save to `data/processed/bikelanes_final_gdf.gpkg`.

**Open questions:**

1. Should scooter lanes be treated the same as bike lanes for pedestrian comfort?
2. Some lanes are one direction. Does that matter for our use?

## Coordinate systems, in plain words

| CRS | Units | Use for |
| - | - | - |
| `EPSG:4326` | degrees (lat/lon) | storage, raw display |
| `EPSG:3857` | meters | distance, buffering, spatial joins |

> **Rule of thumb.** Anything that involves "within X meters" needs `EPSG:3857`. Buffering in degrees is meaningless. Reproject before buffering, then reproject back if you want lat/lon for storage.

## Universal validation checklist (any new processed file)

Use this any time someone produces a new processed file.

1. The file loads in a fresh Python session without warnings.
2. Geometry column exists and matches the expected type (points for events, lines for streets, polygons for areas).
3. The CRS is set and documented in this doc.
4. Row counts before and after major filters are recorded in the notebook markdown.
5. Every kept row has the columns the next step needs.
6. `gdf.explore()` shows the data inside San Diego (anything outside is suspicious).
7. Surprising decisions are documented so future teammates do not redo the investigation.

## Optional: rerun preprocessing from raw

> **Most teammates skip this section.** You only need it if you want to refresh the data (for example, a newer SDPD year).

### Get the raw files

| Dataset | Source | Save to |
| - | - | - |
| SDPD Calls | [data.sandiego.gov](https://data.sandiego.gov/datasets/police-calls-for-service/) | `data/raw/pd_calls_for_service_YYYY_datasd.csv` |
| EPA Walkability | [Kaggle](https://www.kaggle.com/datasets/stacey06/u-s-walkability-index) | `data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv` |
| Census TIGER | [TIGER 2020 ZIP](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip) | `data/raw/tl_2020_06_bg/` (keep all sibling files) |
| San Diego streetlights | run `python src/data/get_streetlights.py` | `data/raw/streetlights/` |

### Run the notebooks / scripts top to bottom

1. [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb). **Warning: hours on first run** because of the 1 per second Nominatim limit. Do not delete `geocode_cache.json` between runs.
2. [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb).
3. `python src/data/clean_streetlights.py --raw data/raw/streetlights/streetlights_YYYYMMDD.geojson` (a few seconds).

All three must finish before scoring work can run.
