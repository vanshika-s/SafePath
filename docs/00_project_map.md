# 00. Project map

> **TL;DR.** SafePath turns public datasets (crime, walkability, lights, bike lanes, OpenStreetMap streets) into a per segment safety score, then picks three routes (fastest, safest, balanced) and explains why. This file tells you which doc to read for your task.

## What SafePath does, in 3 lines

1. User enters a **start** and a **destination** in San Diego.
2. SafePath returns **3 routes**: fastest, safest, balanced.
3. Each route has a **plain English explanation** of why it scored that way.

## The 5 step project flow

Read each step in order. Every step has its own doc.

```
data sources           →   01_data_sources.md
data cleaning          →   02_data_cleaning.md
feature engineering    →   03_feature_engineering.md
scoring methodology    →   04_scoring_methodology.md
current team status    →   status.md
```

Plain English version:

| Step | Question it answers | Doc |
| - | - | - |
| 1 | What public datasets do we use and why? | [`01_data_sources.md`](01_data_sources.md) |
| 2 | How do we clean each dataset so it loads and joins? | [`02_data_cleaning.md`](02_data_cleaning.md) |
| 3 | How do we attach features to OSM street edges? | [`03_feature_engineering.md`](03_feature_engineering.md) |
| 4 | How do we score edges and pick routes? | [`04_scoring_methodology.md`](04_scoring_methodology.md) |
| 5 | Who is doing what right now? | [`status.md`](status.md) |

## Pick the right doc for your task

| Your task | Read these |
| - | - |
| Understand the scoring formula and weight choices | [`04_scoring_methodology.md`](04_scoring_methodology.md) |
| Understand how features are attached to OSM edges | [`03_feature_engineering.md`](03_feature_engineering.md) |
| Understand how raw data was cleaned | [`02_data_cleaning.md`](02_data_cleaning.md) |
| Add a new data source | [`01_data_sources.md`](01_data_sources.md), [`03_feature_engineering.md`](03_feature_engineering.md) |
| Run the app locally or add an API endpoint | `app/api_server.py`, `src/api/pipeline.py` |
| Add or fix a test | `tests/`, `src/api/graph_store.py` |
| New teammate, no specific task yet | [`01_data_sources.md`](01_data_sources.md), then [`status.md`](status.md) |

## Where things live

| Type of thing | Lives in |
| - | - |
| Final code, instructions, and project knowledge | this GitHub repo |
| Large processed data files | team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing) |
| Quick chat | Discord |
| Meeting notes and brainstorming | team Google Drive notes folder |
| GitHub crash course materials | [GitHub workshop slides](https://docs.google.com/presentation/d/1WPHBVzyirhDXo6mF61rogD_oO6OWuwoV/edit?slide=id.p1#slide=id.p1) |

If a Google Doc starts holding final project knowledge, port the short version into the right doc here.

## Sprint timeline (from the [original design doc](https://docs.google.com/document/d/1gufXZGHToZtFlsREL3u_rizqxXCKs3DR3LbKhO05fSc/edit?usp=sharing))

| Week | Goal | Status |
| - | - | - |
| 1 | Research, setup, define safety features | Done |
| 2 | Filter and clean crime + walkability data to San Diego | Done |
| 3 | Design route scoring (weighted scores per neighborhood) | Done |
| 4 | Prototype routing engine, generate route alternatives | Done |
| 5 | Move scoring + routing logic into reusable Python modules | Done — `src/api/` |
| 6 | Build map-based web app | Done — Streamlit + custom landing page |
| 7 | Write unit tests, validate routes across neighborhoods | Done — 51 tests passing |
| 8 | Deploy, prepare demo + final docs | Done — live at [safepaths.onrender.com](https://safepaths.onrender.com) |

See [`status.md`](status.md) for current open items.

## Repo at a glance

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
└── docs/                    you are here
    ├── 00_project_map.md
    ├── 01_data_sources.md
    ├── 02_data_cleaning.md
    ├── 03_feature_engineering.md
    ├── 04_scoring_methodology.md
    ├── status.md
    ├── status/              older weekly snapshots
    └── references/          SDPD code books (CSV/PDF)
```
