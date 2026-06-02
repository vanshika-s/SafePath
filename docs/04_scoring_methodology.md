# 04. Scoring methodology

> **TL;DR.** SafePath gives every street segment a `safety_score` (0 to 1, 1 is best), turns that into a `route_cost` the routing algorithm minimizes, then runs Dijkstra 3 times: fastest, safest, balanced. Scores displayed in the UI are length-weighted so longer segments carry more weight than short ones.

> **Status: implemented and deployed.** Scoring and routing are live at [safepaths.onrender.com](https://safepaths.onrender.com). The scoring formula was built in `safety-score-edge.ipynb` and the pre-computed weight arrays are loaded at runtime by `src/api/graph_store.py`.

## Where to find related docs

| Topic | Doc |
| - | - |
| Where the cleaning happens | [`02_data_cleaning.md`](02_data_cleaning.md) |
| How features get attached to OSM edges | [`03_feature_engineering.md`](03_feature_engineering.md) |
| Live status and decisions | [`status.md`](status.md) |

## Core idea

SafePath scores each street segment first. A route is evaluated by summing the costs of all segments along it.

| Layer | What it is | Range |
| - | - | - |
| `safety_score` per edge | weighted average of normalized features | 0 to 1 (1 = safest) |
| `safety_cost` per edge | length-scaled cost the router minimizes | meters, amplified by danger |

Lower `safety_cost` wins.

## Pipeline

```
user enters address
  → geocode into coordinates                   (src/api/geocoder.py)
  → snap to nearest OSM walking node           (RouteGraph.nearest_node)
  → read pre-computed safety / balanced costs  (RouteGraph._csr_safe / _csr_balanced)
  → run Dijkstra 3 times                       (fastest, safest, balanced)
  → return route polylines + per-segment scores + turn steps
```

Feature scores were pre-computed in `safety-score-edge.ipynb` and saved as numpy arrays. No scoring math runs at request time — the router reads the arrays directly.

## Inputs to the score

Each edge carries these features (see [`03_feature_engineering.md`](03_feature_engineering.md)):

| Feature | Range | Weights (day / night) |
| - | - | - |
| `crime_score_day` / `crime_score_night` | 0–1 (1 = low crime) | 0.50 day / 0.45 night |
| `walk_score` | 0–1 (from EPA `NatWalkInd`) | 0.25 / 0.25 |
| `infrastructure` (lighting + infra) | 0–1 | 0.25 day / 0.30 night |

Night weights shift more toward crime and infrastructure (lighting) because those matter more after dark. Day/night is determined by real San Diego sunrise/sunset via `src/api/day_night.py`.

## Scoring formula

```
safety_score = W_crime × crime_score  +  W_walk × walk_score  +  W_infra × infrastructure
```

Day weights: `W_crime=0.50, W_walk=0.25, W_infra=0.25`
Night weights: `W_crime=0.45, W_walk=0.25, W_infra=0.30`

Six versions of every weight array are pre-computed and saved: `{short, medium, long} × {day, night}`. Route length is classified at query time (short < 500 m, medium ≤ 2000 m, long > 2000 m) and the matching array is selected.

## Route cost formula

```
safety_cost = length × (1 + 4 × (1 − safety_score))
```

Plain English — the router treats dangerous streets as physically longer:

| `safety_score` | `safety_cost` per meter |
| - | - |
| 1.0 (perfectly safe) | 1× length — no penalty |
| 0.75 | 2× length |
| 0.5 (average) | 3× length |
| 0.25 | 4× length |
| 0.0 (worst) | 5× length |

```
balanced_cost = length × (1 + 2 × (1 − safety_score))
```

Balanced uses a multiplier of 2 instead of 4 — half the safety pressure, so it stays closer to the direct path.

## Route types

| Route | Edge weight | Optimizes for |
| - | - | - |
| Fastest | `length` | shortest physical walk |
| Safest | `safety_cost` (multiplier 4) | maximum safety |
| Balanced | `balanced_cost` (multiplier 2) | blend of speed and safety |

## How scores are displayed in the UI

All percentages shown in the app are **length-weighted** — longer edges count proportionally more than short ones. This means a 10 m dangerous alley doesn't drag down the score as much as a 500 m safe boulevard raises it.

**Overall safety** is back-calculated from `safety_cost`:

```
displayed_score = 1 − (total_safety_cost − total_length) / (4 × total_length)
```

This is mathematically equivalent to a length-weighted average of per-edge `safety_score` and is the same formula used in the route cards, the compare table, and the API response.

**Crime, infrastructure, and walk scores** use direct length-weighted averages:

```
displayed_crime = Σ(crime_score × edge_length) / total_length
```

Both the Streamlit app and the web app use identical formulas — the API computes them and the Streamlit computes them locally from `edge_scores`.

## What the app shows

For each route:

1. Map polyline with animated drawing on selection.
2. Total distance (miles) and estimated walk time (minutes).
3. Overall safety percentage (length-weighted, derived from `safety_cost`).
4. Score breakdown: crime safety, infrastructure, walkability — all length-weighted.
5. Turn-by-turn steps with direction icons.
6. Crime heat map — density-filtered (min 10 incidents per ~100 m cell), p95 intensity scaling.

## Limitations

| Limitation | Why it matters |
| - | - |
| SDPD calls ≠ all crime | some calls are nothing; some real incidents are never reported |
| Underreporting bias | quiet-looking neighborhoods may just have fewer 911 calls |
| No real-time data | crime is historical; lighting is the city DB snapshot, not "is this light on right now" |
| Walkability is a proxy | `NatWalkInd` captures street network and land use, not human comfort |
| Safety score is a model | the app should say "looks safer in our data," not "is safe" |

## Connecting back to the user question

| User question | Where the answer lives |
| - | - |
| "Will this route feel isolated?" | `walk_score` (low score → isolated) |
| "Is this route worth the extra walking time?" | `safety_cost` exposes the tradeoff explicitly |
| "Why is this route recommended?" | per-segment breakdown returned with every route |
| "Is this based on incidents, walkability, or what?" | crime, walkability, and infrastructure stay separate inputs and are shown separately |
| "What does the app not know?" | the Limitations table above |
