# SafePath

SafePath recommends walking routes in San Diego based on safety and comfort, not only speed. It is for people who feel vulnerable walking alone: students, women, anyone walking at night or in unfamiliar areas. Users enter a start and destination, pick a preference (fastest, safest, balanced), and get a route with a plain explanation of why it scored that way.

This is a quarter long student data science project (DS3 at UC San Diego). It uses public crime data, the EPA Walkability Index, Census block group boundaries, San Diego street lights and bike lanes, OpenStreetMap walking networks, and a weighted scoring algorithm.

## Start here

If you just joined the team, open these in order:

1. This README. Project description and how to set up the data locally.
2. [`docs/00_project_map.md`](docs/00_project_map.md). The navigation guide. Tells you which doc to read for your task.
3. [`docs/status.md`](docs/status.md). Who is working on what right now.

For meeting notes and brainstorming, see the team Google Drive (link in Discord).

## Quick start

```bash
# 1. clone
git clone https://github.com/vanshika-s/SafePath.git
cd SafePath

# 2. install dependencies (Python 3.10 or newer recommended)
pip install -r requirements.txt

# 3. download processed data (see Data setup below)

# 4. open a notebook
jupyter notebook notebooks/
```

## Repo layout

```
SafePath/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/                 preprocessing notebooks
├── docs/
│   ├── 00_project_map.md      start here after the README
│   ├── 01_data_sources.md
│   ├── 02_data_cleaning.md
│   ├── 03_feature_engineering.md
│   ├── 04_scoring_methodology.md
│   ├── status.md              live team status and ownership
│   ├── status/                older weekly snapshots
│   └── references/            SDPD reference files (CSV/PDF)
├── src/                       planned, empty for now
└── app/                       planned, empty for now
```

You will also create a local `data/processed/` folder at the repo root. It is gitignored on purpose because the files are too large for GitHub. See Data setup below.

## Data setup

The two heavy preprocessing notebooks have already been run. The processed files are shared in the team Google Drive. **You do not need to download the raw datasets or rerun preprocessing.** Just download three files.

### Step 1. Make the data folder

Create `data/processed/` at the repo root, next to `notebooks/`. The notebooks read from `../data/processed/...`, so the folder must sit there for the code to work.

### Step 2. Download the processed files

From the team Google Drive folder:

**https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing**

Place all three files in `data/processed/`:

1. `crime_final_gdf.gpkg`. Geocoded crime points.
2. `walkability_final_gdf.gpkg`. Block group polygons with walkability scores.
3. `geocode_cache.json`. Cached Nominatim lookups. Do not delete. Lets reruns of the preprocessing notebook resume instead of regeocoding from zero.

### Step 3. Sanity check

Your folder should look like:

```
data/processed/
  crime_final_gdf.gpkg
  walkability_final_gdf.gpkg
  geocode_cache.json
```

You are done. The scoring and routing work reads from `data/processed/`.

For a deeper explanation of how the cleaning is done, plus how to rerun preprocessing from raw data, see [`docs/02_data_cleaning.md`](docs/02_data_cleaning.md).

## Reference documents (in `docs/`)

External documentation we use to interpret the data:

1. [SDPD Call Type Codes](https://data.sandiego.gov/datasets/police-calls-call-types/). Definitions for all 234 call type codes.
2. [SDPD Disposition Codes](https://data.sandiego.gov/datasets/police-calls-disposition-codes/). Definitions for disposition codes (A, R, U, K, and so on).
3. [SDPD Dispatch Priority Definitions](https://seshat.datasd.org/police_calls_for_service/pd_cfs_priority_defs_datasd.pdf). Priority levels 0 to 4 and 9.
4. [EPA Smart Location Database Technical Documentation v3.0](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf). Full data dictionary including `NatWalkInd`.

The first three are also bundled in `docs/references/` as CSV and PDF for offline reference.

## Where to read more

1. [`docs/00_project_map.md`](docs/00_project_map.md). Navigation guide. Read this second.
2. [`docs/01_data_sources.md`](docs/01_data_sources.md) through [`docs/04_scoring_methodology.md`](docs/04_scoring_methodology.md). The 5 step project flow.
3. [`docs/status.md`](docs/status.md). Live team status.
4. The notebooks themselves. Markdown cells in `notebooks/crime-df-preprocessing.ipynb` and `notebooks/walkability-df-preprocessing.ipynb` document each preprocessing decision.
