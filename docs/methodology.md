# SafePath methodology, to be edited

This is the long-form companion to the README. It explains how the data flows from a typed-in address to a route line on the map, what each step is doing, and why. If you want the quick version, the README's "Quick start" + "Data setup" sections are enough to get going. Come here when you want to actually understand or extend the pipeline.

## Connecting the pipeline to the user's question

The technical pieces below all exist to answer questions a user might actually ask about a route:

(TBD)

| User question                                                       | What in the pipeline answers it                                                |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| "Will this route feel isolated?"                                    | Walkability score per edge (NatWalkInd from the EPA index) — captures how connected and pedestrian-active the neighborhood is. |
| "Is this route worth the extra walking time?"                       | Balanced cost = length × (1 + 4·(1 − safety_score)) — exposes the tradeoff explicitly. |
| "Why is this route recommended?"                                    | Per-edge score breakdown returned alongside the route geometry — lighting, crime count, walkability per segment. |
| "Is the recommendation based on incidents, walkability, or what?"   | Crime score and walkability score are kept as separate inputs into the final cost; the explanation surfaces both. |
| "What are the limitations of the data?"                             | See "What this pipeline still doesn't know" at the bottom.                     |

The technical work is in service of these questions, not the other way around.

## Datasets and what each contributes

### `crime_final_gdf.gpkg` — geocoded crime points

Each row is a confirmed pedestrian-relevant incident filtered down from SDPD calls for service. Only calls with a confirmed outcome (arrest, report taken, or officer action) and a call type that directly affects pedestrian safety are kept — covering violent crimes (assault, robbery, ADW), active threats (weapons, criminal threats, stalking), public safety hazards (narcotics, hazardous conditions, bomb threats), and in-progress incidents (burglary, foot pursuit). Each row has an exact lat/lon point geometry, the original call type, priority level, and hour of day.

In scoring this becomes:

- **Crime density per street edge** — a 50m buffer is drawn around each edge in the OSMnx walking network and crime points inside are counted. A street with 15 incidents in its buffer scores higher than one with 2.
- **Severity weighting** — call types are assigned a severity weight so a single robbery contributes more than a trespassing call. Priority level (0 = immediate life threat, 4 = non-urgent) further weights the contribution.
- **Time-of-day split** — `HOUR` produces separate `crime_score_day` and `crime_score_night` per edge, since the same street can feel very different at 2pm vs. 2am.

### `walkability_final_gdf.gpkg` — block group walkability polygons

Each row is a Census block group polygon with a `NatWalkInd` score (1–20) from the EPA Smart Location Database. `NatWalkInd` is a composite of four sub-measures of the built environment:

- **D3B — Street intersection density** (weight 1/3): pedestrian-oriented intersections per square mile. Higher density = more route options and shorter blocks.
- **D4A — Distance to nearest transit stop** (weight 1/3): proximity to bus and rail from the population-weighted centroid. Block groups with no transit access rank lowest.
- **D2A — Employment and household entropy** (weight 1/6): mix of jobs and housing. Mixed-use areas are more walkable than purely residential or commercial.
- **D2B — 8-tier employment entropy** (weight 1/6): diversity of job types (retail, office, service, industrial, etc.). Varied employment generates foot traffic throughout the day.

Each sub-measure is ranked 1–20 by national quantile and combined; final scores 1–5.75 are least walkable, 15.26–20 most walkable.

In scoring this becomes:

- **Walkability score per street edge** — each edge is spatially joined to the block group containing its midpoint to inherit `NatWalkInd`.
- **Baseline pedestrian infrastructure signal** — independent of crime. A low-crime street in a poorly connected industrial zone still scores lower than a well-connected, transit-accessible street, pushing routes toward areas that are both safe *and* built for pedestrians.

### The street network — OSM nodes and edges

We download the San Diego walking network from OpenStreetMap via the OSMnx library. The graph has two parts:

- **Nodes** are intersections and dead ends — any point where two or more walking paths meet, or where a path terminates. Each node has lat/lon coordinates.
- **Edges** are the street segments connecting two nodes. A single block between two intersections is one edge. Each edge has attributes like length, street name, and highway type.

Every edge is what we score. A pedestrian walking from A to B traverses a sequence of edges, so the safety of the route is the sum of the per-edge safety scores along the path.

## End-to-end pipeline (backend → frontend)

This is what happens between the user typing an address and seeing a route line.

### 1. Address → coordinates (geopy)

`geopy` wraps Nominatim, OpenStreetMap's free geocoder. It turns a typed address like "6th Ave & University Ave, San Diego" into a `(lat, lon)` pair. No API key needed.

```python
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="safepath")
loc = geolocator.geocode("6th Ave & University Ave, San Diego")
# loc.latitude, loc.longitude
```

Output: `(lat, lon)` for the start and end addresses.

### 2. San Diego street network (osmnx)

`osmnx` downloads the city's walking graph from OpenStreetMap. The graph is the structure `networkx` will route through later, and it lets us snap arbitrary coordinates to the nearest real intersection.

```python
import osmnx as ox
G = ox.graph_from_place("San Diego, CA", network_type="walk")
ox.save_graphml(G, "san_diego.graphml")           # cache locally — download once
orig = ox.nearest_nodes(G, X=start_lon, Y=start_lat)
dest = ox.nearest_nodes(G, X=end_lon,   Y=end_lat)
```

Each edge straight out of OSMnx looks roughly like:

```
{ "length": 87.3, "lit": "yes", "highway": "residential",
  "sidewalk": "both", "name": "College Ave" }
```

Output: graph `G` plus integer node IDs `orig` and `dest`.

### 3. Crime/walkability data → projected geodataframes (geopandas)

The crime and walkability tables become geodataframes — pandas with a geometry column attached. We project everything to **EPSG:3857** (meters) before any distance work. Buffering in raw degrees is meaningless; we need real meters to say "50m around this edge."

```python
import geopandas as gpd
crimes_gdf = gpd.GeoDataFrame(
    crimes_df, geometry=gpd.points_from_xy(crimes_df.lon, crimes_df.lat), crs="EPSG:4326"
).to_crs("EPSG:3857")
```

### 3a. Crime geocoding (one-time preprocessing)

The SDPD dataset has addresses, not coordinates. Geocoding turns each unique address into `(lat, lon)` via Nominatim and caches the result. This is what `notebooks/crime-df-preprocessing.ipynb` does. Key points:

- Geocode **unique** addresses, not every row — the same intersection appears hundreds of times.
- Nominatim allows ~1 request/sec; use `RateLimiter` so you don't get IP-blocked.
- Save results to `geocode_cache.json` so re-runs skip already-geocoded addresses.
- Drop rows whose geocode failed.

### 3b. Walkability + Census boundary merge

The EPA walkability CSV has scores but no geometry; the Census TIGER shapefile has block-group polygons but no scores. We merge them on the shared block-group ID. This is what `notebooks/walkability-df-preprocessing.ipynb` does. Watch outs:

- The walkability CSV covers the whole US — filter to San Diego (`STATEFP == 6`, `COUNTYFP == 73`).
- `GEOID20` in the CSV may load as a float (`6.073017e+10`); cast to a 12-character zero-padded string before merging.
- Keep all shapefile siblings (`.shp`, `.dbf`, `.prj`, `.shx`, `.cpg`) in the same folder.

San Diego has ~2,058 block groups; that's how many rows the merged geodataframe should have.

### 4. Crime count per edge — spatial join (geopandas + shapely)

For each edge in the graph, draw a 50m polygon (buffer) around it and count how many crime points fall inside.

```python
edges_buf = edges.copy()
edges_buf["geometry"] = edges.geometry.buffer(50)        # meters, because EPSG:3857
joined = gpd.sjoin(edges_buf, crimes_gdf, how="left", predicate="contains")
crime_count = joined.groupby(level=0).size()
```

Output: every edge gets a `crime_count` attribute.

### 5. Walkability score per edge — midpoint lookup

For each edge, find its midpoint and check which block-group polygon it falls inside. That polygon's `NatWalkInd` becomes the edge's `walk_score`.

We use the midpoint (not the whole line) because a long segment could cross two block groups — a single point lands in exactly one polygon, so the score is unambiguous.

```python
edges_mid = edges.copy()
edges_mid["geometry"] = edges.geometry.interpolate(0.5, normalized=True)
edges_mid = gpd.sjoin(edges_mid, walk_gdf, how="left", predicate="within")
edges_mid["walk_score"] = edges_mid["NatWalkInd"].fillna(5.0)   # default for unmatched
```

### 6. Safety cost function — collapse attributes into one number

Each edge now carries OSM attributes (lighting, road type, sidewalk) plus our additions (`crime_count`, `walk_score`). The cost function normalizes each factor to 0–1 (1 = best, 0 = worst), combines them as a weighted average, and converts the resulting safety score into a cost:

```
cost = length × (1 + 4 × (1 − safety_score))
```

A perfect edge costs just its length. A terrible edge costs up to 5× its length, so the routing algorithm strongly avoids it. We use one number because `networkx` Dijkstra needs a single edge weight.

### 7. Route finding — Dijkstra (networkx)

`networkx` runs Dijkstra's algorithm three times, once per route preference, each pointing at a different edge weight:

| Weight                  | Resulting route |
| ----------------------- | --------------- |
| `weight="length"`       | Fastest — ignores safety |
| `weight="safety_cost"`  | Safest — minimizes the composite cost |
| `weight="balanced_cost"`| Balanced — alpha-weighted blend of length and safety |

```python
import networkx as nx
route = nx.shortest_path(G, orig, dest, weight="safety_cost")
```

Output: three ordered lists of node IDs.

### 8. Node IDs → coordinates + per-segment explanation

Node IDs are just integers; the map needs coordinates and the user needs to see *why* a route was picked. We convert each node ID to `(lat, lon)` and pull each edge's individual scores so the UI can show a per-segment breakdown.

```python
coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
edge_scores = [
    {
        "from": u, "to": v,
        "name": G[u][v][0].get("name"),
        "lit": G[u][v][0].get("lit"),
        "crime_count": G[u][v][0].get("crime_count", 0),
        "walk_score": G[u][v][0].get("walk_score", 5.0),
    }
    for u, v in zip(route, route[1:])
]
```

### 9. Frontend — what Streamlit gets

Streamlit only sees two things:

1. **Three lists of `(lat, lon)` coordinates** — one per route preference. `folium` draws three colored lines on an interactive map (e.g., green safest, blue balanced, red fastest). The user can pan, zoom, and visually compare.
2. **Per-edge score breakdowns** — street name, lighting status, crime count, walkability score per segment. Displayed below the map so the user can see exactly why each block scored the way it did. This is the "explainability" surface.

Everything else — the graph, the preprocessing, the spatial joins, the scoring — stays in the backend.

## Full pipeline at a glance

```
user types address
  ↓ geopy (Nominatim)
(lat, lon) for start + end
  ↓ osmnx
walking graph G + nearest-node IDs
  ↓ geopandas (preprocessing already done — load .gpkg files)
crime points (projected) + walkability polygons (projected)
  ↓ buffer + sjoin
crime_count on every edge
  ↓ midpoint + sjoin
walk_score on every edge
  ↓ scoring function
safety_cost (and balanced_cost) on every edge
  ↓ networkx Dijkstra × 3 modes
three node-id paths
  ↓ id → (lat, lon) + per-segment breakdown
Streamlit: folium map + score table
```

## Why GeoPandas (and not just pandas)

Standard pandas works great for tabular data but has no concept of geography — it cannot answer "which neighborhood does this point fall inside?" or "how many crimes occurred within this polygon?" GeoPandas extends pandas by adding a geometry column to every row, turning a plain table into a spatially aware dataset.

In SafePath, GeoPandas does four things plain pandas cannot:

**1. Reads spatial files.** `gpd.read_file("walkability_final_gdf.gpkg")` loads a GeoPackage with geometry attached — no manual coordinate parsing.

**2. Reprojects coordinate systems.** `crime_gdf.to_crs(epsg=4326)` reprojects in one line so spatial operations across datasets work correctly.

**3. Spatial joins.** `gpd.sjoin(edges_gdf, walkability_gdf, how="left", predicate="intersects")` joins two datasets by *geographic overlap* rather than a shared key column.

**4. Geometry operations.** `contains`, `intersects`, `within`, `buffer` (e.g. 50m around an edge), and `.area` are all built in. Without GeoPandas, all of this would mean writing geometry math from scratch on top of Shapely.


Reference: https://docs.google.com/document/d/1y2eViHtmPmksf7rXS3IgglXV2l2p_o8H/edit?usp=sharing&ouid=102290811200605502736&rtpof=true&sd=true

## Optional — rerun from raw data

You usually don't need this. Only do it if you want to refresh the underlying data (e.g., a newer year of SDPD calls).

### Download each raw dataset

**SD Police Calls for Service**
1. https://data.sandiego.gov/datasets/police-calls-for-service/
2. Download the CSV for the most recent year.
3. Save to `data/raw/pd_calls_for_service_YYYY_datasd.csv`.

**U.S. Walkability Index**
1. https://www.kaggle.com/datasets/stacey06/u-s-walkability-index (free Kaggle account required).
2. Save the CSV to `data/raw/EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv`.

**Census TIGER Block Group Shapefile**
1. https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip
2. Unzip into `data/raw/tl_2020_06_bg/`. Keep all sibling files.

`data/raw/` should look like:

```
data/raw/
  pd_calls_for_service_YYYY_datasd.csv
  EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv
  tl_2020_06_bg/
    tl_2020_06_bg.dbf
    tl_2020_06_bg.prj
    tl_2020_06_bg.shp
    tl_2020_06_bg.shx
```

### Run the preprocessing notebooks

1. Open `notebooks/crime-df-preprocessing.ipynb` and run from the top. Filters SDPD calls to pedestrian-relevant incidents, geocodes each address via Nominatim, and writes `data/processed/crime_final_gdf.gpkg` plus `geocode_cache.json`. **Expect several hours on first run** (one geocode per second). Don't delete the cache; it lets you resume.
2. Open `notebooks/walkability-df-preprocessing.ipynb` and run from the top. Filters the EPA database to San Diego block groups, merges with TIGER polygons, writes `data/processed/walkability_final_gdf.gpkg`.

Both must finish before the scoring step.

## What this pipeline still doesn't know

Worth being honest about so the team can plan around it.

- **SDPD calls for service ≠ crime that happened.** Some incidents go unreported. Some calls turn out to be nothing. Disposition filtering helps but doesn't fully fix this.
- **Time-of-day in the cleaned data is incident-specific, not user-specific.** The crime score knows when each incident occurred, but the route picker currently doesn't ask the user *when* they want to walk. That's a planned UI question.
- **Lighting comes from OSM `lit` tags**, which are sparse and inconsistent across the city. Many edges will have `lit = None`.
- **NatWalkInd is national-quantile, not San-Diego-quantile.** A "low" walkability score in SD might still be more walkable than the median US block group.
- **No real-time signal.** No live transit, traffic, construction, or recent-incident data — everything is historical.
- **Sample size.** The processed crime file currently covers a limited window (months, not years). Sparse-coverage edges will look "safe" mostly because no one has called the cops there yet.
- **No user feedback loop.** We can't tell whether users actually felt safer on the routes we recommended.

These are good candidates for future work — see `STATUS.md`.
