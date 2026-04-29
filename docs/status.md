# Status

<<<<<<< HEAD
> **TL;DR.** Crime + walkability cleaned. Next: Max cleans street lights and bike lanes; Matthew designs the scoring weights; Ruan prototypes scoring on a test neighborhood; AJ compares weight settings.

_Last updated: end of Week 4 → moving into Week 5._

Past weekly snapshots live in [`status/`](status/). This file is the single source of truth for "where are we right now."
=======
The single live status file for SafePath. Update it as the project moves. Past weekly snapshots live in `docs/status/` if anyone wants the history.

_Last updated: end of Week 4_

## Big picture

We have cleaned crime and walkability. The next milestone is scoring a small slice of the OSM walking network end to end, using two more cleaned datasets that Max is starting on.
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

## This week's owners

| Person | Task | Doc to read | Status |
<<<<<<< HEAD
| - | - | - | - |
| Matthew | Design the weighted score for safety + convenience | [`04_scoring_methodology.md`](04_scoring_methodology.md) | in progress |
| Max | Clean the street lights + buffered bike lane datasets | [`02_data_cleaning.md`](02_data_cleaning.md) | not started |
| Ruan | Feature engineering + initial scoring on sample routes | [`03_feature_engineering.md`](03_feature_engineering.md), [`04_scoring_methodology.md`](04_scoring_methodology.md) | not started |
| AJ | Compare how different weights change route results | [`04_scoring_methodology.md`](04_scoring_methodology.md) | blocked on Matthew |

## Big picture

We finished cleaning crime and walkability. The next milestone is scoring a small slice of the OSM walking network end to end, using two more cleaned datasets that Max is starting on.

## Done

| What | Where |
| - | - |
| Crime preprocessing | [`crime-df-preprocessing.ipynb`](../notebooks/crime-df-preprocessing.ipynb) → `crime_final_gdf.gpkg` |
| Walkability preprocessing | [`walkability-df-preprocessing.ipynb`](../notebooks/walkability-df-preprocessing.ipynb) → `walkability_final_gdf.gpkg` |
| Processed files shared | team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing) |
| Repo docs split into 5 step learning path | `docs/00` through `docs/04` plus this file |

## In progress

1. **Matthew** is drafting the weighting between crime, walkability, lighting, bike comfort, and road class.
2. **Ruan** is wiring up the OSM walking graph and attaching crime + walkability features to a small test area.

## Not started

1. **Max:** pull and clean the [San Diego street lights dataset](https://data.sandiego.gov).
2. **Max:** pull and clean the [buffered bike + scooter lanes dataset](https://data.sandiego.gov).

## Blocked

| Who | What | Blocked on |
| - | - | - |
| AJ | weight comparison | needs at least one draft scoring formula from Matthew |
| Lighting + bike comfort features | Max finishing cleaning |
=======
| --- | --- | --- | --- |
| Matthew | Design the weighted score for safety and convenience | `04_scoring_methodology.md` | in progress |
| Max | Clean the street lights and buffered bike lane datasets | `02_data_cleaning.md` | not started |
| Ruan | Feature engineering and initial scoring on sample routes | `03_feature_engineering.md`, `04_scoring_methodology.md` | not started |
| AJ | Compare how different weighted scores change route results | `04_scoring_methodology.md` | blocked on Matthew |

## Done

1. Crime preprocessing notebook produces `crime_final_gdf.gpkg`.
2. Walkability preprocessing notebook produces `walkability_final_gdf.gpkg`.
3. Both processed files are shared in the team Google Drive.
4. Repo docs split into a 5 step learning path (`00` to `04`).

## In progress

1. Matthew is drafting the weighting between crime, walkability, lighting, bike comfort, and road class.
2. Ruan is wiring up the OSM walking graph and attaching crime and walkability features to a small test area.

## Not started

1. Max: pull and clean the San Diego street lights dataset.
2. Max: pull and clean the buffered bike and scooter lanes dataset.

## Blocked

1. AJ is blocked on Matthew. The weight comparison work needs at least one draft scoring formula to compare against.
2. Lighting and bike comfort features in `03_feature_engineering.md` are blocked on Max.
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

## Open questions to resolve this week

1. Should the user choose a time of day (day vs night) in the app, or do we infer it from the system clock?
2. How do we label neighborhoods with very few SDPD calls? Truly safe, or underreported?
<<<<<<< HEAD
3. What is the default for a missing feature on an edge: drop the term, or use a neutral 0.5?
=======
3. What is the default value for a missing feature on an edge (drop the term, or use a neutral 0.5)?
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

## Pick this up if you have time

These do not need a specific owner. Anyone can grab one.

<<<<<<< HEAD
| Task | Why it helps |
| - | - |
| Open both `.gpkg` files in a fresh notebook and call `gdf.explore()` | sanity checks the cleaned data |
| Spot check 10 random crime addresses against [Google Maps](https://www.google.com/maps) | validates geocoding quality |
| Sketch the Streamlit result page on paper | unblocks the Week 6 UI work |

## Where things live

| Type of thing | Lives in |
| - | - |
| Final code, instructions, project knowledge | this repo |
| Large processed data | team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing) |
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
=======
1. Open both `.gpkg` files in a fresh notebook and call `gdf.explore()` to view them on a map.
2. Spot check 10 random crime addresses against Google Maps to confirm they land near the right intersection.
3. Sketch the Streamlit result page on paper. What does the user see first?

## Where things live

1. Final code, instructions, and project knowledge: this repo.
2. Large processed data: team Google Drive (link in `README.md`).
3. Quick chat: Discord.
4. Meeting notes and brainstorming: Google Drive notes folder.

## Capacity reminder

5 people, each with roughly 5 to 10 hours per week. Plan small. One file or one notebook per person per week is plenty. Drop a quick note in Discord when you start something so two people do not pick up the same task.
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb
