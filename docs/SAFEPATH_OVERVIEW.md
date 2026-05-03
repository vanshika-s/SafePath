# SafePath — Multi-agent repo breakdown

> Full repo analysis by 4 agents (Data Engineer / Workflow Orchestrator / Knowledge Synthesizer / Technical Teacher). Beginner-friendly but technically deep. Generated 2026-05-01.

Repo accessed locally at `/Users/maximechung/Projects/team-repos`, branch `main`, latest commit through the streetlight + Clery work this session.

---

## AGENT 1 — Data Engineer

Per-file breakdown of every executable / data file.

### `src/data/get_streetlights.py`
- **Input data:** none (HTTP source). Fetches from City of San Diego ArcGIS Feature Layer at `https://webmaps.sandiego.gov/arcgis/rest/services/Planning/PLN_Mobility/MapServer/1`.
- **Cleaning steps:** none — this is a downloader, not a cleaner. Hits `/1?f=pjson` once for the layer descriptor, then pages `/1/query` with `where=1=1`, `outFields=*`, `outSR=4326`, `f=geojson`, `resultRecordCount=2000`, until the page returns 0 features or `exceededTransferLimit` is false.
- **Transformations:** concatenates pages into a single FeatureCollection. No filtering. No reprojection (server is asked for `EPSG:4326` directly).
- **Output:** `data/raw/streetlights/streetlights_YYYYMMDD.geojson` + `streetlights_layer_desc_YYYYMMDD.json` + `SOURCE_METADATA.yaml`.
- **Risks / assumptions:** stdlib `urllib` only (no `requests` / `geopandas` dependency, deliberately bullet-proof). 250 ms politeness sleep + 30 s timeout + 3 retries with 2/4/8 s backoff on 5xx. Aborts on 4xx (don't retry our own bad requests). Sanity cap of 200 pages so a server bug can't infinite-loop. **Not idempotent** — running again produces a new dated file; old snapshots are kept.

### `src/data/clean_streetlights.py`
- **Input data:** `data/raw/streetlights/streetlights_YYYYMMDD.geojson` (output of the downloader).
- **Cleaning steps:**
  1. Drop rows with null geometry or coords outside the SD bbox `(-117.4, 32.4, -116.8, 33.2)`.
  2. Filter to active set: `STATUS == "A"` AND `MAPNG_STAT_CD ∈ {"AB", "OP"}` (operational lights only).
  3. Flag (don't drop) duplicate `SAPOBJNR` with `dup_sapobjnr_flag` (0 / 1).
  4. Add `data_quality_flag = "ok"` for kept rows.
- **Transformations:** writes two files — `interim` keeps every original field, `processed` trims to scoring columns.
- **Output:** `data/interim/streetlights/streetlights_active_wgs84.geojson` (55,506 features, all 39 original fields) and `data/processed/streetlights/streetlights_processed.geojson` (55,506 features, 6 fields + geometry).
- **Risks / assumptions:**
  - **Bug**: line 102 reads `props.get("DRAWING_DATE")`, but the source field is named `DRAWING_NO` and is 100% null anyway. Result: `drawing_date` column in processed file is always null. Benignly null — no consumer reads it — but the column is dead weight.
  - Tie-out arithmetic holds: 56,049 raw − 543 (`STATUS=I`) = 55,506 processed. ✓
  - Bbox check assumes EPSG:4326. If the server ever returns a different CRS the bbox filter would silently drop everything.

### `notebooks/crime-df-preprocessing.ipynb`
- **Input data:** SDPD Calls for Service CSV at `data/raw/pd_calls_for_service_YYYY_datasd.csv`.
- **Cleaning steps:** filter `DISPOSITION` to confirmed outcomes (arrest / report taken / officer action), filter `CALL_TYPE` to pedestrian-relevant categories, drop rows with missing road name.
- **Transformations:** build `full_address = address + ", San Diego, CA"`, geocode each unique address via Nominatim at 1 req/s, cache results in `geocode_cache.json`, drop rows where geocoding failed, attach point geometry.
- **Output:** `data/processed/crime_final_gdf.gpkg` (GeoPackage, EPSG:4326).
- **Risks / assumptions:** Nominatim limit means **first run takes hours**; never delete `geocode_cache.json`. Geocoding accuracy depends on address quality — typos and abbreviations silently drop incidents.

### `notebooks/walkability-df-preprocessing.ipynb`
- **Input data:** EPA Walkability Index CSV + Census TIGER 2020 California block group shapefile (`data/raw/tl_2020_06_bg/`).
- **Cleaning steps:** filter EPA to San Diego County (`STATEFP == 6`, `COUNTYFP == 73`), standardize `GEOID10` to a 12-char zero-padded string (pandas loads it as float and loses leading zeros).
- **Transformations:** merge EPA scores onto TIGER polygons by `GEOID10`. Result is one row per SD block group with both score and polygon geometry.
- **Output:** `data/processed/walkability_final_gdf.gpkg` (~2,058 polygons).
- **Risks / assumptions:** if `len(merged) != len(walk_sd)` then the join lost rows — sanity check mandatory. EPA dataset is 2021 — the score is a snapshot, not live.

### `data/processed/ucsd_clery/ucsd_clery_stats_2022_2024.csv`
- **Input data:** `data/raw/ucsd_police_logs/annualclery.pdf` pp. 141–144 (UCSD Annual Security & Fire Safety Report 2025, reissued Feb 2026).
- **Cleaning steps:** `pdftotext -layout -f 141 -l 160` → manual table parse → CSV write.
- **Transformations:** wide tables (one row per offense, columns for year × geography) flattened to **long format** (one row per offense × year × geography). Asterisks/crosses preserved as `revised_flag` enum.
- **Output:** 66-row long CSV with 10 columns. Schema in [`docs/data/ucsd_crime/00_NEXT_SESSION.md`](data/ucsd_crime/00_NEXT_SESSION.md) §7.
- **Risks / assumptions:** Annual aggregates per Clery geography — **cannot become a per-edge feature** (see Decision in handoff §4). Cross-category sums double-count (Rape + Domestic Violence may be the same incident). Always use `category=criminal` OR `category=vawa`, never both summed.

### `data/raw/ucsd_police_logs/logs_20260501.csv`
- **Input data:** placeholder (1 byte, single newline).
- **Status:** **NOT YET POPULATED.** Blocks F10 (`campus_incident_score`).

### Documentation files
- 7 root markdown docs under `docs/` (`00_project_map.md`, `01_data_sources.md`, `02_data_cleaning.md`, `03_feature_engineering.md`, `04_scoring_methodology.md`, `status.md`, plus `README.md` at the root). All conflict-marker-poisoned versions were resolved this session.
- `docs/data/streetlights/` — workstream-specific docs (HANDOFF_v0, CLEANING_AND_VALIDATION, FEATURE_CONTRACT — these three are live; the rest are stale templates per audit).
- `docs/data/ucsd_crime/00_NEXT_SESSION.md` — handoff for the still-open UCSD daily-log workstream.

---

## AGENT 2 — Workflow Orchestrator

```
Step 1 — RAW DATA INGEST
  ┌─ get_streetlights.py            → data/raw/streetlights/*.geojson
  ├─ (manual download)              → data/raw/pd_calls_for_service_*.csv (SDPD)
  ├─ (manual download)              → data/raw/EPA_SmartLocationDatabase_*.csv
  ├─ (manual download)              → data/raw/tl_2020_06_bg/*.shp (TIGER)
  ├─ (manual download)              → data/raw/ucsd_police_logs/annualclery.pdf
  └─ (PENDING) ucsd daily scrape    → data/raw/ucsd_police_logs/logs_*.csv

Step 2 — CLEAN
  ┌─ clean_streetlights.py          → data/processed/streetlights/streetlights_processed.geojson
  ├─ crime-df-preprocessing.ipynb   → data/processed/crime_final_gdf.gpkg
  ├─ walkability-df-preprocessing.ipynb → data/processed/walkability_final_gdf.gpkg
  └─ Clery PDF extraction           → data/processed/ucsd_clery/ucsd_clery_stats_2022_2024.csv

Step 3 — FEATURE ENGINEERING (NOT YET RUN)
  Builds in OSMnx walking graph G = ox.graph_from_place("San Diego, CA", network_type="walk")
  For each edge (u, v, key):
    ├─ crime_score_day / crime_score_night ← spatial-join crime points within 50 m buffer
    ├─ walk_score                          ← edge midpoint within block-group polygon → NatWalkInd
    ├─ lighting_score (L1–L5)              ← spatial-join streetlight points within 50 m buffer
    ├─ bike_buffer_score (F6–F8)           ← bike lanes within 15 m of edge midline
    ├─ road_class_score                    ← OSM `highway` tag → table lookup
    └─ campus_incident_score (F10)         ← (BLOCKED — needs daily UCSD log + lookup table)

Step 4 — SCORING (NOT YET RUN)
  safety_score = w_crime*crime_component + w_walk*walk_score + w_light*lighting_score
               + w_bike*bike_buffer_score + w_road*road_class_score
  (weights TBD by Matthew; sum to 1; crime_component picks day or night)

Step 5 — ROUTE COST (NOT YET RUN)
  route_cost   = length * (1 + 4 * (1 - safety_score))
  balanced_cost = alpha * length + (1 - alpha) * route_cost   (alpha owned by Ajay, default 0.5)

Step 6 — ROUTING (NOT YET RUN)
  networkx.shortest_path(G, orig, dest, weight=...)
  Run 3 times: weight=length (fastest), weight=route_cost (safest), weight=balanced_cost (balanced)

Step 7 — APP (Week 6)
  Streamlit + (Google Maps OR Leaflet) — see 04_scoring_methodology §What the app should eventually show

Full pipeline:
raw data → cleaning → feature engineering → scoring → routing → output (Streamlit map + 3 routes + per-segment explanation)
```

**Execution order (file-level dependencies):**

| Step | Depends on | Owner |
| - | - | - |
| `get_streetlights.py` | none | Max — done |
| `clean_streetlights.py` | `get_streetlights.py` output | Max — done |
| `crime-df-preprocessing.ipynb` | raw SDPD CSV | Matthew — done |
| `walkability-df-preprocessing.ipynb` | raw EPA CSV + TIGER zip | Matthew — done |
| Clery extraction | `annualclery.pdf` | Max — done this session |
| Daily-log scrape | (TBD scraping script) | Max — **blocked, P0** |
| OSMnx walking graph build | none | Ruhan — in progress |
| Per-edge feature attachment | all processed datasets + walking graph | Ruhan — in progress |
| Scoring formula + weights | feature attachment + Matthew's weights | Matthew — in progress |
| Weight comparison | scoring formula | Ajay — blocked on Matthew |
| Streamlit app | scoring outputs stable on a test neighborhood | Week 6 |

---

## AGENT 3 — Knowledge Synthesizer

### Key concepts

- **OSM walking edge as the unit of analysis.** Everything in the project ultimately attaches to OSM edges. Every dataset gets reduced to "one or two numbers per edge," then scoring reads only those numbers. This is the spine.
- **Snapshot-based, not live.** Every dataset is a point-in-time snapshot. Crime is a 2026 window. Walkability is the 2021 EPA index. Streetlights are 2026-04-30. OSM is downloaded fresh per session. No real-time data anywhere.
- **Weighted-average → inverse-cost transformation.** A `[0, 1]` `safety_score` is converted to a `route_cost` by `length * (1 + 4 * (1 - safety_score))`. The factor 4 is a knob: higher = router avoids low-score edges harder.
- **Three routes from one graph.** Same graph, three different edge-weights, three different shortest paths. Cheap to compute once features exist.

### Repeated patterns

- **Raw → interim → processed**, one-way flow. Documented in `02_data_cleaning.md` and again in every workstream's plan.
- **`SOURCE_METADATA.yaml`** sits next to every raw download (only streetlights has one so far; Clery + UCSD log are missing it).
- **Long-format CSVs** (one row per offense × year × geography) for tabular sources — Clery follows this; daily log will too.
- **Validation has 4 layers:** structural → logical → business-rule → tie-out. Streetlight `CLEANING_AND_VALIDATION.md` is the worked example.
- **"Owner" labeling** in every doc maps each dataset to a single person. After this session: Matthew (crime, walkability), Max (streetlights ✓, Clery ✓, bike lanes ✗, daily log ✗), Ruhan (OSM + feature attachment), Ajay (weight comparison).

### Inconsistencies / gaps

- **No `src/` modules for scoring or routing yet.** Week-5 sprint goal is to lift the logic out of notebooks into `src/`; not done yet.
- **No tests.** Week-7 sprint goal mentions pytest; no `tests/` directory exists.
- **No Streamlit app file.** `app/` is `.gitkeep` only.
- **`drawing_date` column** in processed streetlights is sourced from a non-existent key — always null. (Documented bug, low impact.)
- **Bike-lane workstream has no raw data, no cleaning script, no feature spec is computed yet.** Just citations + a numeric F6/F7/F8 sketch in `03_feature_engineering.md`.
- **UCSD daily-log workstream is unstarted past placeholder.** Empty CSV, no scraper, no lookup table, no campus polygon chosen.
- **Cross-doc references mostly hyperlinked**, but `.gitignore`'s `/data/` rule means the `docs/data/streetlights/` and `docs/data/ucsd_crime/` referenced docs require `git add -f` to actually push.

### Missing pieces or risks

| Risk | Why it matters |
| - | - |
| Crime "underreporting bias" | A quiet-looking neighborhood may have fewer 911 calls but more actual incidents. Already in `04_scoring_methodology.md` Limitations. |
| Walkability is a proxy | `NatWalkInd` reflects street network + land use, not human comfort. Same caveat documented. |
| Lighting "administrative active" ≠ "currently on" | `STATUS == "A"` means the city's database considers the light active — not that it's energized right now. |
| UCSD interior coverage uneven | 228 city lights inside the campus interior bbox, but coverage is uneven; L4 falls back to neutral 0.5 there. |
| Cross-category Clery double-count | Same incident may appear in both Criminal Offenses and VAWA Offenses tables. Documented in `00_NEXT_SESSION.md` §3. |
| No campus polygon chosen | Blocks F11 (`is_on_ucsd_campus`) → blocks F4 lighting fallback rule → blocks F10 routing. |
| Token-economy / context-drift | Multiple branches diverged earlier this quarter; merge-conflict markers landed in 7 root docs. Resolved this session, but the pattern can recur. |

---

## AGENT 4 — Technical Teacher

7 concepts. Read in order — each builds on the prior.

### Concept 1 — Geographic Coordinate Reference System (CRS)
- **Explanation:** A CRS tells you what your numbers (`x, y` or `lat, lon`) mean on the actual Earth. Two CRSs matter here:
  - **EPSG:4326** = WGS84 = degrees of longitude / latitude. Units are degrees. Used for storage and most map APIs.
  - **EPSG:3857** = Web Mercator = meters in a flat-projected plane. Units are meters. Used for any distance math.
- **Example:** Two points at `(32.870, -117.235)` and `(32.871, -117.235)` are roughly 111 m apart, but their numeric difference in degrees is `0.001`. If you naively buffered by `0.001` you'd cover way more than 1 m near the equator and way less near the poles. So **always reproject to EPSG:3857 before any "within X meters" operation**, then reproject back if you want lat/lon for storage.
- **Why it matters:** Buffering in degrees is meaningless. Most spatial bugs in beginner code are CRS bugs.

### Concept 2 — GeoJSON FeatureCollection
- **Explanation:** A JSON file containing a list of "features." Each feature has a `geometry` (Point / LineString / Polygon with coordinates) and a `properties` object (the table-like attributes). The whole thing is wrapped in `{"type": "FeatureCollection", "crs": {...}, "features": [...]}`.
- **Example:** One streetlight in our processed file:
  ```json
  {"type":"Feature","geometry":{"type":"Point","coordinates":[-117.236,32.766]},"properties":{"sap_obj_nr":"...","status":"A","mapng_stat_cd":"AB","drawing_date":null,"dup_sapobjnr_flag":0,"data_quality_flag":"ok"}}
  ```
- **Why it matters:** Every spatial dataset in this project ends up as a GeoJSON or GeoPackage. Reading them with `geopandas.read_file()` gives you a `GeoDataFrame` — a pandas DataFrame with a special `geometry` column.

### Concept 3 — Spatial join
- **Explanation:** A SQL-style join where the matching condition is **geometry**, not a key column. Common predicates: `contains` (point inside polygon), `intersects` (any overlap), `within` (one geometry fully inside another).
- **Example:** "Attach a walkability score to each OSM edge" = take edge midpoint (Point) → join with block group polygons (`predicate='within'`) → copy the polygon's `NatWalkInd` onto the edge. In code:
  ```python
  edges_with_score = gpd.sjoin(edge_midpoints, walkability_polygons, how='left', predicate='within')
  ```
- **Why it matters:** This is how every dataset gets attached to the routing graph. The `lighting_score`, `crime_score`, and `bike_buffer_score` recipes are all variations of "buffer the edge → spatial-join with points/lines → aggregate."

### Concept 4 — OSMnx walking graph (multi-directed graph)
- **Explanation:** OSMnx downloads OpenStreetMap into a **NetworkX MultiDiGraph**. **Nodes** are intersections (have `lat`/`lon`). **Edges** are street segments between two intersections; each has a `length` (meters), a `name` (street name), a `highway` (street class like `residential`/`primary`/`footway`), and sometimes `lit`, `sidewalk` tags. "Multi" means two intersections can have multiple edges between them (parallel lanes, service roads). "Di" means edges have direction (one-way streets).
- **Example:** Build it once and cache:
  ```python
  import osmnx as ox
  G = ox.graph_from_place("San Diego, CA", network_type="walk")
  ox.save_graphml(G, "san_diego.graphml")  # cache; loading from disk is much faster
  ```
- **Why it matters:** This graph is the *map* SafePath routes through. Every feature gets attached as an edge attribute on this graph. Every shortest-path call runs on this graph. Loop with `G.edges(keys=True, data=True)` so you don't collide on duplicate edges.

### Concept 5 — Buffer + spatial join recipe (the lighting score, fully worked)
- **Explanation:** "Count operational streetlights within 50 m of each edge." Done in 4 mechanical steps:
  ```python
  # 1. read both datasets
  lights = gpd.read_file("data/processed/streetlights/streetlights_processed.geojson")  # EPSG:4326
  edges = ox.graph_to_gdfs(G, nodes=False)                                              # EPSG:4326

  # 2. reproject to meters
  lights_3857 = lights.to_crs(3857)
  edges_3857 = edges.to_crs(3857)
  edges_3857["length_m"] = edges_3857.geometry.length  # length now in meters

  # 3. buffer each edge by 50 m
  edges_buf = edges_3857.assign(geometry=edges_3857.buffer(50))

  # 4. spatial-join + count
  joined = gpd.sjoin(edges_buf, lights_3857, how="left", predicate="contains")
  edges_3857["streetlight_count_50m"] = joined.groupby(level=0).size()
  ```
- **Why it matters:** This is the L1 feature from `docs/data/streetlights/FEATURE_CONTRACT.md`. The crime score and bike comfort score follow the same pattern with different geometries (points → buffer of 50 m for crime; lines → buffer of 15 m for bike lanes).

### Concept 6 — Weighted scoring → inverse-cost transformation
- **Explanation:** Two consecutive math steps:
  - **Score:** `safety_score = sum(w_i * feature_i)` where weights sum to 1 and each `feature_i ∈ [0, 1]` with 1 = best. Result `safety_score ∈ [0, 1]`.
  - **Cost:** `route_cost = length * (1 + 4 * (1 - safety_score))`. A perfect edge (`safety_score = 1`) costs 1 × length (just walk it). A worst edge (`safety_score = 0`) costs 5 × length (router will detour up to 5× the length to avoid it).
- **Example:** A 100 m edge with `safety_score = 0.6` has `route_cost = 100 * (1 + 4 * 0.4) = 100 * 2.6 = 260 m equivalent`. So the router treats it like a 260 m edge when minimizing safety-cost — it'll detour through it only if no alternative is shorter than 260 m.
- **Why it matters:** This single transformation lets a generic shortest-path algorithm (which only knows how to minimize sums of edge weights) produce a "safe" route. The `4` is a knob — tune it later if safest routes are always too long or always identical to fastest.

### Concept 7 — Three weights → three routes
- **Explanation:** `networkx.shortest_path(G, orig, dest, weight=...)` accepts a `weight` parameter that names the edge attribute to minimize. Run it three times with different weights:
  - `weight="length"` → fastest route (ignores safety)
  - `weight="route_cost"` → safest route (length × penalty)
  - `weight="balanced_cost"` → blend, where `balanced_cost = alpha * length + (1 - alpha) * route_cost` and `alpha ∈ [0, 1]` is a single knob (Ajay owns it; default 0.5)
- **Example:**
  ```python
  import networkx as nx
  fastest  = nx.shortest_path(G, orig, dest, weight="length")
  safest   = nx.shortest_path(G, orig, dest, weight="route_cost")
  balanced = nx.shortest_path(G, orig, dest, weight="balanced_cost")
  ```
- **Why it matters:** Same graph, same algorithm, three different routes. The user picks "fastest / safest / balanced" in the Streamlit UI and the backend just changes the `weight=` argument. Everything else — the per-segment explanation, the total distance, the length-weighted average safety score — falls out of the chosen route.

---

## Where to read more (links inside this repo)

- [`README.md`](../README.md) — project pitch + 3-min install
- [`docs/00_project_map.md`](00_project_map.md) — navigation guide + sprint timeline
- [`docs/01_data_sources.md`](01_data_sources.md) — every dataset, citation, owner
- [`docs/02_data_cleaning.md`](02_data_cleaning.md) — cleaning recipes + validation checklists
- [`docs/03_feature_engineering.md`](03_feature_engineering.md) — feature spec + recipes
- [`docs/04_scoring_methodology.md`](04_scoring_methodology.md) — weights + route cost + limitations
- [`docs/status.md`](status.md) — who owns what right now
- [`docs/data/streetlights/CLEANING_AND_VALIDATION.md`](data/streetlights/CLEANING_AND_VALIDATION.md) — exemplar validation report
- [`docs/data/streetlights/FEATURE_CONTRACT.md`](data/streetlights/FEATURE_CONTRACT.md) — L1–L5 lighting feature spec
- [`docs/data/ucsd_crime/00_NEXT_SESSION.md`](data/ucsd_crime/00_NEXT_SESSION.md) — UCSD workstream handoff
