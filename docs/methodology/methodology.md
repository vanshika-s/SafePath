# SafePath Methodology

This document describes the planned SafePath scoring and routing methodology. The cleaned crime and walkability datasets are ready. The next step is to assign scores to street segments, build routes, and connect the results to the app.

For project setup and data download instructions, use `README.md`. For weekly progress and next tasks, use `docs/status/`. For how the cleaned data files were created and how to validate them, use `docs/preprocessing.md`.

## Purpose of this document

This file explains the technical design behind SafePath's route recommendation pipeline. It focuses on the planned logic for turning processed data into scored street segments and route recommendations.

It is not meant to be:

- a setup guide
- a weekly status update
- a raw data download guide
- a full GeoPandas tutorial

## Core idea

SafePath does not score an entire route all at once. It scores each street segment first.

A street segment is an edge in the OpenStreetMap walking network. Each edge receives feature values such as nearby crime risk and walkability. After every edge has a score, a route can be evaluated by adding up the edge costs along the path.

In simple terms:

```text
street edge features → edge safety score → edge route cost → full route recommendation
```

This structure matters because route algorithms such as Dijkstra need one cost value per edge. SafePath's job is to convert multiple safety and comfort signals into that one edge cost.

## Planned pipeline

```text
user enters start and destination
  ↓
geocode addresses into coordinates
  ↓
snap coordinates to nearest OpenStreetMap walking nodes
  ↓
load the San Diego walking network
  ↓
assign crime and walkability features to each street edge
  ↓
calculate an edge-level safety score
  ↓
convert safety score into route cost
  ↓
generate fastest, safest, and balanced routes
  ↓
return route geometry and plain-language explanation to the app
```

## Unit of analysis: street edges

The main object in the pipeline is the street edge.

- A node is an intersection, dead end, or connection point in the walking network.
- An edge is the walkable street segment between two nodes.
- A route is a sequence of edges.

Because a route is made of edges, SafePath should attach safety and comfort information to each edge before routing.

## Inputs used by the scoring pipeline

### `crime_final_gdf.gpkg`

This processed file contains geocoded crime-related points from SDPD Calls for Service. Each row represents an incident that passed the cleaning and filtering process.

Planned use in scoring:

- count nearby incidents around each street edge
- optionally weight incidents by severity or priority
- optionally separate day and night risk if the app asks for time of day later

### `walkability_final_gdf.gpkg`

This processed file contains San Diego Census block group polygons with EPA `NatWalkInd` scores.

Planned use in scoring:

- assign each street edge a walkability score based on the block group it falls inside
- use walkability as a comfort and pedestrian environment signal
- keep this separate from crime risk so the explanation can say whether a route is recommended because of lower incidents, better walkability, or both

### OpenStreetMap walking network

SafePath will use OSMnx to load the San Diego walking network. The network provides nodes, edges, street lengths, and available OSM attributes.

Planned use in scoring:

- route through real walkable paths instead of straight lines
- use edge length as the base cost
- optionally use available OSM attributes such as road type, sidewalk, or lighting tags if they are reliable enough

## Edge-level feature construction

Each edge should receive a small set of interpretable features. The first version should stay simple enough for the team to validate.

### Crime feature

For each edge, draw a buffer around the street segment and count crime points inside the buffer.

Planned first version:

```text
crime_count = number of crime points within 50 meters of the edge
```

Possible later version:

```text
crime_risk = weighted count using call type severity, priority, and time of day
```

Important note: if a left spatial join is used, make sure unmatched edges count as zero incidents, not one missing row.

### Walkability feature

For each edge, find the midpoint of the street segment. Then assign the `NatWalkInd` score from the block group polygon containing that midpoint.

Planned first version:

```text
walkability_raw = NatWalkInd value for the edge midpoint's block group
```

Because `NatWalkInd` is on a 1 to 20 scale, it should be normalized before combining with other features.

### Optional comfort features

These can be added only after the first crime and walkability pipeline works.

Possible examples:

- lighting coverage
- sidewalk availability
- road type
- user-selected time of day
- user-selected preference for safety versus distance

These should not block the first scoring prototype.

## Draft scoring logic

The exact feature weights are not final yet. The first version should prioritize clarity and validation over complexity.

### Step 1: normalize each feature

Each feature should be converted to a 0 to 1 score where:

```text
1 = better / safer / more comfortable
0 = worse / less safe / less comfortable
```

Example directions:

| Feature | Raw meaning | Normalized direction |
|---|---|---|
| `crime_count` | More nearby incidents | Higher should become worse, so invert after normalization |
| `walkability_raw` | Higher `NatWalkInd` | Higher should stay better |
| `lighting_score` | Better lighting, if added | Higher should stay better |

### Step 2: combine normalized features

Use a weighted average of available features.

Draft placeholder:

```text
safety_score = weighted average of normalized feature scores
```

Example only, not final:

```text
safety_score = 0.60 × crime_score + 0.40 × walkability_score
```

The team still needs to decide the final weights. Until then, the code should make weights easy to change.

### Step 3: convert safety score into route cost

```text
route_cost = length × (1 + 4 × (1 − safety_score))
```

Plain-English meaning:

- A very safe edge has a cost close to its real walking length.
- A less safe edge becomes more expensive.
- A very unsafe edge can cost up to 5 times its length.
- This pushes the routing algorithm away from risky edges without completely banning them.

This is useful because the route algorithm still receives one number per edge.

## Route types

SafePath should eventually return three route options.

| Route type | Edge weight used | Meaning |
|---|---|---|
| Fastest | `length` | Shortest walking route, ignoring safety score |
| Safest | `route_cost` or `safety_cost` | Route that avoids high-cost edges, even if longer |
| Balanced | blend of `length` and `safety_cost` | Compromise between distance and safety |

Possible balanced formula:

```text
balanced_cost = α × normalized_length + (1 − α) × normalized_safety_cost
```

The team should choose `α` based on how much extra distance feels acceptable for a safer route.

## User-facing explanation

SafePath should not only return a route. It should explain why the route was recommended.

The app should eventually show:

- route map
- route type: fastest, safest, or balanced
- distance or estimated walking time
- overall route safety or comfort score
- short explanation of the main reason the route was chosen
- optional per-segment breakdown for crime and walkability

Example explanation:

> The safest route is longer than the fastest route, but it avoids several segments with higher nearby incident counts and stays mostly in more walkable block groups.

The explanation should stay plain-language. Users should not need to understand GeoPandas, OSMnx, or Dijkstra to understand the recommendation.

## Validation questions for scoring

Before treating the route output as trustworthy, the team should test a few routes manually.

Useful checks:

- Does the fastest route look like a normal shortest walking route?
- Does the safest route avoid edges with high nearby crime counts?
- Does the safest route become unreasonably long?
- Are low-crime but isolated areas being over-rewarded?
- Are high-walkability downtown areas being over-rewarded despite incident density?
- Do the route explanations match the actual edge features?

## Limitations

SafePath's score is a proxy, not a guarantee of personal safety.

Known limitations:

- SDPD Calls for Service are not the same as all crime that happened.
- Some incidents are never reported.
- Some calls may not represent confirmed danger.
- Historical incidents do not capture real-time conditions.
- Walkability is measured at the block group level, which may be too coarse for street-level comfort.
- The first version may not include time of day, lighting, construction, crowds, or user feedback.
- A route that scores safer in the model may still feel unsafe to a real user.

These limitations should be visible in the final project so the team does not overclaim what SafePath can do.

## What belongs somewhere else

To keep this document readable:

- raw data download steps belong in `docs/preprocessing.md`
- geocoding details belong in `docs/preprocessing.md`
- CRS and GeoPandas validation details belong in `docs/preprocessing.md`
- weekly progress belongs in `docs/status/`
- installation and data setup belong in `README.md`
