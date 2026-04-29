# SafePath

> **TL;DR.** SafePath recommends walking routes in San Diego that feel safer and more comfortable, not just the fastest. We score every street segment using crime, walkability, lighting, and bike lane data, then pick three routes (fastest, safest, balanced) and explain why.

[![Status](https://img.shields.io/badge/status-active--development-yellow)](docs/status.md) [![Docs](https://img.shields.io/badge/docs-5_step_path-blue)](docs/00_project_map.md) [![Course](https://img.shields.io/badge/DS3-Spring_2026-purple)](https://ds3.ucsd.edu)

## What is SafePath

A route recommendation tool aimed at people who feel vulnerable walking alone. Students, women, anyone walking at night or in unfamiliar areas. The user enters a start and a destination, picks a preference (fastest, safest, balanced), and gets a route plus a plain English explanation of why it scored that way.

This is a quarter long student data science project run through [DS3 at UC San Diego](https://ds3.ucsd.edu).

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

> **Why download instead of regenerating?** The crime preprocessing notebook geocodes thousands of addresses through Nominatim at 1 request per second, which takes hours. We share the cleaned outputs so you can skip that step.

### Step 1. Make the local data folder

Create `data/processed/` at the repo root. The notebooks read from `../data/processed/...` so the folder must live there. It is gitignored on purpose because the files are too large for GitHub.

```bash
mkdir -p data/processed
```

### Step 2. Download from Google Drive

Open the team folder: [SafePath processed data](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing).

Download all three files into `data/processed/`:

| File | What it is | Do not delete |
| - | - | - |
| `crime_final_gdf.gpkg` | geocoded crime points | |
| `walkability_final_gdf.gpkg` | block group polygons with walkability scores | |
| `geocode_cache.json` | cached Nominatim lookups | yes |

### Step 3. Sanity check

Your folder should now look like:

```
data/processed/
  crime_final_gdf.gpkg
  walkability_final_gdf.gpkg
  geocode_cache.json
```

Done. The scoring and routing work reads from this folder.

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

You also keep a local `data/processed/` folder. Gitignored. See Data setup.

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
