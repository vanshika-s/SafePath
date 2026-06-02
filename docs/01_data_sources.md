# 01. Data sources

> **TL;DR.** SafePath uses 5 public datasets. Crime, walkability, and **street lights are cleaned**. Bike lanes are next (Max owns). OSM walking network downloads on demand.

## Quick scan table

| Dataset | Status | Output file | Progress | Owner |
| - | - | - | - | - |
| [SDPD Calls for Service](https://data.sandiego.gov/datasets/police-calls-for-service/) | cleaned | `data/processed/crime_final_gdf.gpkg` | done | Matthew (per [`status/week4_status.md`](status/week4_status.md)) |
| [EPA Walkability Index](https://www.kaggle.com/datasets/stacey06/u-s-walkability-index) + [Census TIGER](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip) | cleaned | `data/processed/walkability_final_gdf.gpkg` | done | Matthew (per [`status/week4_status.md`](status/week4_status.md)) |
| San Diego street lights | cleaned | `data/processed/streetlights/streetlights_processed.geojson` | done | Max |
| San Diego buffered bike + scooter lanes | not started | TBD | not started | Max |
| OpenStreetMap walking network (via [OSMnx](https://osmnx.readthedocs.io)) | downloaded at runtime | not stored | downstream | unassigned |
| [UCSD Annual Clery Report](https://police.ucsd.edu/clery/index.html) (annual aggregates, 2022–2024) | extracted; **validator only — not a feature input** | `data/processed/ucsd_clery/ucsd_clery_stats_2022_2024.csv` | aggregate counts only; cannot be turned into per-edge features | Max |
| [UCSD Daily Crime & Fire Log](https://www.ucsdpolice.com/policelog/index.html) (per-incident, point-level — **the actual feature source**) | **not started** — `data/raw/ucsd_police_logs/logs_*.csv` is empty | TBD | blocks `campus_incident_score` (F10) | Max |

## 1. SDPD Calls for Service (crime)

**Source.** [City of San Diego open data, Police Calls for Service](https://data.sandiego.gov/datasets/police-calls-for-service/).

**What it has.** One row per police call. Columns include date, time, [call type](https://data.sandiego.gov/datasets/police-calls-call-types/), [priority](https://seshat.datasd.org/police_calls_for_service/pd_cfs_priority_defs_datasd.pdf), [disposition](https://data.sandiego.gov/datasets/police-calls-disposition-codes/), and address.

**Why it matters.** This is the raw signal for "did something risky happen near here." We filter to confirmed pedestrian-relevant calls, geocode addresses to lat/lon points, and split incidents by `HOUR` into day and night buckets. The app loads whichever bucket matches the current San Diego time, so both the heatmap and the edge safety weights reflect time-of-day crime patterns.

**Reference files (offline).** In [`docs/references/`](references/):

1. [`pd_cfs_calltypes_datasd.csv`](references/pd_cfs_calltypes_datasd.csv) (call type definitions)
2. [`pd_dispo_codes_datasd.csv`](references/pd_dispo_codes_datasd.csv) (disposition codes)
3. [`pd_cfs_priority_defs_datasd.pdf`](references/pd_cfs_priority_defs_datasd.pdf) (priority levels 0 to 4 and 9)

**Cleaning recipe.** See [`02_data_cleaning.md`](02_data_cleaning.md#crime-cleaning-pipeline). Notebook: [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb).

## 2. EPA Walkability Index

**Source.** [Kaggle mirror of the EPA Smart Location Database](https://www.kaggle.com/datasets/stacey06/u-s-walkability-index). Reference: [EPA SLD v3.0 PDF](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf).

**What it has.** One row per Census block group in the US. Key column `NatWalkInd` is a 1 to 20 score combining street connectivity, transit access, and land use mix.

**Why it matters.** Tells us whether the streets in a block group are friendly for walking, independent of crime.

**Cleaning recipe.** See [`02_data_cleaning.md`](02_data_cleaning.md#walkability-cleaning-pipeline). Notebook: [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb).

## 3. Census TIGER block group boundaries (CA, 2020)

**Source.** [Census TIGER 2020 (CA block groups, ZIP)](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip).

**What it has.** Polygon boundary for every California Census block group.

**Why it matters.** The EPA file has scores but no shapes. We merge TIGER polygons with EPA scores so each block group has both a score and a geographic shape we can spatially join to street edges.

## 4. San Diego street lights (cleaned)

**Source.** [City of San Diego ArcGIS Feature Layer](https://webmaps.sandiego.gov/arcgis/rest/services/Planning/PLN_Mobility/MapServer/1) (Department of Transportation & Storm Water).

**What it has.** Point geometry for every city-maintained streetlight, plus 38 attribute columns (status, mapping status, pole/fixture descriptors, install year, location description, etc.). Snapshot date 2026-04-30. Raw: 56,049 features. Processed: **55,506 active lights** after `STATUS == 'A'` AND `MAPNG_STAT_CD ∈ {'AB','OP'}` filter.

**Why it matters.** Lighting is one of the strongest signals for whether a walk feels safe at night. Becomes the `lighting_score` per street edge.

**Output files.**
- Raw: `data/raw/streetlights/streetlights_20260430.geojson`
- Interim (filtered, all original fields): `data/interim/streetlights/streetlights_active_wgs84.geojson`
- Processed (trimmed for scoring): `data/processed/streetlights/streetlights_processed.geojson`

**Owner.** Max. Tie-out and validation PASS — see `docs/data/streetlights/CLEANING_AND_VALIDATION.md` for the full report.

## 5. San Diego buffered bike + scooter lanes (not started)

**Source.** City of San Diego open data, [Bike Route Lines](https://data.sandiego.gov/datasets/bike-route-lines/) (existing facilities, 2015 baseline — verify "updated" timestamp on download). Geometry: line. Format: GeoJSON, shapefile, TopoJSON, CSV.

**Expected fields** (from ArcGIS hub mirrors, unverified until download): `OBJECTID`, `CLASS` (1=Class I separated path, 2=Class II striped lane, 3=Class III signed shared route, 4=Class IV protected cycle track), `CLASSTYPE` (sub-types: Buffered / Protected / Cycle Track), `CATEGORY`, `Shape`, `Shape_Length`, `GlobalID`.

**California bikeway classification** (Streets & Highways Code 890.4): Class I = fully separated path; Class II = striped on-roadway lane (Buffered if a painted buffer is present); Class III = signed shared roadway, no separation; Class IV = physically separated cycle track / protected bikeway.

**Scooter relevance.** Class I, II, and IV facilities are generally usable by Class 2 e-scooters under California Vehicle Code §21229 / §21235; sidewalks are not. Treating bike-lane presence as a scooter-comfort proxy is reasonable.

**Why it matters.** Buffered lanes correlate with calmer streets and are a useful proxy for pedestrian comfort.

**Hard rule — do not mix existing with proposed.** A separate City of San Diego *Bike Master Plan* dataset ([data.sandiego.gov/datasets/bike-master-plan](https://data.sandiego.gov/datasets/bike-master-plan/)) lists *proposed* facilities. Never feed it into the live route score — it would tell users a route is comfortable when the lane doesn't exist yet. Save under `data/raw/bike_master_plan_proposed/` if downloaded for reference.

**Owner.** Max. See [`02_data_cleaning.md`](02_data_cleaning.md#what-is-not-done-yet-maxs-task) and the bike feature spec in [`03_feature_engineering.md`](03_feature_engineering.md#bike-comfort-feature-future-depends-on-max).

## 6. OpenStreetMap walking network

**Source.** [OpenStreetMap](https://www.openstreetmap.org), downloaded through the [OSMnx Python library](https://osmnx.readthedocs.io) at runtime.

**What it has.** Every walkable street and intersection in San Diego as a graph. **Nodes** are intersections. **Edges** are street segments. Each edge has attributes like length, street name, lit (sometimes), sidewalk (sometimes), highway type.

**Why it matters.** This is the actual map we route through. Every other dataset gets attached to OSM edges so the routing engine has one place to read scores from.

**Status.** In production. The full San Diego walking network is stored as `data/processed/sd_walk_graph.graphml` and was used by `safety-score-edge.ipynb` to build the fast numpy `RouteGraph`. At runtime the server loads pre-built numpy arrays — OSMnx is not called at request time.

## A note on data freshness

We work with snapshots, not live feeds.

| Dataset | Snapshot |
| - | - |
| Crime | limited 2026 window |
| EPA Walkability | 2021 index |
| Street lights | 2026-04-30 (city ArcGIS) |
| Bike lanes | whatever the city publishes when Max pulls them |
| OSM | downloaded fresh per session |

This is fine for a prototype. We do not pretend the data is real time.
