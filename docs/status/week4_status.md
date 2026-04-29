# Week 4 status

A short weekly snapshot for the SafePath team. Anyone can edit this file. Save next week as `week5_status.md` next to it.

**Date range:** end of Week 4
**Team:** Vanshika (mentor), Matthew, Max, Ruhan, Ajay
**Overall status:** on track or not?

## What got done this week

1. Crime preprocessing notebook is complete. Output: `crime_final_gdf.gpkg`.
2. Walkability preprocessing notebook is complete. Output: `walkability_final_gdf.gpkg`.
3. Processed files are shared in the team Google Drive so nobody has to rerun geocoding.
4. README and methodology doc are cleaned up so a new teammate can set up the data without asking.

## What we are doing next week (Week 5)

1. Move the proven scoring logic out of the notebooks into a small Python file under `src/`.
2. Stand up a placeholder Streamlit page in `app/` (two address inputs, a button, no routing yet).
3. Pick weights for the safety cost (how much do crime, walkability, lighting, road type each count).

## Blockers and decisions we need

1. We have not decided whether the app should ask the user for time of day. The crime data supports day vs night but the UI does not ask yet. Decision needed before scoring weights are locked in.
2. Some neighborhoods have very few SDPD calls. We need to decide how to label these on the map (truly safe, or just underreported).

## Pick this up if you have time

If you want a small concrete first task this week, any of these are useful:

1. Open both `.gpkg` files in a fresh notebook and use `gdf.explore()` to plot them on a map. Eyeball that the points and polygons look right.
2. Spot check 10 random crime addresses in the geocoded file against Google Maps to confirm they land on the correct intersection.
3. Sketch on paper what the Streamlit result page should show first (map, score, explanation).

## Notes for the team

We have 4 people and roughly 10 hours each per week, so plan small. One file or one notebook cell is plenty for a week. Drop a quick note in Discord when you start something so we do not double up.

## Where things live

1. Final code, instructions, and project knowledge: this GitHub repo.
2. Large processed data files: team Google Drive (link in `README.md`).
3. Quick chat and questions: Discord.
4. Meeting minutes and brainstorming: team Google Drive (notes folder).
