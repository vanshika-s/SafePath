# 04. Scoring methodology

> **TL;DR.** SafePath gives every street segment a `safety_score` (0 to 1, 1 is best), turns that into a `route_cost` the routing algorithm minimizes, then runs shortest path 3 times: fastest, safest, balanced. This doc is future facing. TODOs mark things still being decided.

> **Status: implemented and deployed.** Scoring and routing are live at [safepaths.onrender.com](https://safepaths.onrender.com). The scoring formula was built in `safety-score-edge.ipynb` and the pre-computed weight arrays are loaded at runtime by `src/api/graph_store.py`. This document describes what was built and the reasoning behind the key parameters.

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

## Pipeline

```
user enters address
  → geocode address into coordinates          (src/api/geocoder.py)
  → snap coordinates to OSM walking network   (RouteGraph.nearest_node)
  → read pre-computed safety / balanced costs (RouteGraph._csr_safe / _csr_balanced)
  → run Dijkstra 3 times                      (fastest, safest, balanced)
  → return route polylines + per-segment scores + turn steps
```

Feature scores (crime, walk, lighting, infrastructure) were pre-computed in `safety-score-edge.ipynb` and saved as numpy arrays. At runtime no scoring math runs — the router reads the arrays directly.

## Inputs to the score

Each edge carries these features (built in `safety-score-edge.ipynb`, see [`03_feature_engineering.md`](03_feature_engineering.md)):

| Feature | Range | Status |
| - | - | - |
| `crime_score_day`, `crime_score_night` | 0 to 1 (1 = low crime) | **In production** |
| `walk_score` | 0 to 1 (normalized from `NatWalkInd`) | **In production** |
| `infrastructure` (lighting + bike infra) | 0 to 1 | **In production** |
| `bike_buffer_score` | 0 to 1 | Not yet added |
| `road_class_score` | 0 to 1 (from OSM `highway`) | Not yet added |

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

> **`daytime` is currently NOT IMPLEMENTED in code.** The proposed cutoff (per v0 default, see Provenance banner above) is `daytime ∈ [06:00, 18:00)` in **local San Diego time (America/Los_Angeles)**, with `nighttime` covering the complement `[00:00, 06:00) ∪ [18:00, 24:00)`. When scoring code is written, expose this as a single named constant (e.g. `DAYTIME_HOURS = range(6, 18)`) so the team can tune one place. The "user picks vs system clock" question is still open — see [`status.md`](status.md) Open Question #1.

**TODOs for Matthew:**

1. Pick the 5 weights. Document the reasoning.
2. Decide whether the user picks a time of day or whether the app picks it from the system clock.
3. Decide what default we use if a feature is missing on an edge (drop the term, or fill with neutral 0.5). Note: lighting already has a built-in fallback for UCSD-interior edges (`L4 == ucsd_uncovered` → `lighting_score = 0.5`).

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

We run Dijkstra 3 times (in `src/api/graph_store.py`), each with a different CSR weight matrix:

| Route | Edge weight | Optimizes for |
| - | - | - |
| Fastest | `length` | shortest physical walk |
| Safest | `route_cost` | safety adjusted cost |
| Balanced | `balanced_cost` | a blend |

```
balanced_cost = alpha * length + (1 - alpha) * route_cost
```

`alpha` is a knob between 0 and 1. **Ajay owns** picking and testing alpha. Start at `alpha = 0.5`.

## What the app shows

For each route the API returns:

1. Map polyline (Leaflet, rendered in `landing/routes.js`).
2. Total distance (miles) and estimated walk time (minutes).
3. Per-segment breakdown: street name, safety score, crime score, walk score, infrastructure score.
4. Turn-by-turn steps with direction icons.
5. Crime heat map clipped to a bounding box around the routes.

## Limitations

Be honest about these in the app and in any presentation.

| Limitation | Why it matters |
| - | - |
| SDPD calls ≠ all crime | some calls are nothing, some real incidents are never reported |
| Underreporting bias | quiet looking neighborhoods may just have fewer 911 calls |
| No real time data | crime is historical, lighting is the city DB (not "is this light on right now"), bike lanes are static |
| Walkability is a proxy | `NatWalkInd` captures street network and land use, not human comfort |
| Lighting coverage is uneven on UCSD interior | 228 lights in the campus interior bbox, but coverage is uneven, so L4 falls back to neutral 0.5 there |
| Safety score is a model | the app should say "looks safer in our data," not "is safe" |

## Connecting back to the user question

The technical pieces above all exist to answer questions a real user might ask.

| User question | Where the answer lives |
| - | - |
| "Will this route feel isolated?" | `walk_score` (low score → isolated) |
| "Is this route worth the extra walking time?" | `route_cost` exposes the tradeoff explicitly |
| "Why is this route recommended?" | per segment breakdown returned with the route |
| "Is this based on incidents, walkability, or what?" | crime, walkability, and lighting stay separate inputs; explanation surfaces all three |
| "What does the app not know?" | the Limitations table above |
