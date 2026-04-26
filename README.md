# SafePath
SafePath is a route recommendation tool that prioritizes safety and comfort over speed, helping users, especially those who feel vulnerable, choose safer walking paths. It uses factors like lighting, sidewalks, traffic, nearby businesses, and crime data to suggest more visible and active routes, supporting safer and more informed travel decisions.


## Project structure
SafePath/
├── data/
│   ├── raw/          # Downloaded source files (not tracked in git — see Data Setup)
│   └── processed/    # Cleaned and merged outputs ready for modeling
├── notebooks/        # Exploratory analysis and sprint-by-sprint prototyping
├── src/              # Reusable Python modules imported by the app and notebooks
├── app/              # Streamlit frontend and map display logic
└── README.md

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

### Step 4 — You're ready

Open `notebooks/01_crime_eda.ipynb` and run from the top. All notebooks load data from `data/raw/` and save cleaned outputs to `data/processed/`.

## Processed outputs

After running the preprocessing notebooks, your `data/processed/` folder should contain:

    data/processed/
      crime_final_gdf.gpkg       # 4,342 geocoded crime points with severity weights and hour
      walkability_final_gdf.gpkg # 1,794 San Diego block groups with NatWalkInd scores
      geocode_cache.json         # cached geocoding results — do not delete

## what's next

With both processed datasets ready, the next step builds the safety scoring algorithm
by loading the San Diego street network and assigning scores directly to street edges.

    crime_final_gdf.gpkg              walkability_final_gdf.gpkg
    (4,342 geocoded crime points)     (1,794 block groups with NatWalkInd)
            ↓                                  ↓
            For each street edge in the OSMnx walking network:
                1. Draw a 50m buffer around the edge
                2. Count crime points inside the buffer
                   → weight by severity (call type) and time of day (day vs night)
                   → crime_score_day and crime_score_night per edge
                3. Spatial join edge to block group
                   → get NatWalkInd → walkability_score per edge
                4. Combine into one safety_score per edge
                   → normalize both scores to 0–1 scale
                   → safety_score = w1 * crime_score + w2 * walkability_score
            ↓
            Save scored edge network → used by Week 4 routing engine

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