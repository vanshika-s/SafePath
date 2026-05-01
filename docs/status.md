# Status

> **TL;DR.** Crime, walkability, and **street lights are cleaned**. Next: Max cleans bike lanes; Matthew designs the scoring weights; Ruan prototypes scoring on a test neighborhood (now with lighting); AJ compares weight settings.

_Last updated: end of Week 4 → moving into Week 5._

Past weekly snapshots live in [`status/`](status/). This file is the single source of truth for "where are we right now."

## This week's owners

| Person | Task | Doc to read | Status |
| - | - | - | - |
| Matthew | Design the weighted score for safety + convenience | [`04_scoring_methodology.md`](04_scoring_methodology.md) | in progress |
| Max | Clean the buffered bike + scooter lane dataset | [`02_data_cleaning.md`](02_data_cleaning.md) | not started |
| Ruan | Feature engineering + initial scoring on sample routes (now includes lighting) | [`03_feature_engineering.md`](03_feature_engineering.md), [`04_scoring_methodology.md`](04_scoring_methodology.md) | not started |
| AJ | Compare how different weights change route results | [`04_scoring_methodology.md`](04_scoring_methodology.md) | blocked on Matthew |

## Big picture

Crime, walkability, and street lights are cleaned. The next milestone is scoring a small slice of the OSM walking network end to end. Bike lanes are the only remaining cleaning task (Max).

## Done

| What | Where |
| - | - |
| Crime preprocessing | [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb) → `crime_final_gdf.gpkg` |
| Walkability preprocessing | [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb) → `walkability_final_gdf.gpkg` |
| Streetlight cleaning + validation | `src/data/get_streetlights.py` + `src/data/clean_streetlights.py` → `data/processed/streetlights/streetlights_processed.geojson` (55,506 active lights, validation + tie-out PASS, snapshot 2026-04-30) |
| Crime + walkability files shared | team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing) |
| Repo docs split into 5 step learning path | `docs/00` through `docs/04` plus this file |

## In progress

1. **Matthew** is drafting the weighting between crime, walkability, lighting, bike comfort, and road class.
2. **Ruan** is wiring up the OSM walking graph and attaching crime + walkability features to a small test area. Lighting (L1 from `docs/data/streetlights/FEATURE_CONTRACT.md`) can be added on the same slice now that the source data is ready.

## Not started

1. **Max:** pull and clean the [buffered bike + scooter lanes dataset](https://data.sandiego.gov).
2. Compute lighting features L1–L5 against OSM edges (waiting on UCSD campus polygon decision for L4).

## Blocked

| Who | What | Blocked on |
| - | - | - |
| AJ | weight comparison | needs at least one draft scoring formula from Matthew |
| Bike comfort feature | Max finishing bike-lane cleaning |
| Lighting L4 (`lighting_data_quality_flag`) | UCSD campus polygon source decision (SANGIS vs. hand-built bbox) |

## Open questions to resolve this week

1. Should the user choose a time of day (day vs night) in the app, or do we infer it from the system clock?
2. How do we label neighborhoods with very few SDPD calls? Truly safe, or underreported?
3. What is the default for a missing feature on an edge: drop the term, or use a neutral 0.5? (Lighting already has a built-in `0.5` fallback for UCSD-interior edges.)
4. UCSD campus polygon: SANGIS layer or hand-built bbox for v0?

## Pick this up if you have time

These do not need a specific owner. Anyone can grab one.

| Task | Why it helps |
| - | - |
| Open the cleaned `.gpkg` and `.geojson` files in a fresh notebook and call `.explore()` | sanity checks the cleaned data |
| Spot check 10 random crime addresses against [Google Maps](https://www.google.com/maps) | validates geocoding quality |
| Sketch the Streamlit result page on paper | unblocks the Week 6 UI work |

## Where things live

| Type of thing | Lives in |
| - | - |
| Final code, instructions, project knowledge | this repo |
| Large processed data (crime, walkability) | team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing) |
| Streetlight data | committed to the repo under `data/` |
| Quick chat | Discord |
| Meeting notes + brainstorming | Google Drive notes folder |
| Sprint timeline + design intent | [original design doc](https://docs.google.com/document/d/1gufXZGHToZtFlsREL3u_rizqxXCKs3DR3LbKhO05fSc/edit?usp=sharing) |
| GitHub crash course | [workshop slides](https://docs.google.com/presentation/d/1WPHBVzyirhDXo6mF61rogD_oO6OWuwoV/edit?slide=id.p1#slide=id.p1) |

## Capacity reminder

5 people, roughly 5 to 10 hours each per week. **Plan small.** One file or one notebook per person per week is plenty. Drop a note in Discord when you start something so two people do not pick up the same task.

## How to update this file

1. Edit the table for "This week's owners" first. Status column should read: `not started`, `in progress`, `blocked`, or `done`.
2. Move finished items into the "Done" table with a date.
3. Move new questions into "Open questions."
4. Commit straight to `main` if changes are small. Otherwise open a PR.

If you want a frozen snapshot of this week's status, copy this file into [`status/week5_status.md`](status/) before making big edits.
