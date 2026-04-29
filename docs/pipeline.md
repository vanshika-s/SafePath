# SafePath Technical Pipeline

## Purpose of this document

This document explains how SafePath data moves from a user's typed address to route lines on the map.

Use this file when you want to understand the overall backend and frontend flow, especially if you are new to packages like `geopy`, `osmnx`, `geopandas`, `networkx`, `folium`, or `Streamlit`.

This file is **not** the README, the weekly status, or the preprocessing validation guide.

- For project overview and setup, read `README.md`.
- For current progress and next tasks, read the latest file in `docs/status/`.
- For scoring assumptions and route methodology, read `docs/methodology.md`.
- For how cleaned data files were created and validated, read `docs/preprocessing.md`.

---

## Backend vs frontend in simple terms

**Backend** means the hidden work that prepares the route recommendation. It loads data, builds the street network, calculates scores, and chooses routes.

**Frontend** means what the user sees. In SafePath, this is the Streamlit page with a map, route options, and plain-language explanations.

A simple way to think about it:

```text
Backend = decides the routes
Frontend = shows the routes
```

---

## Full pipeline at a glance

```text
User types start and destination
  ↓
geopy converts addresses into latitude and longitude
  ↓
osmnx loads the San Diego walking network
  ↓
coordinates are snapped to nearest graph nodes
  ↓
processed crime and walkability files are loaded with geopandas
  ↓
crime counts are assigned to nearby street edges
  ↓
walkability scores are assigned to street edges
  ↓
safety_cost is calculated for every edge
  ↓
networkx finds fastest, safest, and balanced routes
  ↓
node IDs are converted back into latitude and longitude coordinates
  ↓
Streamlit and folium display route lines and explanations
```

---

## Backend data pipeline

### 1. Address input to coordinates with `geopy`

#### What it is

`geopy` is a Python package that converts a human-readable address into a latitude and longitude coordinate pair.

It can use Nominatim, OpenStreetMap's free geocoding service. No API key is needed for basic use.

#### Why we need it

A user may type something like:

```text
6th Ave & University Ave, San Diego
```

The computer cannot route using that text directly. It needs numbers.

`geopy` turns the text address into coordinates like:

```text
(32.748, -117.159)
```

#### Important functions

```python
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="safepath")
loc = geolocator.geocode("6th Ave & University Ave, San Diego")

lat = loc.latitude
lng = loc.longitude
```

#### Output

```text
(lat, lng) for the start location
(lat, lng) for the destination
```

These coordinates are then passed to `osmnx`.

---

### 2. San Diego street network with `osmnx`

#### What it is

`osmnx` downloads real street map data from OpenStreetMap and turns it into a graph.

A graph is made of:

- **nodes**: intersections, dead ends, or points where paths connect
- **edges**: walkable street segments between nodes

Think of San Diego as a giant connect-the-dots map. Each dot is an intersection, and each line is a walkable street segment.

#### Why we need it

Without the walking graph, SafePath has no map to route through.

`osmnx` gives us the street-level graph that `networkx` will later use to find routes. It also lets us snap a user's latitude and longitude to the nearest real node in the graph.

#### Important functions

```python
import osmnx as ox

G = ox.graph_from_place("San Diego, CA", network_type="walk")
ox.save_graphml(G, "san_diego.graphml")

orig_node = ox.nearest_nodes(G, X=start_lng, Y=start_lat)
dest_node = ox.nearest_nodes(G, X=end_lng, Y=end_lat)
```

Useful functions:

```python
ox.graph_from_place("San Diego, CA", network_type="walk")
```

Downloads only walkable streets.

```python
ox.save_graphml(G, "san_diego.graphml")
```

Saves the graph locally so we do not need to download it every time.

```python
ox.load_graphml("san_diego.graphml")
```

Loads the cached graph from disk.

```python
ox.graph_to_gdfs(G)
```

Converts the graph into GeoDataFrames for nodes and edges.

```python
ox.nearest_nodes(G, X=lng, Y=lat)
```

Snaps a latitude and longitude point to the closest graph node.

#### Example edge from OSMnx

An edge may look roughly like this:

```python
{
    "length": 87.3,
    "lit": "yes",
    "highway": "residential",
    "sidewalk": "both",
    "name": "College Ave"
}
```

#### Output

```text
walking graph G
origin node ID
destination node ID
```

---

### 3. Load processed spatial data with `geopandas`

#### What it is

`geopandas` is like pandas, but with geography built in.

In pandas, each row is just data. In GeoPandas, each row can also have geometry:

- a point, such as a crime incident
- a line, such as a street segment
- a polygon, such as a Census block group

This lets us ask spatial questions like:

```text
Which crime points are near this street segment?
Which walkability polygon contains this street segment midpoint?
```

#### Why we need it

SafePath uses processed spatial files:

- `crime_final_gdf.gpkg`
- `walkability_final_gdf.gpkg`

GeoPandas lets us load those files and combine them with OSM street edges.

#### Coordinate systems

Raw latitude and longitude usually use `EPSG:4326`, which is measured in degrees.

Distance work should use a projected coordinate system, such as `EPSG:3857`, which is measured in meters.

This matters because a 50 meter buffer only makes sense after projection.

#### Important functions

```python
import geopandas as gpd

crimes_gdf = gpd.read_file("data/processed/crime_final_gdf.gpkg").to_crs("EPSG:3857")
walk_gdf = gpd.read_file("data/processed/walkability_final_gdf.gpkg").to_crs("EPSG:3857")
```

If starting from a regular DataFrame with longitude and latitude:

```python
crimes_gdf = gpd.GeoDataFrame(
    crimes_df,
    geometry=gpd.points_from_xy(crimes_df.lng, crimes_df.lat),
    crs="EPSG:4326"
).to_crs("EPSG:3857")
```

#### Output

```text
projected crime points
projected walkability polygons
projected street edges
```

---

### 4. Crime count per street edge

#### What it is

For each street edge, we draw a 50 meter buffer around it and count how many crime points fall inside.

That count becomes an edge feature called something like:

```text
crime_count
```

#### Why we need it

A street segment with many nearby incidents should not be treated the same as a street segment with no nearby incidents.

This step is what makes SafePath use historical crime data in routing.

#### Important functions

```python
edges_buffered = edges.copy()
edges_buffered["geometry"] = edges.geometry.buffer(50)

joined = gpd.sjoin(
    edges_buffered,
    crimes_gdf,
    how="left",
    predicate="contains"
)
```

Important validation note:

With a left spatial join, be careful when counting matches. If an edge has no matching crime point, it may still appear once with missing crime fields. Counting rows with `.size()` can accidentally turn 0 matches into 1.

A safer approach is to count a column that only exists when a crime point matched, such as `index_right`:

```python
crime_count = joined.groupby(joined.index)["index_right"].count()
```

#### Output

```text
crime_count on every street edge
```

---

### 5. Walkability score per street edge

#### What it is

For each street edge, we find the midpoint of the edge. Then we check which walkability polygon contains that midpoint.

The polygon's `NatWalkInd` score becomes the edge's walkability score.

#### Why we use the midpoint

A long street segment may cross more than one block group. The midpoint gives us one clean point that lands in one polygon.

This keeps the edge-level score simple and unambiguous.

#### Important functions

```python
edges_mid = edges.copy()
edges_mid["geometry"] = edges.geometry.interpolate(0.5, normalized=True)

edges_mid = gpd.sjoin(
    edges_mid,
    walk_gdf,
    how="left",
    predicate="within"
)

edges_mid["walk_score"] = edges_mid["NatWalkInd"].fillna(5.0)
```

#### Output

```text
walk_score on every street edge
```

---

### 6. Safety cost function

#### What it is

Each edge now has multiple pieces of information, such as:

- edge length
- nearby crime count
- walkability score
- possible OpenStreetMap attributes, such as lighting or sidewalk tags

The scoring function combines these into one number that `networkx` can use.

#### Why we need it

`networkx` routing needs one edge weight.

It cannot directly decide from five separate columns unless we collapse them into one cost.

#### Planned scoring idea

Each feature is normalized to a 0 to 1 scale:

```text
1 = better or safer
0 = worse or less safe
```

Then the features are combined into a safety score:

```text
safety_score = weighted average of normalized feature scores
```

Then the safety score is converted into a route cost:

```text
safety_cost = length × (1 + 4 × (1 − safety_score))
```

Plain English:

- A very safe edge costs close to its real walking length.
- A less safe edge becomes more expensive.
- The routing algorithm avoids expensive edges when looking for a safer route.

#### Important functions

Example planned function:

```python
def compute_safety_cost(edge_data):
    ...
    return safety_cost
```

Looping through graph edges:

```python
for u, v, k, data in G.edges(keys=True, data=True):
    G[u][v][k]["safety_cost"] = compute_safety_cost(data)
```

#### Output

```text
safety_cost on every edge
```

---

### 7. Route finding with `networkx`

#### What it is

`networkx` is a Python graph library. It can run shortest path algorithms, including Dijkstra's algorithm.

Dijkstra's algorithm finds the lowest-cost path between two nodes.

#### Why we need it

San Diego has many possible walking paths between two locations. We cannot manually check all of them.

`networkx` finds the best path based on the weight we choose.

#### Route modes

SafePath can run routing multiple times with different weights:

| Route mode | Weight used | Meaning |
|---|---|---|
| Fastest | `length` | Minimizes walking distance |
| Safest | `safety_cost` | Minimizes safety-adjusted cost |
| Balanced | `balanced_cost` | Blends distance and safety |

#### Important functions

```python
import networkx as nx

fastest_route = nx.shortest_path(G, orig_node, dest_node, weight="length")
safest_route = nx.shortest_path(G, orig_node, dest_node, weight="safety_cost")
balanced_route = nx.shortest_path(G, orig_node, dest_node, weight="balanced_cost")
```

#### Output

```text
three ordered lists of node IDs
```

Each list is one route.

---

### 8. Node IDs to coordinates and explanations

#### What it is

`networkx` returns node IDs, such as:

```text
[112345, 112346, 112350]
```

A map cannot draw those IDs directly. We need to convert each node ID back into latitude and longitude coordinates.

We also pull edge-level score details so the app can explain why a route was chosen.

#### Important functions

```python
route_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route]
```

To read edge data between consecutive nodes:

```python
edge_scores = []

for u, v in zip(route, route[1:]):
    data = G[u][v][0]
    edge_scores.append({
        "from": u,
        "to": v,
        "name": data.get("name"),
        "crime_count": data.get("crime_count", 0),
        "walk_score": data.get("walk_score"),
        "safety_cost": data.get("safety_cost")
    })
```

#### Output

```text
route coordinates
per-edge score explanations
```

---

## Frontend: what Streamlit displays

The backend hands Streamlit two main things.

### 1. Route coordinates

For each route mode, Streamlit receives a list of coordinates.

`folium` uses these coordinates to draw route lines on the map.

Example colors:

| Route | Color |
|---|---|
| Safest | Green |
| Balanced | Blue |
| Fastest | Red |

### 2. Route explanation

Streamlit can display a simple explanation below the map.

Example:

```text
This route avoids several nearby high-crime segments and passes through more walkable block groups, but it is 6 minutes longer than the fastest route.
```

It can also display a table with per-segment details:

| Street | Nearby crime count | Walkability score | Safety cost |
|---|---:|---:|---:|
| College Ave | 3 | 14.2 | 132.5 |
| El Cajon Blvd | 8 | 10.1 | 286.4 |

Everything else stays in the backend.

---

## From notebooks to production code

Once the full routing pipeline works in notebooks, the proven logic should be moved into clean Python files under `src/`.

The notebooks are for exploration. The `src/` files are for reusable project code.

### Why move from notebooks to `.py` files?

| Notebook problem | Why `.py` files help |
|---|---|
| Hard to import | Functions in `src/` can be imported by the app |
| Hard to test | Unit tests can call one function at a time |
| Hidden state | `.py` files run fresh every time |
| Hard to review | Small functions are easier to inspect and debug |

Rule of thumb:

```text
Use notebooks to figure things out.
Use .py files to keep things working.
```

### Recommended `src/` layout

```text
src/
  data_loader.py    # load_crime_gdf(), load_walk_gdf(), load_graph()
  geocoder.py       # address_to_node(address, G)
  scorer.py         # compute_crime_score(), compute_walk_score(), safety_cost()
  router.py         # get_routes(G, orig_node, dest_node)
  pipeline.py       # run(origin_address, destination_address)
```

The Streamlit app should stay thin.

```text
app/main.py
```

should mostly call:

```python
from src.pipeline import run
```

and then display the returned map data.

---

## Unit tests

A unit test is a short check that gives one function known input and confirms that the output is what we expect.

### Example test

```python
def test_dark_street_costs_more_than_lit_street():
    lit_edge = {
        "lit": "yes",
        "crime_count": 0,
        "walk_score": 12.0,
        "length": 100
    }

    dark_edge = {
        "lit": "no",
        "crime_count": 0,
        "walk_score": 12.0,
        "length": 100
    }

    assert safety_cost(dark_edge) > safety_cost(lit_edge)
```

This test does not need a map or real data. It only tests the scoring function.

### Recommended `tests/` layout

```text
tests/
  test_geocoder.py   # does a real SD address return a valid graph node ID?
  test_scorer.py     # does a risky edge cost more than a safer edge?
  test_router.py     # do all route modes connect start to end?
  test_pipeline.py   # end-to-end smoke test with two known SD addresses
```

### How to run tests

```bash
pip install pytest
pytest tests/
pytest tests/test_scorer.py
pytest -v
```

### Development flow

```text
1. Explore idea in notebook
2. Turn working logic into a small function in src/
3. Add at least one unit test
4. Connect the function to the app only after it passes
```

---

## Glossary

| Term | Meaning |
|---|---|
| Backend | Hidden code that loads data, scores routes, and sends results to the frontend |
| Frontend | User-facing app page that displays the map and route explanation |
| Node | A graph point, usually an intersection or path endpoint |
| Edge | A walkable street segment between two nodes |
| GeoDataFrame | A table with a geometry column |
| CRS | Coordinate reference system, or how geographic coordinates are represented |
| Buffer | A zone around a geometry, such as 50 meters around a street segment |
| Spatial join | A join based on location, not matching text IDs |
| Dijkstra's algorithm | Algorithm that finds the lowest-cost path through a graph |
| Edge weight | The number used by the routing algorithm to decide which path is cheaper |
