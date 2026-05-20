# SafePath

> **TL;DR.** SafePath recommends walking routes in San Diego that feel safer and more comfortable, not just the fastest. We score every street segment using crime, walkability, lighting, and bike lane data, then pick three routes (fastest, safest, balanced) and explain why.

[![Status](https://img.shields.io/badge/status-active--development-yellow)](docs/status.md) [![Docs](https://img.shields.io/badge/docs-5_step_path-blue)](docs/00_project_map.md) [![Course](https://img.shields.io/badge/DS3-Spring_2026-purple)](https://www.ds3atucsd.com)

## What is SafePath

A route recommendation tool aimed at people who feel vulnerable walking alone. Students, women, anyone walking at night or in unfamiliar areas. The user enters a start and a destination, picks a preference (fastest, safest, balanced), and gets a route plus a plain English explanation of why it scored that way.

This is a quarter long student data science project run through [DS3 at UC San Diego](https://www.ds3atucsd.com).

## Start here (read in this order)

| # | Doc | What you get |
| - | - | - |
| 1 | This README | Project pitch, install, data setup |
| 2 | [`docs/00_project_map.md`](docs/00_project_map.md) | The full 5 step learning path |
| 3 | [`docs/status.md`](docs/status.md) | Who is doing what right now |

For meeting notes, see the team [Google Drive](https://docs.google.com/document/d/1gufXZGHToZtFlsREL3u_rizqxXCKs3DR3LbKhO05fSc/edit?usp=sharing) and [GitHub workshop slides](https://docs.google.com/presentation/d/1WPHBVzyirhDXo6mF61rogD_oO6OWuwoV/edit?slide=id.p1#slide=id.p1). Quick chat is on Discord.

## Quick start (3 minutes)

```bash
git clone https://github.com/vanshika-s/SafePath.git
cd SafePath
pip install -r requirements.txt
```

Then download data (next section), then open a notebook:

```bash
jupyter notebook notebooks/
```

## Data setup (one time)

> **Why download instead of regenerating?** The crime preprocessing notebook geocodes thousands of addresses through Nominatim at 1 request per second, which takes hours. The graph and scoring outputs take even longer. We share the cleaned outputs so you can skip all of that.

> **Note on data and git:** All data files live outside git in Google Drive. The `data/` folder is gitignored. Raw source files (streetlights, police calls, EPA, census) and all processed outputs are stored in the team Drive folder below.

### Step 1. Make the local data folders

```bash
mkdir -p data/processed/streetlights
```

### Step 2. Download from Google Drive

Open the team folder: [SafePath data](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing).

**Processed outputs** — download into `data/processed/`:

| File | Size | What it is | Do not delete |
| - | - | - | - |
| `crime_final_gdf.gpkg` | 98 MB | geocoded, scored crime points | |
| `walkability_final_gdf.gpkg` | 5.5 MB | block group polygons with walkability scores | |
| `edge_scores_infrastructure.csv` | 50 MB | per-edge crime, walk, and infrastructure scores | |
| `sd_walk_graph.graphml` | 300 MB | San Diego OSM walking network graph | |
| `geocode_cache.json` | 1.3 MB | cached Nominatim lookups | yes |

**Processed streetlights** — download into `data/processed/streetlights/`:

| File | Size | What it is |
| - | - | - |
| `streetlights_processed.geojson` | 15 MB | cleaned streetlight points with quality flags |

> **Raw source files** (streetlights, police calls, EPA, census) are public datasets — download them directly from their original sources. See [`docs/01_data_sources.md`](docs/01_data_sources.md) for links.

### Step 3. Sanity check

Your folder should now look like:

```
data/
  processed/
    crime_final_gdf.gpkg
    walkability_final_gdf.gpkg
    edge_scores_infrastructure.csv
    sd_walk_graph.graphml
    geocode_cache.json
    streetlights/
      streetlights_processed.geojson
```

Done. The scoring and routing notebooks read from these folders.

For deeper preprocessing details, see [`docs/02_data_cleaning.md`](docs/02_data_cleaning.md).

## Repo layout

```
SafePath/
├── README.md                    you are here
├── requirements.txt
├── .gitignore
├── notebooks/                   preprocessing notebooks
│   ├── crime-df-preprocessing.ipynb
│   └── walkability-df-preprocessing.ipynb
├── docs/                        the 5 step learning path
│   ├── 00_project_map.md
│   ├── 01_data_sources.md
│   ├── 02_data_cleaning.md
│   ├── 03_feature_engineering.md
│   ├── 04_scoring_methodology.md
│   ├── status.md
│   ├── status/                  older weekly snapshots
│   └── references/              SDPD code books (CSV/PDF)
├── src/                         planned, empty for now
└── app/                         planned, empty for now
```

## Reference materials

External docs we use to interpret the data:

| Source | Use |
| - | - |
| [SDPD Call Type Codes](https://data.sandiego.gov/datasets/police-calls-call-types/) | definitions for all 234 call type codes |
| [SDPD Disposition Codes](https://data.sandiego.gov/datasets/police-calls-disposition-codes/) | what each disposition letter means |
| [SDPD Priority Definitions (PDF)](https://seshat.datasd.org/police_calls_for_service/pd_cfs_priority_defs_datasd.pdf) | priority levels 0 to 4 and 9 |
| [EPA Smart Location Database v3.0 (PDF)](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf) | full data dictionary including `NatWalkInd` |

The first three are also bundled offline in [`docs/references/`](docs/references/).

## Team

5 people. Lead: Vanshika. This week's owners are tracked in [`docs/status.md`](docs/status.md).

## Where to read more

| You want to know about | Open |
| - | - |
| Where each dataset comes from | [`01_data_sources.md`](docs/01_data_sources.md) |
| How data gets cleaned | [`02_data_cleaning.md`](docs/02_data_cleaning.md) |
| How features get attached to street edges | [`03_feature_engineering.md`](docs/03_feature_engineering.md) |
| The scoring formula and route logic | [`04_scoring_methodology.md`](docs/04_scoring_methodology.md) |
| What is in flight this week | [`status.md`](docs/status.md) |
