# Status

The single live status file for SafePath. Update it as the project moves. Past weekly snapshots live in `docs/status/` if anyone wants the history.

_Last updated: end of Week 4_

## Big picture

We have cleaned crime and walkability. The next milestone is scoring a small slice of the OSM walking network end to end, using two more cleaned datasets that Max is starting on.

## This week's owners

| Person | Task | Doc to read | Status |
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

## Open questions to resolve this week

1. Should the user choose a time of day (day vs night) in the app, or do we infer it from the system clock?
2. How do we label neighborhoods with very few SDPD calls? Truly safe, or underreported?
3. What is the default value for a missing feature on an edge (drop the term, or use a neutral 0.5)?

## Pick this up if you have time

These do not need a specific owner. Anyone can grab one.

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
