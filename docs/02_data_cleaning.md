# 02. Data cleaning

> **TL;DR.** Crime and walkability are cleaned and ready in `data/processed/`. Street lights and bike lanes are next (Max). Each cleaned file gets a validation checklist before the next step uses it.

## What is done

| Output file | Created by | Owner |
| - | - | - |
| `data/processed/crime_final_gdf.gpkg` | [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb) | done |
| `data/processed/walkability_final_gdf.gpkg` | [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb) | done |
| `data/processed/geocode_cache.json` | crime notebook (auto written) | do not delete |

Files are shared in the team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing). See the [README data setup](../README.md#data-setup-one-time).

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

## What is not done yet (Max's task)

Two more datasets need cleaning before scoring can fully use them.

### Street lights

1. Find and download the SD street lights dataset from the [city open data portal](https://data.sandiego.gov).
2. Load and inspect: row count, columns, geometry type.
3. Drop rows without coordinates.
4. Decide a single CRS and reproject if needed.
5. Save to `data/processed/streetlights_final_gdf.gpkg` (or similar clear name).

**Open questions to resolve:**

1. Are some lights private property and should they be excluded?
2. Does the dataset include broken or removed lights, and how do we filter them?

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

Use this any time someone produces a new `*_final_gdf.gpkg`.

1. The file loads in a fresh Python session without warnings.
2. Geometry column exists and matches the expected type (points for events, lines for streets, polygons for areas).
3. The CRS is set and documented in this doc.
4. Row counts before and after major filters are recorded in the notebook markdown.
5. Every kept row has the columns the next step needs.
6. `gdf.explore()` shows the data inside San Diego (anything outside is suspicious).
7. Surprising decisions are documented in the notebook so future teammates do not redo the investigation.

## Optional: rerun preprocessing from raw

> **Most teammates skip this section.** You only need it if you want to refresh the data (for example, a newer SDPD year).

### Get the raw files

| Dataset | Source | Save to |
| - | - | - |
| SDPD Calls | [data.sandiego.gov](https://data.sandiego.gov/datasets/police-calls-for-service/) | `data/raw/pd_calls_for_service_YYYY_datasd.csv` |
| EPA Walkability | [Kaggle](https://www.kaggle.com/datasets/stacey06/u-s-walkability-index) | `data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv` |
| Census TIGER | [TIGER 2020 ZIP](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip) | `data/raw/tl_2020_06_bg/` (keep all sibling files) |

### Run the notebooks top to bottom

1. [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb). **Warning: hours on first run** because of the 1 per second Nominatim limit. Do not delete `geocode_cache.json` between runs.
2. [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb).

Both must finish before scoring work can run.
