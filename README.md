# SafePath
SafePath is a route recommendation tool that prioritizes safety and comfort over speed, helping users, especially those who feel vulnerable, choose safer walking paths. It uses factors like lighting, sidewalks, traffic, nearby businesses, and crime data to suggest more visible and active routes, supporting safer and more informed travel decisions.


## Project structure

```
SafePath/
├── data/
│   ├── raw/          # Downloaded source files (not tracked in git — see Data Setup)
│   └── processed/    # Cleaned and merged outputs ready for modeling
├── docs/             # External reference documents tracked in git
├── notebooks/        # Exploratory analysis and sprint-by-sprint prototyping
├── src/              # Reusable Python modules imported by the app and notebooks
├── app/              # Streamlit frontend and map display logic
└── README.md
```

**`data/`** — Not tracked in git due to file size. Raw source files go in `data/raw/` and cleaned outputs saved by the notebooks go in `data/processed/`. See Data Setup below.

**`docs/`** — External reference documents that are small enough to track in git. Contains the SDPD call type code list, disposition code definitions, and dispatch priority definitions used to interpret and filter the crime dataset. Tracked so everyone on the team has the same reference material without needing to download it separately.

**`notebooks/`** — Where we explore and validate ideas. Each notebook maps to a sprint week. Messy and experimental by design; once logic is proven here it gets cleaned up and moved to `src/`.

**`src/`** — The core of the project. Clean, importable Python modules for data loading, safety scoring, and routing. Nothing Streamlit-specific lives here — just reusable logic that can be tested independently.

**`app/`** — Everything the user sees. `main.py` is the Streamlit entry point and stays thin by calling functions from `src/`. Map rendering and UI components are broken into separate files to keep things organized.

## Datasets

**San Diego Police Calls for Service** — City-level crime and incident reports logged by the SD Police Department. Each row is a call with a date, time, incident type, and coordinates. We use this to measure crime density across neighborhoods and flag high-risk areas along walking routes.

**U.S. Walkability Index** — A neighborhood-level walkability score published by the EPA, covering factors like street connectivity, proximity to transit, and land use mix. Filtered down to San Diego's block groups, this gives us a baseline measure of how pedestrian-friendly each area is.

**Census TIGER Block Group Shapefile (CA, 2020)** — Polygon boundary files for every Census block group in California. We merge these with the Walkability Index using a shared GEOID to give each neighborhood a geographic shape, which lets us assign walkability scores to street edges in the routing algorithm.

## Data setup

Raw data files are not tracked in git due to file size. Follow these steps to set up your local data folder before running any notebooks.

### Step 1 — Create the folder structure

Inside your cloned repo, create the following folders if they don't already exist:

    SafePath/
    └── data/
        ├── raw/        ← all downloaded files go here
        └── processed/  ← cleaned outputs saved by notebooks go here

### Step 2 — Download each dataset

**SD Police Calls for Service**
1. Go to https://data.sandiego.gov/datasets/police-calls-for-service/
2. Download the CSV for the most recent year available
3. Save to `data/raw/pd_calls_for_service_YYYY_datasd.csv`

**U.S. Walkability Index**
1. Go to https://www.kaggle.com/datasets/stacey06/u-s-walkability-index
2. Download the CSV (requires free Kaggle account)
3. Save to `data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv`

**Census TIGER Block Group Shapefile**
1. Go to https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip
2. Download and unzip the file
3. Save all unzipped files to `data/raw/tl_2020_06_bg/`

### Step 3 — Verify your folder looks like this

    data/raw/
      pd_calls_for_service_YYYY_datasd.csv
      EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv
      tl_2020_06_bg/
        tl_2020_06_bg.dbf
        tl_2020_06_bg.prj
        tl_2020_06_bg.shp
        tl_2020_06_bg.shx

### Step 4 — Run the preprocessing notebooks

**Crime data**

Open `notebooks/crime-df-preprocessing.ipynb` and run from the top. This filters the SDPD calls for service down to pedestrian-relevant incidents, geocodes each address to an exact lat/lon coordinate, and saves the result to `data/processed/`.

The geocoding step contacts Nominatim (OpenStreetMap's free geocoder) once per unique address and stores the result in `data/processed/geocode_cache.json`. The cache means you only ever geocode each address once — if you stop and re-run, it picks up where it left off and skips anything already looked up. Do not delete this file.

When the notebook finishes, `data/processed/` will contain:

```
data/processed/
  crime_final_gdf.gpkg   # geocoded crime points — call type, priority, hour, point geometry
  geocode_cache.json     # Nominatim results keyed by address — do not delete
```

**Walkability data**

Open `notebooks/walkability-df-preprocessing.ipynb` and run from the top. This filters the EPA Smart Location Database down to San Diego block groups, merges in the Census TIGER polygon boundaries to give each block group a geographic shape, and saves the result to `data/processed/`.

When the notebook finishes, `data/processed/` will also contain:

```
data/processed/
  walkability_final_gdf.gpkg  # San Diego block group polygons with NatWalkInd (1–20)
```

Both notebooks must be run before moving on to the scoring step.

## Processed outputs

After running both preprocessing notebooks, your `data/processed/` folder should contain:

```
data/processed/
  crime_final_gdf.gpkg       # geocoded crime points — call type, priority, hour, point geometry
  walkability_final_gdf.gpkg # San Diego block group polygons with NatWalkInd (1–20)
  geocode_cache.json         # cached geocoding results — do not delete
```

## How the preprocessed data feeds into the next steps

Both preprocessing notebooks produce GeoPackage files that serve as the inputs for the safety scoring and routing stages.

### `crime_final_gdf.gpkg` — geocoded crime points

Each row is a confirmed pedestrian-relevant incident filtered down from SDPD calls for service. Only calls with a confirmed outcome (arrest, report taken, or officer action) and a call type that directly affects pedestrian safety are kept — covering violent crimes (assault, robbery, ADW), active threats (weapons, criminal threats, stalking), public safety hazards (narcotics, hazardous conditions, bomb threats), and in-progress incidents (burglary, foot pursuit). Each row has an exact lat/lon point geometry, the original call type, priority level, and hour of day.

In the scoring step this feeds in as:

- **Crime density per street edge** — a 50m buffer is drawn around each edge in the OSMnx walking network and all crime points inside are counted. A street with 15 incidents in its buffer scores higher than one with 2, directly reflecting how much confirmed criminal activity occurred near that stretch.
- **Severity weighting** — not all crimes count equally. Call types are assigned a severity weight so that a single robbery or ADW contributes more to the score than a trespassing or public intoxication incident. Priority level from the SDPD dispatch system (0 = immediate life threat, 4 = non-urgent) is also factored in, meaning high-priority calls raise the score more than low-priority ones even within the same call type.
- **Time-of-day split** — `HOUR` is used to produce separate `crime_score_day` and `crime_score_night` values per edge, since the same street can feel very different at 2pm vs 2am. A block with most incidents after dark gets a higher night score without penalizing its daytime score.

### `walkability_final_gdf.gpkg` — block group walkability polygons

Each row is a Census block group polygon with a `NatWalkInd` score (1–20) from the EPA Smart Location Database. `NatWalkInd` is a composite index built from four sub-measures of the built environment:

- **D3B — Street intersection density** (weight 1/3): counts pedestrian-oriented intersections per square mile, excluding auto-only ramps. Higher intersection density means a more connected, grid-like street network where walkers have more route options and shorter blocks.
- **D4A — Distance to nearest transit stop** (weight 1/3): measures proximity to bus and rail stops from the block group's population-weighted centroid. Block groups with no transit access receive the lowest rank.
- **D2A — Employment and household entropy** (weight 1/6): measures land use mix by combining the diversity of jobs and housing in an area. Mixed-use areas with both residents and employers are more walkable than purely residential or purely commercial zones.
- **D2B — 8-tier employment entropy** (weight 1/6): measures diversity of job types (retail, office, service, industrial, entertainment, education, healthcare, public administration). Areas with varied employment types generate foot traffic throughout the day.

Each sub-measure is ranked 1–20 by national quantile and combined using the weights above, giving a final score where 1–5.75 is least walkable and 15.26–20 is most walkable.

In the scoring step this feeds in as:

- **Walkability score per street edge** — each edge is spatially joined to the block group it falls inside to inherit its `NatWalkInd` score
- **Baseline pedestrian infrastructure signal** — independent of crime, this captures whether the physical environment supports walking. A low-crime street in a poorly connected area with no transit still scores lower than a well-connected, transit-accessible street, pushing routes toward areas that are both safe and built for pedestrians

### The street network — OSM nodes and edges

Before scoring can happen, we need a map of every walkable street segment in San Diego. We get this from OpenStreetMap (OSM) via the OSMnx library, which downloads the city's walking network as a graph.

The graph has two components:

- **Nodes** are intersections and dead ends — any point where two or more streets meet, or where a street terminates. Each node has a lat/lon coordinate.
- **Edges** are the individual street segments that connect two nodes. A single block between two intersections is one edge. Each edge has attributes like length, street name, and highway type.

Every edge is what we actually score. A pedestrian walking from A to B travels along a sequence of edges, so the safety of the route is the sum of the safety scores of the edges it uses.

### Combined into a safety score

```
crime_final_gdf.gpkg              walkability_final_gdf.gpkg
(geocoded crime points)           (block groups with NatWalkInd)
        ↓                                  ↓
        For each street edge in the OSMnx walking network:
            1. Buffer 50m → count + weight nearby crime points
               → crime_score_day and crime_score_night
            2. Spatial join to block group → NatWalkInd
               → walkability_score
            3. Normalize both to 0–1 scale
               → safety_score = w1 * crime_score + w2 * walkability_score
        ↓
        Scored edge network → input to the routing engine (Dijkstra / A*)
```

## Reference documents

External documentation used to interpret and validate each dataset.

**San Diego Crime Data**
- [SDPD Call Type Codes](https://data.sandiego.gov/datasets/police-calls-call-types/) — definitions for all 234 call type codes in the crime dataset
- [SDPD Disposition Codes](https://data.sandiego.gov/datasets/police-calls-disposition-codes/) — definitions for disposition codes (A, R, U, K, etc.)
- [SDPD Dispatch Priority Definitions](https://seshat.datasd.org/police_calls_for_service/pd_cfs_priority_defs_datasd.pdf) — explanation of priority levels 0, 1, 2, 3, 4, and 9

**Walkability Data**
- [EPA Smart Location Database Technical Documentation v3.0](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf) — full data dictionary and methodology for all SLD variables including `NatWalkInd`

## Why we use GeoPandas

Standard pandas works great for tabular data but has no concept of geography —
it cannot answer questions like "which neighborhood does this point fall inside?"
or "how many crimes occurred within this polygon?" GeoPandas extends pandas by
adding a geometry column to every row, turning a plain table into a spatially
aware dataset.

In SafePath, GeoPandas does four things that regular pandas cannot:

**1. Loads spatial files**
GeoPandas reads shapefiles (.shp) and GeoPackages (.gpkg) directly into a
DataFrame with geometry attached — no manual coordinate parsing needed.

```python
walkability_gdf = gpd.read_file('walkability_final_gdf.gpkg')
```

**2. Reprojects coordinate systems**
Our datasets come in different coordinate systems. GeoPandas reprojects them
to a common system in one line so spatial operations work correctly.

```python
crime_gdf = crime_gdf.to_crs(epsg=4326)  # reproject to lat/lon
```

**3. Spatial joins**
GeoPandas can join two datasets based on geographic overlap rather than a shared
column. This is how we assign walkability scores to street edges — by checking
which block group each edge falls inside.

```python
gpd.sjoin(edges_gdf, walkability_gdf, how='left', predicate='intersects')
```

**4. Spatial comparisons and geometry operations**
GeoPandas has built-in functions to compare and analyze geometries spatially
without any manual math:

- `contains` — does this polygon fully contain this point?
- `intersects` — do these two shapes overlap at all?
- `within` — is this point inside this polygon?
- `buffer` — expand a geometry outward by a distance (e.g. 50 meters around a
  street edge to find nearby crimes)
- `.area` — compute the area of a polygon, useful for normalizing crime counts
  by area

Without GeoPandas, all of these operations would require writing complex
geometry math from scratch. GeoPandas handles all of that using Shapely under
the hood, letting us focus on the analysis instead of the math.