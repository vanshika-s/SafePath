# Week 4 status

A short weekly snapshot for the SafePath team. Anyone can edit this file. Save next week as `week5_status.md` next to it.

**Date range:** end of Week 4, Apr 26, 2026  
**Team:** Matthew, Max, Ruhan, Ajay  
**Mentor:** Vanshika  
**Overall status:** On track. Crime and walkability preprocessing are mostly complete, and the next major step is assigning safety scores to street segments.

## What got done this week

1. Matthew merged the main preprocessing work into `main`.
2. Crime data from SDPD Calls for Service was filtered to confirmed incidents only using relevant disposition codes.
3. Crime data was narrowed to pedestrian-relevant call types that may affect walking safety.
4. Crime incidents were geocoded so each incident has latitude and longitude coordinates.
5. EPA walkability data was filtered from the national dataset down to San Diego block groups.
6. Census TIGER shapefiles were merged with the walkability data so each block group has polygon geometry.
7. The cleaned crime and walkability files are now closer to being usable for spatial lookups and route scoring.
8. README and methodology documentation were cleaned up so teammates can better understand setup and project direction.

## Why this matters

The main goal of this preprocessing work is to create clean, geocoded data that can be connected to the San Diego street network. Once each street segment has nearby crime and walkability information, SafePath can score routes based on safety and comfort instead of only shortest distance.

## What we are doing next week (Week 5)

1. Use the latitude and longitude crime data to connect incidents to nearby street segments.
2. Use OSMnx and OpenStreetMap data to build a San Diego street network.
3. Use NetworkX to generate walking routes between intersections or addresses.
4. Start assigning a safety score to each edge, meaning each street segment between two nodes.
5. Move proven scoring logic out of notebooks into a small Python file under `src/`.
6. Stand up a placeholder Streamlit page in `app/` if time allows.

## Blockers and decisions we need

1. We have not decided whether the app should ask the user for time of day. The crime data may support day versus night, but the UI does not ask yet.
2. Some neighborhoods may have fewer SDPD calls because of underreporting, not because they are truly safer.
3. We still need to decide how much weight crime, walkability, lighting, and road type should have in the final route score.

## Pick this up if you have time

If you want a small concrete first task this week, any of these are useful:

1. Open the processed `.gpkg` files in a fresh notebook and use `gdf.explore()` to check whether the points and polygons look right.
2. Spot check 10 random geocoded crime locations against Google Maps to confirm they land near the correct address or intersection.
3. Sketch what the Streamlit result page should show first, such as the map, route score, and explanation.
4. Look at one street segment and think through what information it needs before we can call it safer or less safe.

## Notes for the team

We have 4 student teammates and one mentor. Plan small for each week. One file, one notebook section, or one clear check is enough. Drop a quick note in Discord when you start something so we do not double up.

## Where things live

1. Final code, instructions, and project knowledge: this GitHub repo.
2. Large processed data files: team Google Drive, linked in `README.md`.
3. Quick chat and questions: Discord.
4. Meeting minutes and brainstorming: team Google Drive notes folder.
