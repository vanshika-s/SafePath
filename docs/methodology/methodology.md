# SafePath Methodology

## Purpose of this document

This document explains the planned scoring and routing methodology for SafePath.

It focuses on the question:

```text
How should SafePath decide which walking route is safer or more comfortable?
```

This file is future-facing. The cleaned crime and walkability datasets are ready, and the next step is to turn those processed files into edge-level scores, route costs, and user-facing route explanations.

Use this file for scoring logic, assumptions, and limitations.

Use other files for other purposes:

- `README.md`: project overview, setup, and data download
- `docs/status/`: weekly progress and blockers
- `docs/pipeline.md`: beginner-friendly backend-to-frontend pipeline
- `docs/preprocessing.md`: how processed data files were created and how to validate them

---

## Core idea

SafePath does not score an entire route all at once.

Instead, SafePath scores each **street edge** first. A street edge is one walkable street segment between two graph nodes, usually intersections or path endpoints.

A route is then evaluated by adding up the costs of the edges along that path.

```text
street edge features → edge safety score → edge route cost → full route cost
```

This design matters because routing algorithms, such as Dijkstra's algorithm in `networkx`, choose routes by comparing edge weights.

---

## Unit of analysis: street edge

The central object in SafePath is the **street edge**.

Each edge should eventually have:

| Attribute | Meaning |
|---|---|
| `length` | physical length of the street segment |
| `crime_count` | number of relevant crime incidents near the edge |
| `walk_score` | walkability score inherited from the block group |
| `safety_score` | normalized combined safety score |
| `safety_cost` | distance adjusted by safety |
| `balanced_cost` | optional blend of distance and safety |

The main methodological choice is how to turn several imperfect safety signals into one route cost.

---

## Inputs used for scoring

### 1. Crime signal

Source file:

```text
data/processed/crime_final_gdf.gpkg
```

This file contains geocoded crime or incident points from SDPD Calls for Service after filtering.

Planned use:

- Count nearby incidents within a buffer around each street edge.
- Optionally weight incidents by severity.
- Optionally split scores by time of day if the app asks when the user is walking.

Interpretation:

A higher nearby crime count means the edge should be treated as less safe.

Important caution:

SDPD Calls for Service are not the same as all crime that happened. Some incidents are underreported, and some calls may not represent confirmed crime.

---

### 2. Walkability signal

Source file:

```text
data/processed/walkability_final_gdf.gpkg
```

This file contains Census block group polygons with EPA `NatWalkInd` scores.

Planned use:

- Find the midpoint of each street edge.
- Check which block group polygon contains that midpoint.
- Assign that block group's `NatWalkInd` score to the edge.

Interpretation:

Higher walkability suggests the area may be more pedestrian-friendly, connected, and active.

Important caution:

Walkability is a proxy for comfort. It does not directly measure whether a person feels safe.

---

### 3. OpenStreetMap signal

Source:

```text
OpenStreetMap walking network from osmnx
```

Potential edge attributes:

- `length`
- `highway`
- `name`
- `lit`
- `sidewalk`

Planned use:

- `length` is always needed for routing.
- Other OSM attributes may be used if coverage is good enough.

Important caution:

Some OSM attributes are sparse or inconsistent. For example, many streets may have missing `lit` values.

---

### 4. Future comfort signals

Future datasets may be added if the team decides they are useful and trustworthy.

Examples:

- streetlight point data
- real-time construction or closure data
- user feedback
- campus-specific safety infrastructure

These should only be added after the team documents:

1. what the dataset measures
2. how it maps to edges
3. how missing values are handled
4. whether it actually improves the recommendation

---

## Edge-level feature construction

### Crime feature

Planned approach:

```text
For each edge:
  draw a 50 meter buffer around the edge
  count crime points inside the buffer
  assign the count to the edge
```

Possible feature names:

```text
crime_count
crime_score
crime_score_day
crime_score_night
```

Basic version:

```text
crime_count = number of relevant incidents within 50 meters
```

More advanced version:

```text
crime_risk = weighted count using call type severity and priority level
```

Decision still needed:

```text
Should SafePath use raw counts, severity-weighted counts, or time-specific counts?
```

---

### Walkability feature

Planned approach:

```text
For each edge:
  find the midpoint
  spatially join the midpoint to a walkability polygon
  assign the polygon's NatWalkInd value to the edge
```

Possible feature names:

```text
walk_score
walkability_score
```

Basic version:

```text
walk_score = NatWalkInd for the block group containing the edge midpoint
```

Decision still needed:

```text
Should NatWalkInd be used directly, or should it be normalized against San Diego only?
```

---

### Missing values

The scoring logic must handle missing values clearly.

Possible rules:

| Missing input | Possible handling |
|---|---|
| missing crime count | treat as 0 only if spatial join is valid |
| missing walkability score | assign neutral default or nearest polygon |
| missing OSM lighting | treat as unknown, not automatically dark |
| missing sidewalk tag | treat as unknown unless coverage is reliable |

Important principle:

```text
Unknown should not always mean unsafe, but it also should not always mean safe.
```

---

## Draft safety score

Each edge receives a normalized safety score from 0 to 1.

```text
1 = safest or most comfortable
0 = least safe or least comfortable
```

A simple draft structure:

```text
safety_score = weighted average of normalized feature scores
```

Example only, not final:

```text
safety_score =
  w_crime × crime_score
+ w_walkability × walkability_score
+ w_lighting × lighting_score
+ w_sidewalk × sidewalk_score
```

Where the weights add up to 1.

The team still needs to decide the actual weights.

---

## Normalizing feature scores

Because the inputs use different scales, they need to be converted to comparable 0 to 1 scores.

### Crime

Raw crime counts are "higher is worse," so the normalized score should reverse the direction.

Example idea:

```text
crime_score = 1 − normalized_crime_count
```

Meaning:

```text
higher crime count → lower crime_score
```

### Walkability

EPA `NatWalkInd` ranges from 1 to 20, where higher generally means more walkable.

Example idea:

```text
walkability_score = (NatWalkInd − 1) / 19
```

Meaning:

```text
higher NatWalkInd → higher walkability_score
```

### Lighting and sidewalks

If OSM lighting or sidewalk data is used, it should be encoded carefully.

Example idea:

| Raw value | Possible score |
|---|---:|
| `lit = yes` | 1.0 |
| `lit = no` | 0.0 |
| `lit = unknown` | 0.5 |

Do not use these values as final without checking data coverage.

---

## Route cost formula

After calculating `safety_score`, convert it into a route cost.

Draft formula:

```text
safety_cost = length × (1 + 4 × (1 − safety_score))
```

Plain English:

- If an edge is very safe, its cost is close to its real length.
- If an edge is very unsafe, its cost can become up to five times its length.
- This makes the routing algorithm avoid unsafe edges unless the detour is too large.

Example:

| Edge length | Safety score | Safety cost |
|---:|---:|---:|
| 100 m | 1.0 | 100 m |
| 100 m | 0.5 | 300 m |
| 100 m | 0.0 | 500 m |

---

## Route modes

SafePath should eventually return three route options.

| Route mode | Edge weight | Meaning |
|---|---|---|
| Fastest | `length` | shortest walking route |
| Safest | `safety_cost` | route that avoids risky edges most strongly |
| Balanced | `balanced_cost` | tradeoff between distance and safety |

A possible balanced formula:

```text
balanced_cost = α × length + (1 − α) × safety_cost
```

Where:

```text
α closer to 1 = more distance-focused
α closer to 0 = more safety-focused
```

Decision still needed:

```text
What alpha value should SafePath use for the balanced route?
```

---

## User-facing explanation logic

SafePath should not only show a route. It should explain why that route was recommended.

Possible explanation outputs:

- total distance
- estimated walking time
- route safety score
- number of high-risk segments avoided
- route tradeoff compared with fastest route
- per-segment breakdown

Example plain-language explanation:

```text
The safest route is 7 minutes longer than the fastest route, but it avoids several segments with higher nearby incident counts and passes through more walkable block groups.
```

Example per-segment table:

| Street segment | Nearby crime count | Walkability score | Safety interpretation |
|---|---:|---:|---|
| College Ave | 3 | 14.2 | moderate |
| El Cajon Blvd | 8 | 10.1 | lower |
| University Ave | 1 | 16.5 | stronger |

The exact explanation design can evolve, but the key goal is:

```text
The user should understand what tradeoff the route is making.
```

---

## Methodological limitations

### Crime data is incomplete

SDPD Calls for Service do not represent every unsafe event. Some incidents are never reported.

### Calls for service are not the same as confirmed crime

Even with filtering, a call record is not always the same as a verified criminal event.

### Walkability is a proxy

`NatWalkInd` measures built environment factors such as connectivity and land use mix. It does not directly measure perceived safety.

### Edge-level scoring can over-simplify context

A route may feel unsafe for reasons not captured by crime count or walkability, such as visibility, harassment, crowding, or personal familiarity.

### Historical data is not real-time

SafePath does not currently include live traffic, construction, transit delays, police alerts, or temporary closures.

### A safety score is not a guarantee

SafePath can suggest routes based on available data, but it cannot guarantee that a route is safe.

---

## Open methodological decisions

The team still needs to decide:

1. What buffer distance should be used for nearby crime?
2. Should crime be severity-weighted?
3. Should the app ask for time of day?
4. Should walkability be normalized nationally or within San Diego?
5. Which OSM attributes are reliable enough to include?
6. What weights should be used in the safety score?
7. What alpha value should define the balanced route?
8. How should route explanations be shown to users?
