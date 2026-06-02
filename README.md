# SafePath

> SafePath recommends walking routes in San Diego that feel safer and more comfortable, not just the fastest. Every street segment is scored using crime, walkability, lighting, and infrastructure data; then three routes (fastest, safest, balanced) are returned with turn-by-turn directions and a per-segment safety breakdown.

[![Live app](https://img.shields.io/badge/live-safepaths.onrender.com-brightgreen)](https://safepaths.onrender.com) [![Course](https://img.shields.io/badge/DS3-Spring_2026-purple)](https://www.ds3atucsd.com)

## Try it

**[safepaths.onrender.com](https://safepaths.onrender.com)**

Type any two San Diego addresses. SafePath returns three routes on an interactive map, with distance, estimated walk time, safety score, crime density, and step-by-step directions for each.

## What SafePath does

1. User enters a **start** and a **destination** anywhere in San Diego.
2. The API geocodes both addresses, snaps them to the OSM walking network, and runs Dijkstra three times on pre-scored edge weights.
3. Three routes come back: **fastest** (minimize distance), **safest** (minimize safety cost), **balanced** (blend of both).
4. Each route includes per-segment safety, crime, walkability, and infrastructure scores plus turn-by-turn steps.
5. Crime points near the route are overlaid as a heat map so the user can see what the scores are based on.

## How scoring works

Every street edge has a `safety_score` (0–1) computed from three features:

```
safety_score = 0.50 × crime_score  +  0.25 × walk_score  +  0.25 × infrastructure   (day)
safety_score = 0.45 × crime_score  +  0.25 × walk_score  +  0.30 × infrastructure   (night)
```

That score becomes a routing cost: `safety_cost = length × (1 + 4 × (1 − safety_score))` — so a dangerous street looks up to 5× longer to Dijkstra. All percentages displayed in the UI are **length-weighted** (longer edges count more than short ones), derived by back-calculating from `safety_cost`.

## How it is built

### Data pipeline (notebooks)

| Notebook | What it does |
| - | - |
| `crime-df-preprocessing.ipynb` | Cleans raw SDPD calls for service, geocodes addresses, filters to walking-relevant crimes, outputs `crime_final_gdf.gpkg` |
| `walkability-df-preprocessing.ipynb` | Joins EPA Smart Location block-group walkability scores to the SD street network |
| `safety-score-edge.ipynb` | Builds the fast numpy/scipy `RouteGraph` from scored edges: loads the OSM graph, attaches crime + walk + lighting + infrastructure scores to every edge, computes `safety_cost` and `balanced_cost` weight arrays, saves them as numpy files |
| `scoring-engine.ipynb` | Exploratory: tests the scoring formula and weight choices on sample routes before committing them to the production graph |
| `scoring-test.ipynb` | Spot-checks routes across different neighborhoods for sanity |

### Source modules (`src/api/`)

| File | Responsibility |
| - | - |
| `graph_store.py` | `RouteGraph` class — loads numpy edge arrays into memory, builds a KDTree for nearest-node lookup and CSR weight matrices for Dijkstra. Exposes `route_fastest`, `route_safest`, `route_balanced`, `path_length_m`, `path_time_min`, `path_coords`, `path_edge_scores`, `path_steps`. No NetworkX at runtime. |
| `loader.py` | Downloads `fast_graph.zip` and `crime_final_gdf.gpkg` from GCS on first run, then caches them in memory. |
| `geocoder.py` | `address_to_latlng` — wraps Nominatim with an LRU cache and appends `, San Diego, CA` so short queries resolve correctly. |
| `day_night.py` | `is_night_now` — uses `astral` to compute real sunrise/sunset for San Diego and returns `True` if the current time is outside daylight hours. Drives which crime weight arrays the router reads. |
| `router.py` | `get_routes` — thin wrapper: snaps start/end to nearest nodes, classifies route length (short / medium / long) to select the right pre-scored weight array, calls the three Dijkstra variants. |
| `pipeline.py` | `run(origin, destination)` — orchestrates the full call: load graph → geocode → route → format output. Single entry point for both the FastAPI server and the Streamlit app. |

### App layer (`app/`)

| File | What it is |
| - | - |
| `api_server.py` | FastAPI server. `GET /api/route?origin=...&destination=...` calls `pipeline.run`, trims the crime point payload to a bounding box around the routes, and returns JSON. Also serves the static landing page (`landing/`) at `/`. |
| `app.py` | Streamlit app (alternate UI). Same `pipeline.run` call, rendered with Folium maps and route cards in a sidebar. |

### Landing page (`landing/`)

Custom HTML/JS front end served by the FastAPI server. Fetches `/api/route`, draws routes on a Leaflet map, and renders route cards with a step list.

### Tests (`tests/`)

| File | Covers |
| - | - |
| `test_graph_store.py` | `_dijkstra` correctness; all `RouteGraph` public methods via a synthetic 4-node in-memory graph (no files needed) |
| `test_pipeline.py` | `pipeline.run` end-to-end with all external calls mocked |
| `test_router.py` | `get_routes` — route modes, length classification, node snapping |
| `test_geocoder.py` | `address_to_latlng` — caching, error handling, address normalization |
| `test_day_night.py` | `is_night` — SD timezone correctness, sunrise/sunset boundaries |

Run all tests:

```bash
pytest tests/ -v
```

## Quick start

```bash
git clone https://github.com/vanshika-s/SafePath.git
cd SafePath
pip install -r requirements.txt
```

### Run the API server (recommended)

```bash
uvicorn app.api_server:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) for the landing page. On first run the server downloads `fast_graph.zip` (~300 MB) and `crime_final_gdf.gpkg` (~98 MB) from GCS automatically. Subsequent starts load from disk.

### Run the Streamlit app

```bash
streamlit run app/app.py
```

## Data setup (for notebook work)

The route graph and crime data are auto-downloaded by the API server. For notebook-level preprocessing you need the raw and processed files from Google Drive.

Open the team folder: [SafePath data](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing).

Download into `data/processed/`:

| File | Size | What it is |
| - | - | - |
| `crime_final_gdf.gpkg` | 98 MB | geocoded, scored crime points |
| `walkability_final_gdf.gpkg` | 5.5 MB | block-group walkability polygons |
| `edge_scores_infrastructure.csv` | 50 MB | per-edge crime, walk, and infrastructure scores |
| `sd_walk_graph.graphml` | 300 MB | full San Diego OSM walking network |
| `fast_graph.zip` | ~300 MB | pre-built numpy RouteGraph (what the server loads) |

Download into `data/processed/streetlights/`:

| File | Size | What it is |
| - | - | - |
| `streetlights_processed.geojson` | 15 MB | 55,506 operational SD streetlights |

## Repo layout

```
SafePath/
├── README.md
├── requirements.txt
├── app/
│   ├── api_server.py        FastAPI server + static file host
│   └── app.py               Streamlit UI
├── landing/
│   ├── index.html           landing page
│   ├── app.html             map app page
│   └── routes.js            front-end routing / map logic
├── src/
│   ├── api/
│   │   ├── graph_store.py   RouteGraph + _dijkstra
│   │   ├── loader.py        GCS download + in-memory cache
│   │   ├── geocoder.py      Nominatim wrapper
│   │   ├── day_night.py     sunrise/sunset check
│   │   ├── router.py        get_routes()
│   │   └── pipeline.py      run() — main entry point
│   └── data/
│       └── clean_streetlights.py
├── notebooks/
│   ├── crime-df-preprocessing.ipynb
│   ├── walkability-df-preprocessing.ipynb
│   ├── safety-score-edge.ipynb
│   ├── scoring-engine.ipynb
│   └── scoring-test.ipynb
├── tests/
│   ├── test_graph_store.py
│   ├── test_pipeline.py
│   ├── test_router.py
│   ├── test_geocoder.py
│   └── test_day_night.py
└── docs/
    ├── 00_project_map.md
    ├── 01_data_sources.md
    ├── 02_data_cleaning.md
    ├── 03_feature_engineering.md
    ├── 04_scoring_methodology.md
    └── status.md
```

## Docs

| Doc | What it covers |
| - | - |
| [`docs/00_project_map.md`](docs/00_project_map.md) | Project overview and doc index |
| [`docs/01_data_sources.md`](docs/01_data_sources.md) | Where each dataset comes from |
| [`docs/02_data_cleaning.md`](docs/02_data_cleaning.md) | How raw data gets cleaned |
| [`docs/03_feature_engineering.md`](docs/03_feature_engineering.md) | How features are attached to OSM edges |
| [`docs/04_scoring_methodology.md`](docs/04_scoring_methodology.md) | Scoring formula and route cost logic |
| [`docs/status.md`](docs/status.md) | Current sprint status |

## Reference materials

| Source | Use |
| - | - |
| [SDPD Call Type Codes](https://data.sandiego.gov/datasets/police-calls-call-types/) | definitions for all 234 call type codes |
| [SDPD Disposition Codes](https://data.sandiego.gov/datasets/police-calls-disposition-codes/) | what each disposition letter means |
| [EPA Smart Location Database v3.0 (PDF)](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf) | full data dictionary including `NatWalkInd` |

## Team

DS3 at UC San Diego — Spring 2026. Lead: Vanshika.
For quick chat use Discord; meeting notes are in the team [Google Drive](https://docs.google.com/document/d/1gufXZGHToZtFlsREL3u_rizqxXCKs3DR3LbKhO05fSc/edit?usp=sharing).
