<<<<<<< HEAD
# 04. Scoring methodology

> **TL;DR.** SafePath gives every street segment a `safety_score` (0 to 1, 1 is best), turns that into a `route_cost` the routing algorithm minimizes, then runs shortest path 3 times: fastest, safest, balanced. This doc is future facing. TODOs mark things still being decided.

**This week's owners:**

| Person | Task |
| - | - |
| Matthew | Design the weighted score for safety and convenience |
| AJ | Compare how different weights change route results |
| Ruan | Prototype initial scoring on a small test area |

## Where to find related docs

| Topic | Doc |
| - | - |
| Where the cleaning happens | [`02_data_cleaning.md`](02_data_cleaning.md) |
| How features get attached to OSM edges | [`03_feature_engineering.md`](03_feature_engineering.md) |
| Live status and decisions | [`status.md`](status.md) |

## Core idea

> SafePath scores each street segment first. A route is then evaluated by adding up the costs of the segments along that path.

Two layers:

| Layer | What it is | Range |
| - | - | - |
| `safety_score` per edge | weighted average of normalized features | 0 to 1 (1 = best) |
| `route_cost` per edge | length aware cost the router minimizes | meters, scaled |
=======
# Scoring methodology

> This document describes the planned SafePath scoring and routing methodology. The cleaned crime and walkability datasets are ready. The next step is to assign scores to street segments, build routes, and connect the results to the app.

Owners this week: Matthew (designs the weighted score), AJ (compares how different weights change routes). Ruan also touches this when prototyping initial scoring.

## Purpose of this document

This file describes the planned scoring and routing logic for SafePath. It is future facing. Where decisions are not made yet, you will see TODO. Once weights are agreed, replace the TODOs with the real values.

For raw download steps, cleaning recipes, and validation, see `02_data_cleaning.md`. For how features get attached to OSM edges, see `03_feature_engineering.md`.

## Core idea

SafePath scores each street segment first. A route is then evaluated by adding up the costs of the segments along that path.

Two layers:

1. `safety_score` per edge. A number between 0 and 1, where 1 is best.
2. `route_cost` per edge. A length aware cost the routing algorithm minimizes.
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

Lower route cost wins.

## Planned pipeline

```
user enters address
  → geocode address into coordinates
  → snap coordinates to OpenStreetMap walking network
<<<<<<< HEAD
  → assign crime + walkability features to each street edge
  → calculate safety score per edge
  → convert safety score into route cost
  → run shortest path 3 times (fastest, safest, balanced)
  → return route polylines + per segment explanation to the app
=======
  → assign crime and walkability features to each street edge
  → calculate safety score per edge
  → convert safety score into route cost
  → run shortest path 3 times (fastest, safest, balanced)
  → return route polylines and a per segment explanation to the app
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb
```

## Inputs to the score

<<<<<<< HEAD
Each edge will eventually carry these features (built in [`03_feature_engineering.md`](03_feature_engineering.md)):

| Feature | Range | Status |
| - | - | - |
| `crime_score_day`, `crime_score_night` | 0 to 1 (1 = low crime) | ready |
| `walk_score` | 0 to 1 (normalized from `NatWalkInd`) | ready |
| `lighting_score` | 0 to 1 | TODO, depends on Max |
| `bike_buffer_flag` or `bike_buffer_score` | 0 or 1 | TODO, depends on Max |
| `road_class_score` | 0 to 1 (from OSM `highway`) | optional |
=======
Each edge will eventually carry these features (see `03_feature_engineering.md` for how they are computed):

1. `crime_score_day`, `crime_score_night` (0 to 1, 1 means low crime)
2. `walk_score` (0 to 1, normalized from `NatWalkInd`)
3. `lighting_score` (0 to 1, TODO once Max finishes street lights cleaning)
4. `bike_buffer_flag` or `bike_buffer_score` (0 or 1, TODO once Max finishes bike lanes cleaning)
5. `road_class_score` (optional, derived from OSM `highway` tag)
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

## Draft scoring formula

Define `safety_score` first. Use plain words for now and replace with real weights once Matthew picks them.

```
<<<<<<< HEAD
safety_score = w_crime * crime_component
             + w_walk  * walk_score
             + w_light * lighting_score
             + w_bike  * bike_buffer_score
             + w_road  * road_class_score
=======
safety_score = weighted average of normalized feature scores
            = w_crime * crime_component
            + w_walk  * walk_score
            + w_light * lighting_score
            + w_bike  * bike_buffer_score
            + w_road  * road_class_score
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

with w_crime + w_walk + w_light + w_bike + w_road = 1
and  crime_component = crime_score_day if daytime else crime_score_night
```

<<<<<<< HEAD
**TODOs for Matthew:**

1. Pick the 5 weights. Document the reasoning.
2. Decide whether the user picks a time of day or whether the app picks it from the system clock.
3. Decide what default we use if a feature is missing on an edge (drop the term, or fill with neutral 0.5).

## Route cost formula
=======
Open TODOs for Matthew:

1. Pick the five weights. Document the reasoning.
2. Decide whether the user picks a time of day or whether the app picks it from the system clock.
3. Decide what default we use if a feature is missing on an edge (for example if `lighting_score` is not yet computed, do we drop the term or fill it with a neutral 0.5).
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

Once `safety_score` is known per edge, convert it to a route cost:

```
route_cost = length * (1 + 4 * (1 - safety_score))
```

<<<<<<< HEAD
**Plain English:**

| Edge quality | `safety_score` | `route_cost` |
| - | - | - |
| Perfect | 1.0 | 1 × length |
| Average | 0.5 | 3 × length |
| Worst | 0.0 | 5 × length |

The factor 4 is a knob. Tune it later if the safest route is always too long or always identical to the fastest.

## Route types

We run shortest path 3 times using [`networkx.shortest_path`](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.generic.shortest_path.html), each with a different edge weight.

| Route | Edge weight | Optimizes for |
| - | - | - |
| Fastest | `length` | shortest physical walk |
| Safest | `route_cost` | safety adjusted cost |
| Balanced | `balanced_cost` | a blend |
=======
Plain English:

1. A perfect edge (`safety_score = 1`) costs exactly its physical length.
2. A worst edge (`safety_score = 0`) costs 5 times its length.
3. The routing algorithm prefers shorter cost, so it avoids low score edges unless the detour is too long.

The factor 4 is a knob. We can tune it later if the safest route is always too long or always identical to the fastest route.

## Route types

We run shortest path three times, each with a different edge weight, using `networkx.shortest_path(G, orig, dest, weight=...)`.

| Route | Edge weight used | What it optimizes |
| --- | --- | --- |
| Fastest | `length` | shortest physical walk, ignores safety |
| Safest | `route_cost` | minimizes the safety adjusted cost |
| Balanced | `balanced_cost` | a blend, see below |

Balanced cost is a simple mix:
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb

```
balanced_cost = alpha * length + (1 - alpha) * route_cost
```

<<<<<<< HEAD
`alpha` is a knob between 0 and 1. **AJ owns** picking and testing alpha. Start at `alpha = 0.5`.

## What the app should eventually show

For each route:

1. Map of the route.
2. Total distance and rough walking time.
3. Overall safety score (length weighted average of per edge `safety_score`).
4. **One sentence explanation** ("avoids 3 high crime blocks, prefers well lit streets").
5. Optional per segment breakdown: street name, lighting, crime count, walkability per block.

The Streamlit UI itself is not in scope yet. We plan it in Week 6 once scoring produces stable outputs on a test neighborhood.

## Limitations

Be honest about these in the app and in any presentation.

| Limitation | Why it matters |
| - | - |
| SDPD calls ≠ all crime | some calls are nothing, some real incidents are never reported |
| Underreporting bias | quiet looking neighborhoods may just have fewer 911 calls |
| No real time data | crime is historical, lighting is the city DB, bike lanes are static |
| Walkability is a proxy | `NatWalkInd` captures street network and land use, not human comfort |
| Safety score is a model | the app should say "looks safer in our data," not "is safe" |

## How AJ should evaluate weight choices

Minimum experiment design AJ can run as soon as the scoring formula returns numbers.

1. Pick 5 to 10 start/end pairs in different parts of the city. Mix downtown, near campus, residential, less safe areas.
2. For each pair, compute fastest, safest, balanced under at least 3 weight settings.
3. Record per route: total distance, time estimate, length weighted `safety_score`, streets used.
4. Look at results and answer: do safer routes feel sensible to a person who knows the area? Where do they go wrong?
5. Write findings into [`status.md`](status.md) so Matthew can adjust weights.

This is not a formal evaluation. It is the minimum check that the scoring is doing something a person agrees with.

## Connecting back to the user question

The technical pieces above all exist to answer questions a real user might ask.

| User question | Where the answer lives |
| - | - |
| "Will this route feel isolated?" | `walk_score` (low score → isolated) |
| "Is this route worth the extra walking time?" | `route_cost` exposes the tradeoff explicitly |
| "Why is this route recommended?" | per segment breakdown returned with the route |
| "Is this based on incidents, walkability, or what?" | crime and walkability stay separate inputs; explanation surfaces both |
| "What does the app not know?" | the Limitations table above |
=======
`alpha` is a single knob between 0 and 1. AJ owns picking and testing alpha values. A useful starting point is `alpha = 0.5`.

## What the app should eventually show

Per route:

1. Map of the route.
2. Total distance and rough walking time.
3. Overall safety score (an average of the per edge `safety_score` weighted by edge length).
4. One sentence explanation of why this route was chosen ("avoids 3 high crime blocks, prefers well lit streets").
5. Optional per segment breakdown so the user can see street name, lighting status, crime count, walkability per block.

The app design itself is not in scope yet. We will plan the Streamlit UI once the scoring layer produces stable outputs on a test neighborhood.

## Limitations

Be honest about these in the app and in any presentation:

1. SDPD calls for service are not the same as all crime. Some calls turn out to be nothing, and some real incidents are never reported.
2. Underreporting bias. Quiet looking neighborhoods may just have fewer 911 calls, not fewer incidents.
3. No real time data. Crime is historical, lighting is the city's database (not "is this light on right now"), bike lanes are static.
4. Walkability is a 1 to 20 index that captures street network and land use, not human comfort. It is a proxy.
5. Safety score is a model. It is wrong sometimes. The app should phrase it as "this route looks safer in our data" rather than "this route is safe."

## How AJ should evaluate weight choices

A short experiment design AJ can run as soon as the scoring formula returns numbers:

1. Pick 5 to 10 start and end pairs in different parts of the city. Try mixed neighborhoods (downtown, near campus, residential, less safe areas).
2. For each pair, compute fastest, safest, balanced under at least 3 weight settings.
3. Record: total distance, total time estimate, total `safety_score` (length weighted), and the streets used.
4. Look at the results and answer: do the safer routes feel sensible to a human who knows the area? Where do they go wrong?
5. Write findings into `docs/status.md` so Matthew can adjust weights.

This is not a formal evaluation. It is the minimum check that the scoring is doing something a person agrees with.
>>>>>>> 86276a86603548c046675d2af3321e97959e84cb
