# SafePath

SafePath is a route recommendation tool that suggests walking paths in San Diego based on safety and comfort, not just speed. It is aimed at people who feel vulnerable walking alone — students, women, anyone walking at night or in unfamiliar areas. Users will enter a start and destination and pick a preference (fastest, safest, balanced); the app will return a route with a plain-language explanation of why it scored that way.

This is a quarter-long student data science project (DS3 @ UC San Diego). It uses public crime data, the EPA Walkability Index, Census block group boundaries, OpenStreetMap walking networks, and a weighted scoring algorithm to rank routes.

## Start here

If you just joined the project, read in this order:

1. This README : what the project is and how to set up the data.
2. The most recent weekly status under [`docs/status/`](docs/status/), for example [`docs/status/week4_status.md`](docs/status/week4_status.md). One short file is added each week so future contributors can easily track the project's history.
3. [`docs/methodology.md`](docs/methodology.md) : planned scoring and routing methodology

For meeting notes and weekly brainstorming, see Vanshika's Google Docs

## Quick start

```bash
# 1. clone
git clone https://github.com/vanshika-s/SafePath.git
cd SafePath

# 2. install dependencies (Python 3.10+ recommended)
pip install -r requirements.txt

# 3. download processed data (see "Data setup" below)
#    drop the three files into data/processed/

# 4. open a notebook
jupyter notebook notebooks/
```

You don't need to run the preprocessing notebooks unless you want to refresh the underlying data — the cleaned outputs are shared via Google Drive so you can skip straight to the scoring/routing work.

## Project layout

```
SafePath/
├── data/                   # not tracked in git — download per Data setup below
├── docs/
│   ├── methodology/        # planned scoring and routing methodology
│   ├── status/             # one short weekly status file per week (week4_status.md, week5_status.md, ...)
│   ├── reference/          # SDPD reference files (CSV/PDF)
│   ├── preprocessing.md    # data cleaning and validation guide
│   └── pipeline.md         # full technical pipeline write up
├── notebooks/              # data preprocessing notebooks (one per dataset)
├── src/                    # planned: reusable Python modules (scoring, routing). Empty for now.
├── app/                    # planned: Streamlit frontend. Empty for now.
├── requirements.txt
└── README.md
```

`src/` and `app/` are placeholders today. Moving the proven scoring and routing logic out of the notebooks into `src/`, and starting the Streamlit app in `app/`, is the next step. See the latest file in `docs/status/` for the current week. You will also create a local data/processed/ folder at the repo root. It is gitignored. See Data setup section.

## Datasets

Three public datasets feed the project. We use processed versions of all three.

- **San Diego Police Calls for Service** : incident reports from the SDPD with date, time, call type, priority, and address. We use this for crime density and severity along walking routes.
- **U.S. Walkability Index (EPA)** : a 1–20 score per Census block group capturing street connectivity, transit access, and land-use mix.
- **Census TIGER Block Group Boundaries (CA, 2020)** : polygon shapes for every California Census block group. We merge these with the Walkability Index so each block group has both a score and a geographic shape.

Detailed explanations of what each column means and how it feeds into scoring are in [`docs/methodology.md`](docs/methodology.md).

## Data setup

The preprocessing notebooks have already been run and the results are shared in Google Drive. **You do not need to download the raw datasets or rerun preprocessing** — just download the three processed files.

**Why we share processed files:** the crime preprocessing notebook geocodes tens of thousands of unique addresses through Nominatim, which rate-limits to one request per second. From scratch it takes hours. The raw SDPD CSV alone is several hundred MB and requires accounts on the City of San Diego open data portal, Kaggle, and the Census FTP. Sharing the cleaned outputs skips all of that.

### Step 1 — Make the data folder

Create `data/processed/` at the repo root, next to `notebooks/`. The notebooks read from `../data/processed/...`, so the folder must sit there for the code to work. The folder is gitignored on purpose because the files are too large for GitHub.

### Step 2 — Download the processed files

From the Google Drive folder created by Matthew:

**https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing**

Place all three in `data/processed/`:

- `crime_final_gdf.gpkg` : geocoded crime points
- `walkability_final_gdf.gpkg` : block group polygons with walkability scores
- `geocode_cache.json` : cached Nominatim lookups (do not delete; lets re-runs of the preprocessing notebook resume instead of re-geocoding from zero)

### Step 3 — Sanity check

Your folder should look like:

```
data/processed/
  crime_final_gdf.gpkg
  walkability_final_gdf.gpkg
  geocode_cache.json
```

You're done. The scoring/routing work reads directly from `data/processed/`.

### Optional — rerun preprocessing from raw data

Only needed if you want to refresh the data (e.g., a newer year of SDPD calls). Steps and download links are in [`docs/methodology.md`](docs/methodology.md#optional--rerun-from-raw-data).

A note on what "done" means for the data: the processed files load cleanly, columns are standardized, every crime row has coordinates, and every block group has a score and a polygon. That's *technically* clean. Whether the data is *analytically* sufficient — whether crime calls for service is the right signal for "feeling unsafe", whether NatWalkInd captures the right notion of "comfort", whether 2026 Q1 is enough history — is open and worth interrogating as the scoring work progresses.

## Reference documents (in `docs/`)

External documentation we use to interpret the data.

- [SDPD Call Type Codes](https://data.sandiego.gov/datasets/police-calls-call-types/) — definitions for all 234 call type codes
- [SDPD Disposition Codes](https://data.sandiego.gov/datasets/police-calls-disposition-codes/) — definitions for disposition codes (A, R, U, K, etc.)
- [SDPD Dispatch Priority Definitions](https://seshat.datasd.org/police_calls_for_service/pd_cfs_priority_defs_datasd.pdf) — priority levels 0–4 and 9
- [EPA Smart Location Database Technical Documentation v3.0](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf) — full data dictionary including `NatWalkInd`

The first three call-type/disposition/priority files are also bundled in `docs/` as CSV/PDF for offline reference.

## Where to read more

- [`docs/methodology.md`](docs/methodology.md) : scoring assumptions, route-cost formula, route modes, and limitations.
- [`docs/status/`](docs/status/) : short weekly status files, one per week. Read the most recent one to see what is in flight.
- [`notebooks/`](notebooks/) Notebooks themselves : the markdown cells inside `notebooks/crime-df-preprocessing.ipynb` and `notebooks/walkability-df-preprocessing.ipynb` document each preprocessing decision in context.

## Where to read even more

- [`docs/pipeline.md`](docs/pipeline.md) : how data moves from typed address to displayed route.
- [`docs/preprocessing.md`](docs/pipeline.md) : how processed data files were created and how to validate them.

