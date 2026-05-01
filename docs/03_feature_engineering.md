# 03. Feature engineering

> **TL;DR.** Each cleaned dataset becomes one or two numbers attached to each street edge in the OSM walking network. The scoring step only reads those numbers, never the raw data.

**This week's owner:** Ruan.

## The mental model

```
cleaned dataset  →  feature on each OSM edge  →  used by scoring
```

**Concrete example.**

```
crime_final_gdf.gpkg
  → for each edge, count weighted crimes within 50 m
  → store as edge["crime_score"]
  → scoring uses edge["crime_score"]
```

## The OSM walking network

We download the San Diego walking graph through [OSMnx](https://osmnx.readthedocs.io):

```python
import osmnx as ox
G = ox.graph_from_place("San Diego, CA", network_type="walk")
ox.save_graphml(G, "san_diego.graphml")  # cache it; do not redownload
```

Each edge already has these attributes from OSM:

| Attribute | What it is | How reliable |
| - | - | - |
| `length` | meters | always present |
| `name` | street name | sometimes missing |
| `highway` | street class (residential, primary, ...) | always present |
| `lit` | "yes" / "no" | often missing |
| `sidewalk` | sidewalk on which side | often missing |

Anything we add ourselves goes on top of those.

## Planned features

| Feature | Source dataset | What it captures | Status |
| - | - | - | - |
| `crime_score_day`, `crime_score_night` | `crime_final_gdf.gpkg` | weighted crimes within 50 m, split by hour | ready to compute |
| `walk_score` | `walkability_final_gdf.gpkg` | block group walkability (`NatWalkInd`, 1 to 20) | ready to compute |
| `lighting_score` | `data/processed/streetlights/streetlights_processed.geojson` | density of operational lights along the segment | source data ready; spec at [`docs/data/streetlights/FEATURE_CONTRACT.md`](data/streetlights/FEATURE_CONTRACT.md) |
| `bike_buffer_flag` | bike lanes (TBD) | does the edge run alongside a buffered bike or scooter lane | TODO, depends on Max |
| `road_class_score` | OSM `highway` tag | residential and tertiary feel calmer than primary | optional, easy win |

## How each feature is built

### Crime score per edge

**Idea.** Count crime points near the edge, weighted by severity and priority, split by time of day.

**Recipe:**

1. Reproject OSM edges and crime points to `EPSG:3857` (meters).
2. Buffer each edge by 50 m.
3. Spatial join the buffered edges with the crime points.
4. Group by edge, sum weighted crimes. Use `HOUR` to split day vs night.
5. Normalize across all edges so the score sits in `[0, 1]`.

```python
edges_buf = edges.copy()
edges_buf["geometry"] = edges.geometry.buffer(50)  # meters, EPSG:3857
joined = gpd.sjoin(edges_buf, crimes_gdf, how="left", predicate="contains")
edge_scores = joined.groupby(level=0).agg(
    n_day=("HOUR", lambda h: (h.between(6, 18)).sum()),
    n_night=("HOUR", lambda h: (~h.between(6, 18)).sum()),
)
```

**Open question.** Severity weights live in scoring, not here, so this step stays "data math" only.

### Walkability score per edge

**Idea.** Each edge inherits the walkability score of the block group its midpoint sits in.

**Recipe:**

1. Reproject edges and walkability polygons to the same CRS.
2. Compute the midpoint of each edge with `interpolate(0.5, normalized=True)`.
3. Spatial join midpoints with polygons (`predicate="within"`).
4. Copy `NatWalkInd` onto the edge as `walk_score`.
5. Fill missing scores with a neutral default (for example 5.0). Log how many edges fell back.

> **Why the midpoint, not the whole line?** Long edges can cross two block groups. A single point lands in exactly one polygon, which keeps the score unambiguous.

### Lighting score (source data ready)

**Idea.** For each edge, count operational street lights within 50 m, normalize by edge length, clip to `[0, 1]`.

**Source data.** `data/processed/streetlights/streetlights_processed.geojson` (55,506 active lights, snapshot 2026-04-30). Already filtered to `STATUS == "A"` AND `MAPNG_STAT_CD ∈ {"AB","OP"}` — every row in the file is an operational light. Validation + tie-out PASS, see [`docs/data/streetlights/CLEANING_AND_VALIDATION.md`](data/streetlights/CLEANING_AND_VALIDATION.md).

**Full feature spec (L1–L5).** [`docs/data/streetlights/FEATURE_CONTRACT.md`](data/streetlights/FEATURE_CONTRACT.md). The five proposed lighting features:

| ID | Feature | Definition |
| - | - | - |
| L1 | `streetlight_count_50m` | operational streetlights within 50 m of edge (count) |
| L2 | `streetlight_density_per_km` | lights per km of edge length |
| L3 | `percent_route_with_nearby_lighting` | fraction of edge length with a light within 50 m |
| L4 | `lighting_data_quality_flag` | regime tag: `city_layer` / `ucsd_uncovered` / `out_of_city` |
| L5 | `lighting_score` | normalized comfort score, 0–1 (the field scoring code reads) |

**Recipe sketch (L1):**

```python
import geopandas as gpd
lights = gpd.read_file("data/processed/streetlights/streetlights_processed.geojson").to_crs(3857)
edges_3857 = edges.to_crs(3857)
edges_buf = edges_3857.assign(geometry=edges_3857.buffer(50))
joined = gpd.sjoin(edges_buf, lights, how="left", predicate="contains")
edges_3857["streetlight_count_50m"] = joined.groupby(level=0).size()
```

**Caveat (UCSD interior).** The City layer is city-maintained streetlights. UCSD campus interior has 228 lights in the snapshot — non-zero but uneven. L4 tags those edges `ucsd_uncovered` and L5 falls back to neutral 0.5 instead of 0 so the router doesn't penalize campus-interior walks. UCSD campus polygon source still open (SANGIS vs. hand-built bbox) — pick one before computing L4.

### Buffered bike + scooter lane flag (future, depends on Max)

**Idea.** A binary or graded value per edge for whether a buffered bike or scooter lane runs along it. Buffered lanes correlate with calmer traffic, which usually feels more comfortable to a pedestrian.

**Recipe sketch:**

1. Reproject bike lanes and OSM edges to the same CRS.
2. For each edge, ask whether any bike lane segment runs nearby and roughly parallel.
3. Store as `bike_buffer_flag` (0 or 1) or `bike_buffer_score` (`[0, 1]`), whichever is easier.

## Things to be careful about

| Pitfall | Fix |
| - | - |
| CRS mismatch | Reproject to `EPSG:3857` before any distance operation |
| One way edges leaking in | Walking edges are usually two way, but check |
| Multi edges between same nodes | OSMnx returns a multigraph. Loop with `G.edges(keys=True, data=True)` |
| Sparse / missing features | Decide a fallback value per feature and document it here |

## Where features are stored

For now, write features back onto the OSMnx graph in memory:

```python
G[u][v][k]["crime_score"] = ...
G[u][v][k]["walk_score"] = ...
G[u][v][k]["lighting_score"] = ...
```

We are not pickling enriched graphs to disk yet. Fine for the prototype. If routing gets slow because feature computation reruns every time, we will save the enriched graph as a `.graphml` file and document it here.

## What to do this week (Ruan)

1. Get crime + walkability features attached to a small slice of the OSM graph (one neighborhood is plenty).
2. Add the L1 lighting feature on the same slice — source data is ready.
3. Print the distributions: are crime scores concentrated on a few edges, or spread out? Are walkability scores reasonable? Does the lighting count make sense for downtown vs residential?
4. Pick two test routes by hand (start address, end address) and confirm the per edge features look sane along them.
5. Write findings into [`status.md`](status.md).
