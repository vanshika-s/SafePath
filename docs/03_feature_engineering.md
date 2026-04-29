# Feature engineering

How cleaned datasets become features attached to each street segment in the OSM walking network.

This is the bridge between data cleaning and scoring. Owner this week: Ruan.

## The mental model

Every dataset gets reduced to one or two numbers per street edge. The scoring step (next doc) only looks at those numbers, not the raw data.

```
cleaned dataset  →  feature attached to each OSM edge  →  used by scoring
```

Example:

```
crime_final_gdf.gpkg
  → for each edge, count weighted crimes within 50m
  → store as edge["crime_score"]
  → scoring uses edge["crime_score"]
```

## The OSM walking network

We download the San Diego walking network with `osmnx`:

```python
import osmnx as ox
G = ox.graph_from_place("San Diego, CA", network_type="walk")
ox.save_graphml(G, "san_diego.graphml")  # cache it, do not redownload
```

Each edge already has these attributes from OSM:

1. `length` (meters)
2. `name` (street name, sometimes missing)
3. `highway` (street class)
4. `lit` (sometimes "yes", often missing)
5. `sidewalk` (sometimes filled, often missing)

Anything we add ourselves goes on top of those.

## Planned features

| Feature | Source dataset | What it captures | Status |
| --- | --- | --- | --- |
| `crime_score_day` and `crime_score_night` | `crime_final_gdf.gpkg` | weighted crimes within 50 m, split by hour of day | ready to compute |
| `walk_score` | `walkability_final_gdf.gpkg` | block group walkability (`NatWalkInd`, 1 to 20) | ready to compute |
| `lighting_score` | street lights (TBD) | density of working lights along the segment | TODO, depends on Max |
| `bike_buffer_flag` | bike lanes (TBD) | does the edge run alongside a buffered bike or scooter lane | TODO, depends on Max |
| `road_class_score` | OSM `highway` tag | residential and tertiary streets feel calmer than primary roads | optional, easy win |

## How each feature is built

### Crime score per edge

Idea: count crime points near the edge, weighted by severity and priority, split by time of day.

Recipe:

1. Reproject the OSM edges and the crime points to `EPSG:3857` (meters).
2. Buffer each edge by 50 meters.
3. Spatial join the buffered edges with the crime points.
4. Group by edge, sum the weighted crimes. Use `HOUR` to produce a day score and a night score separately.
5. Normalize across all edges so the score sits in 0 to 1.

```python
edges_buf = edges.copy()
edges_buf["geometry"] = edges.geometry.buffer(50)  # meters, EPSG:3857
joined = gpd.sjoin(edges_buf, crimes_gdf, how="left", predicate="contains")
edge_scores = joined.groupby(level=0).agg(
    n_day=("HOUR", lambda h: (h.between(6, 18)).sum()),
    n_night=("HOUR", lambda h: (~h.between(6, 18)).sum()),
)
```

Open question: should severity weights live in this doc or in `04_scoring_methodology.md`. Right now, lean toward putting weights in scoring so feature engineering stays "data math" only.

### Walkability score per edge

Idea: each edge inherits the walkability score of the block group its midpoint sits in.

Recipe:

1. Reproject edges and walkability polygons to the same CRS.
2. Compute the midpoint of each edge with `interpolate(0.5, normalized=True)`.
3. Spatial join the midpoints with the polygons (`predicate="within"`).
4. Copy `NatWalkInd` onto the edge as `walk_score`.
5. Fill missing scores with a neutral default (for example 5.0) and log how many edges fell back.

We use the midpoint, not the whole line, because long edges can cross two block groups. A single point lands in exactly one polygon, which keeps the score unambiguous.

### Lighting score (future, depends on Max)

Idea: for each edge, count working street lights within a small buffer. More lights along a segment means a higher lighting score.

Open questions Max needs to answer first:

1. Does the city dataset distinguish working from broken or removed lights?
2. Do all lights matter equally, or should we weight by wattage or fixture type?

Once those answers are known, the recipe will be very similar to the crime score: buffer the edge, join with point geometry, count, normalize.

### Buffered bike or scooter lane flag (future, depends on Max)

Idea: a binary or graded value per edge for whether a buffered bike or scooter lane runs along it. Buffered lanes correlate with calmer traffic, which usually feels more comfortable to a pedestrian.

Recipe sketch:

1. Reproject the bike lanes and the OSM edges to the same CRS.
2. For each edge, ask whether any bike lane segment runs nearby and roughly parallel.
3. Store as `bike_buffer_flag` (0 or 1) or `bike_buffer_score` (0 to 1) depending on what is easier.

## Things to be careful about

1. CRS mismatch. Always reproject everything to `EPSG:3857` before buffering or measuring distance.
2. Direction of edges. OSM walking edges are usually two way, but check if any one way edges leak in. A pedestrian usually does not care.
3. Multi edges between the same two nodes. OSMnx returns a multigraph. Loop with `G.edges(keys=True, data=True)` so you do not collide on duplicate edges.
4. Sparse edges. Many OSM edges will have no nearby crime, no nearby light, no NatWalkInd polygon. Decide a fallback for each missing feature and document it here.

## Where features are stored

For now, write features back onto the OSMnx graph in memory:

```python
G[u][v][k]["crime_score"] = ...
G[u][v][k]["walk_score"] = ...
```

We are not pickling enriched graphs to disk yet. That is fine for the prototype. If routing gets slow because feature computation reruns every time, we will save the enriched graph as a `.graphml` file and document it here.

## What to do this week (Ruan)

1. Get crime and walkability features attached to a small slice of the OSM graph (one neighborhood is plenty).
2. Print the distributions: are crime scores concentrated on a few edges, or spread out? Are walkability scores reasonable?
3. Pick two test routes by hand (start address, end address) and confirm the per edge features look sane along them. Write findings into `docs/status.md`.
