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

Lower route cost wins.

## Planned pipeline

```
user enters address
  → geocode address into coordinates
  → snap coordinates to OpenStreetMap walking network
  → assign crime + walkability features to each street edge
  → calculate safety score per edge
  → convert safety score into route cost
  → run shortest path 3 times (fastest, safest, balanced)
  → return route polylines + per segment explanation to the app
```

## Inputs to the score

Each edge will eventually carry these features (built in [`03_feature_engineering.md`](03_feature_engineering.md)):

| Feature | Range | Status |
| - | - | - |
| `crime_score_day`, `crime_score_night` | 0 to 1 (1 = low crime) | ready |
| `walk_score` | 0 to 1 (normalized from `NatWalkInd`) | ready |
| `lighting_score` | 0 to 1 | TODO, depends on Max |
| `bike_buffer_flag` or `bike_buffer_score` | 0 or 1 | TODO, depends on Max |
| `road_class_score` | 0 to 1 (from OSM `highway`) | optional |

## Draft scoring formula

Define `safety_score` first. Use plain words for now and replace with real weights once Matthew picks them.

```
safety_score = w_crime * crime_component
             + w_walk  * walk_score
             + w_light * lighting_score
             + w_bike  * bike_buffer_score
             + w_road  * road_class_score

with w_crime + w_walk + w_light + w_bike + w_road = 1
and  crime_component = crime_score_day if daytime else crime_score_night
```

**TODOs for Matthew:**

1. Pick the 5 weights. Document the reasoning.
2. Decide whether the user picks a time of day or whether the app picks it from the system clock.
3. Decide what default we use if a feature is missing on an edge (drop the term, or fill with neutral 0.5).

## Route cost formula

Once `safety_score` is known per edge, convert it to a route cost:

```
route_cost = length * (1 + 4 * (1 - safety_score))
```

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

```
balanced_cost = alpha * length + (1 - alpha) * route_cost
```

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
