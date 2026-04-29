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
