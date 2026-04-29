<<<<<<< HEAD
# 01. Data sources

> **TL;DR.** SafePath uses 5 public datasets. Crime and walkability are already cleaned. Street lights and bike lanes are next (Max owns). OSM walking network downloads on demand.

## Quick scan table

| Dataset | Status | Output file | Owner |
| - | - | - | - |
| [SDPD Calls for Service](https://data.sandiego.gov/datasets/police-calls-for-service/) | cleaned | `data/processed/crime_final_gdf.gpkg` | done |
| [EPA Walkability Index](https://www.kaggle.com/datasets/stacey06/u-s-walkability-index) + [Census TIGER](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip) | cleaned | `data/processed/walkability_final_gdf.gpkg` | done |
| San Diego street lights | not started | TBD | Max |
| San Diego buffered bike + scooter lanes | not started | TBD | Max |
| OpenStreetMap walking network (via [OSMnx](https://osmnx.readthedocs.io)) | downloaded at runtime | not stored | Ruan, downstream |

## 1. SDPD Calls for Service (crime)

**Source.** [City of San Diego open data, Police Calls for Service](https://data.sandiego.gov/datasets/police-calls-for-service/).

**What it has.** One row per police call. Columns include date, time, [call type](https://data.sandiego.gov/datasets/police-calls-call-types/), [priority](https://seshat.datasd.org/police_calls_for_service/pd_cfs_priority_defs_datasd.pdf), [disposition](https://data.sandiego.gov/datasets/police-calls-disposition-codes/), and address.

**Why it matters.** This is the raw signal for "did something risky happen near here." We filter to confirmed pedestrian relevant calls, then geocode addresses to lat/lon points.

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

## 4. San Diego street lights (not started)

**Source.** [San Diego open data portal](https://data.sandiego.gov), search for the Street Lights dataset.

**What it has.** Location of every public street light, usually point geometry plus attributes like wattage or fixture type.

**Why it matters.** Lighting is one of the strongest signals for whether a walk feels safe at night. We will turn this into a `lighting_score` per street edge.

**Owner.** Max. See [`02_data_cleaning.md`](02_data_cleaning.md#what-is-not-done-yet-maxs-task).

## 5. San Diego buffered bike + scooter lanes (not started)

**Source.** [San Diego open data portal](https://data.sandiego.gov), look for Bike Network or Bike Facilities. We want the **buffered** variant (lanes with a physical buffer from car traffic).

**What it has.** Line geometry of bike and scooter lanes with attributes for lane type and buffer presence.

**Why it matters.** Buffered lanes correlate with calmer streets and are a useful proxy for pedestrian comfort.

**Owner.** Max. See [`02_data_cleaning.md`](02_data_cleaning.md#what-is-not-done-yet-maxs-task).

## 6. OpenStreetMap walking network

**Source.** [OpenStreetMap](https://www.openstreetmap.org), downloaded through the [OSMnx Python library](https://osmnx.readthedocs.io) at runtime.

**What it has.** Every walkable street and intersection in San Diego as a graph. **Nodes** are intersections. **Edges** are street segments. Each edge has attributes like length, street name, lit (sometimes), sidewalk (sometimes), highway type.

**Why it matters.** This is the actual map we route through. Every other dataset gets attached to OSM edges so the routing engine has one place to read scores from.

**Owner.** Touched by Ruan in feature engineering. Used downstream in scoring.

## A note on data freshness

We work with snapshots, not live feeds.

| Dataset | Snapshot |
| - | - |
| Crime | limited 2026 window |
| EPA Walkability | 2021 index |
| Street lights / bike lanes | whatever the city published when Max pulls them |
| OSM | downloaded fresh per session |

This is fine for a prototype. We do not pretend the data is real time.
=======
# Data sources

Every dataset SafePath uses, where it came from, and who is working with it.

## Quick table

| Dataset | Status | File on disk after cleaning | Owner |
| --- | --- | --- | --- |
| SDPD Calls for Service (crime) | cleaned | `data/processed/crime_final_gdf.gpkg` | done |
| EPA Walkability Index + Census TIGER | cleaned | `data/processed/walkability_final_gdf.gpkg` | done |
| San Diego street lights | not started | TBD | Max |
| San Diego buffered bike and scooter lanes | not started | TBD | Max |
| OpenStreetMap walking network | downloaded at runtime | not stored locally | Ruan, downstream |

## SDPD Calls for Service (crime)

Source: City of San Diego open data portal, [Police Calls for Service](https://data.sandiego.gov/datasets/police-calls-for-service/).

What it has: each row is one police call. Columns include date, time, call type, priority, disposition, and address.

Why it matters: this is the raw signal for "did something risky happen near here." We filter to confirmed pedestrian relevant calls, then geocode addresses to lat lon points.

Reference files in `docs/references/`:
1. `pd_cfs_calltypes_datasd.csv` (call type definitions)
2. `pd_dispo_codes_datasd.csv` (disposition codes)
3. `pd_cfs_priority_defs_datasd.pdf` (priority levels 0 through 4 and 9)

How it gets cleaned: see `02_data_cleaning.md`.

## EPA Walkability Index

Source: Kaggle mirror of the [EPA Smart Location Database](https://www.kaggle.com/datasets/stacey06/u-s-walkability-index). Reference doc: [EPA SLD v3.0](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf).

What it has: one row per Census block group in the US. The column `NatWalkInd` is a 1 to 20 score that combines street connectivity, transit access, and land use mix.

Why it matters: it tells us whether the streets in a block group are friendly for walking, independent of crime.

How it gets cleaned: see `02_data_cleaning.md`.

## Census TIGER block group boundaries (CA, 2020)

Source: [Census TIGER 2020](https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip).

What it has: polygon boundary for every California Census block group.

Why it matters: the EPA walkability file has scores but no shapes. We merge the TIGER polygons with the EPA scores so each block group has both a score and a geographic shape we can spatially join to street edges.

## San Diego street lights (not started)

Source: City of San Diego open data, look for the Street Lights dataset.

What it has: location of every public street light, usually as point geometry plus attributes like wattage or fixture type.

Why it matters: lighting is one of the strongest signals for whether a walk feels safe at night. We will turn this into a "lighting feature" per street edge.

Owner: Max. See `02_data_cleaning.md` for the cleaning task.

## San Diego buffered bike and scooter lanes (not started)

Source: City of San Diego open data, look for Bike Network or Bike Facilities. The "buffered" variant means lanes that have a physical buffer from car traffic.

What it has: line geometry of bike and scooter lanes, with attributes for lane type and buffer presence.

Why it matters: buffered lanes correlate with calmer streets and are a useful proxy for pedestrian comfort.

Owner: Max. See `02_data_cleaning.md`.

## OpenStreetMap walking network

Source: OpenStreetMap, downloaded through the `osmnx` Python library at runtime.

What it has: every walkable street and intersection in San Diego as a graph. Nodes are intersections. Edges are street segments. Each edge has attributes like length, street name, lit (sometimes), sidewalk (sometimes), highway type.

Why it matters: this is the actual map we route through. Every other dataset gets attached to OSM edges so the routing engine has one place to read scores from.

Owner: not assigned to one person. Touched by Ruan in feature engineering and used downstream in scoring.

## A note on data freshness

We are working with snapshots, not live feeds. The crime file currently covers a limited window in 2026. Walkability is a 2021 EPA index. Street lights and bike lanes will be whatever the city published when Max pulls them. None of this is a problem for the prototype, but we should not pretend it is real time.
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb
