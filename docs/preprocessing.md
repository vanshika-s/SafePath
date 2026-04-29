# SafePath Data Preprocessing

## Purpose of this document

This document explains how the processed SafePath data files were created and how teammates can validate them.

It focuses on data cleaning, preprocessing decisions, and sanity checks.

It does **not** explain route scoring. For scoring and routing assumptions, use `docs/methodology.md`.

It does **not** explain the full backend-to-frontend flow. For that, use `docs/pipeline.md`.

---

## Processed outputs

SafePath uses these processed files:

```text
data/processed/
  crime_final_gdf.gpkg
  walkability_final_gdf.gpkg
  geocode_cache.json
```

### `crime_final_gdf.gpkg`

Contains geocoded SDPD incident points after filtering.

Expected geometry:

```text
Point geometry
```

Expected use:

```text
count nearby incidents around each street edge
```

Created by:

```text
notebooks/crime-df-preprocessing.ipynb
```

---

### `walkability_final_gdf.gpkg`

Contains San Diego Census block group polygons with EPA walkability scores.

Expected geometry:

```text
Polygon or MultiPolygon geometry
```

Expected key score column:

```text
NatWalkInd
```

Expected use:

```text
assign walkability score to each street edge based on midpoint location
```

Created by:

```text
notebooks/walkability-df-preprocessing.ipynb
```

---

### `geocode_cache.json`

Contains cached Nominatim geocoding results.

Expected use:

```text
avoid re-geocoding the same crime addresses every time
```

Important:

Do not delete this file unless the team intentionally wants to rerun geocoding from scratch.

---

## Crime data preprocessing

### Goal

Turn raw SDPD Calls for Service records into geocoded point data that can be mapped and spatially joined to street edges.

### Raw input

Raw source:

```text
SDPD Calls for Service
```

Important raw fields may include:

- date or timestamp
- call type
- disposition code
- priority
- address components
- hour of day

The exact columns may differ by year or export.

---

### Step 1: Load SDPD Calls for Service data

The preprocessing notebook loads the raw SDPD Calls for Service CSV.

Validation checks:

- File loads without error.
- Row count is recorded before filtering.
- Expected columns are present.

Example checks:

```python
df.shape
df.columns
df.head()
```

---

### Step 2: Filter to relevant incidents

The raw SDPD file includes many call types. Not all of them are useful for pedestrian safety.

The preprocessing should filter to:

- confirmed or actioned incidents, based on disposition codes
- call types that are reasonably relevant to walking safety

Examples of relevant categories may include:

- assault
- robbery
- weapons
- stalking or threats
- narcotics
- hazardous conditions
- burglary or in-progress incidents

Validation checks:

- Save or document the list of included call types.
- Save or document the list of included disposition codes.
- Check that obviously irrelevant call types are excluded.
- Check that important safety-related call types are included.

---

### Step 3: Build a geocodable address string

The SDPD dataset may store address pieces across multiple columns.

A full address string should be built before geocoding.

Example pattern:

```python
crimes_df["full_address"] = (
    crimes_df["address_num"].astype(str)
    + " "
    + crimes_df["address_dir"].fillna("")
    + " "
    + crimes_df["address_road"].fillna("")
    + ", San Diego, CA"
)
```

Validation checks:

- Inspect a random sample of `full_address`.
- Check for blank or malformed addresses.
- Check how intersections or block-level addresses are represented.

---

### Step 4: Geocode unique addresses with Nominatim

The crime data needs latitude and longitude before it can become spatial point data.

Use Nominatim through `geopy`.

Important rule:

```text
Geocode unique addresses, not every row.
```

The same address can appear many times. Geocoding unique addresses saves time and avoids unnecessary requests.

Nominatim rate limit:

```text
about 1 request per second
```

Use `RateLimiter` so the process does not overload the free service.

Example:

```python
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

geolocator = Nominatim(user_agent="safepath")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
```

Validation checks:

- Count unique addresses before geocoding.
- Record how many addresses geocoded successfully.
- Record how many failed.
- Spot check a sample of geocoded locations on a map.

---

### Step 5: Cache geocoding results

Save geocoding results so future runs do not start from zero.

Expected output:

```text
geocode_cache.json
```

Validation checks:

- Cache file exists.
- Cache contains successful results.
- Re-running the notebook uses the cache instead of geocoding every address again.

---

### Step 6: Drop failed geocodes

Rows with failed geocoding cannot be placed on a map.

Validation checks:

- Count rows before and after dropping failed geocodes.
- Check whether dropped rows are random or concentrated in certain call types or neighborhoods.
- Document if the failure rate is large.

---

### Step 7: Save final crime GeoPackage

Convert final crime records into a GeoDataFrame and save:

```text
data/processed/crime_final_gdf.gpkg
```

Expected geometry:

```text
Point
```

Example:

```python
import geopandas as gpd

crime_gdf = gpd.GeoDataFrame(
    crimes_df,
    geometry=gpd.points_from_xy(crimes_df.lng, crimes_df.lat),
    crs="EPSG:4326"
)

crime_gdf.to_file("data/processed/crime_final_gdf.gpkg", driver="GPKG")
```

---

## Crime data validation checklist

A teammate should be able to run these checks before using the file for scoring.

### Basic file checks

- [ ] `crime_final_gdf.gpkg` loads without error.
- [ ] Geometry column exists.
- [ ] CRS is set.
- [ ] Geometry type is point.
- [ ] Row count is reasonable.
- [ ] No final rows have missing latitude or longitude.

Example:

```python
import geopandas as gpd

crime_gdf = gpd.read_file("data/processed/crime_final_gdf.gpkg")

crime_gdf.shape
crime_gdf.crs
crime_gdf.geom_type.value_counts()
crime_gdf.isna().mean().sort_values(ascending=False).head(20)
```

### Location checks

- [ ] Points appear in or near San Diego.
- [ ] No points are obviously in the ocean, another state, or another country.
- [ ] A random sample of addresses matches the approximate mapped location.

Example:

```python
crime_gdf.explore()
```

### Filtering checks

- [ ] Included call types match the team's safety definition.
- [ ] Included disposition codes are documented.
- [ ] Irrelevant call types are not accidentally included.
- [ ] High-priority safety-related incidents are not accidentally excluded.

---

## Walkability data preprocessing

### Goal

Turn EPA walkability scores and Census TIGER boundaries into one spatial file with both:

```text
NatWalkInd score + block group polygon geometry
```

---

### Raw inputs

Raw source 1:

```text
EPA Smart Location Database / Walkability Index
```

Contains:

```text
NatWalkInd and related walkability variables
```

Raw source 2:

```text
Census TIGER block group shapefile
```

Contains:

```text
block group polygon geometry
```

---

### Step 1: Load EPA walkability CSV

The EPA file covers the whole United States.

Filter to San Diego County.

Example condition:

```python
walk_sd = walk_df[
    (walk_df["STATEFP"] == 6) &
    (walk_df["COUNTYFP"] == 73)
]
```

Validation checks:

- Filter keeps only San Diego County.
- `NatWalkInd` exists.
- `NatWalkInd` values are within the expected range.

---

### Step 2: Load Census TIGER block group shapefile

GeoPandas needs all shapefile sibling files in the same folder.

Keep these together:

```text
.shp
.dbf
.prj
.shx
.cpg
```

Example:

```python
import geopandas as gpd

bg_gdf = gpd.read_file("data/raw/tl_2020_06_bg/tl_2020_06_bg.shp")
```

Validation checks:

- Shapefile loads without error.
- Geometry column exists.
- Polygons render correctly.
- CRS is set.

---

### Step 3: Standardize block group IDs

The EPA file and the Census shapefile need a shared ID.

Common issue:

```text
GEOID20 may load as a float, such as 6.073017e+10
```

It should become a 12-character zero-padded string.

Example:

```python
walk_sd["GEOID20"] = (
    walk_sd["GEOID20"]
    .astype(int)
    .astype(str)
    .str.zfill(12)
)
```

The shapefile may use `GEOID`, so rename it:

```python
bg_gdf = bg_gdf.rename(columns={"GEOID": "GEOID20"})
```

Validation checks:

- ID columns have the same type.
- ID columns have the same length.
- IDs look like 12-character strings.
- Merge keys are not missing.

---

### Step 4: Merge walkability scores with polygons

Example:

```python
walk_gdf = bg_gdf.merge(
    walk_sd[["GEOID20", "NatWalkInd"]],
    on="GEOID20",
    how="inner"
)
```

Validation checks:

- Merged row count is reasonable.
- `NatWalkInd` is not mostly missing.
- Geometry is preserved after merge.
- Polygons cover San Diego block groups.

Expected approximate row count from prior notes:

```text
about 2,058 San Diego block groups
```

If the number is very different, investigate before using the file.

---

### Step 5: Save final walkability GeoPackage

Expected output:

```text
data/processed/walkability_final_gdf.gpkg
```

Example:

```python
walk_gdf.to_file("data/processed/walkability_final_gdf.gpkg", driver="GPKG")
```

---

## Walkability data validation checklist

A teammate should be able to run these checks before using the file for scoring.

### Basic file checks

- [ ] `walkability_final_gdf.gpkg` loads without error.
- [ ] Geometry column exists.
- [ ] CRS is set.
- [ ] Geometry type is polygon or multipolygon.
- [ ] `NatWalkInd` exists.
- [ ] `NatWalkInd` values are within the expected range.
- [ ] Row count is reasonable.

Example:

```python
walk_gdf = gpd.read_file("data/processed/walkability_final_gdf.gpkg")

walk_gdf.shape
walk_gdf.crs
walk_gdf.geom_type.value_counts()
walk_gdf["NatWalkInd"].describe()
walk_gdf.explore(column="NatWalkInd")
```

### Merge checks

- [ ] Block group IDs were standardized before merge.
- [ ] Merge did not create many missing scores.
- [ ] Merge did not duplicate block groups unexpectedly.
- [ ] Final polygons still cover San Diego.

---

## Coordinate systems

Coordinate systems are important because SafePath uses distance operations.

### Common CRS values

| CRS | Meaning | Used for |
|---|---|---|
| `EPSG:4326` | latitude and longitude in degrees | raw coordinates, web maps |
| `EPSG:3857` | projected coordinates in meters | buffers and distance operations |

### Rule

```text
Use EPSG:4326 for web display.
Use a projected CRS for distance calculations.
```

Before creating a 50 meter buffer, project to a meter-based CRS:

```python
crime_gdf_3857 = crime_gdf.to_crs("EPSG:3857")
edges_3857 = edges.to_crs("EPSG:3857")
```

Why:

```text
Buffering in degrees is not reliable.
Buffering in meters is meaningful.
```

---

## Optional: rerun preprocessing from raw data

Most teammates should not need this. Use the processed files from the shared drive.

Rerun preprocessing only if:

- the team wants to refresh to a newer SDPD file
- the current processed output is wrong
- the team changes filtering rules
- the team wants to reproduce the cleaning from scratch

### Raw sources

#### SDPD Calls for Service

Download from the City of San Diego open data portal.

Save under:

```text
data/raw/
```

#### EPA Walkability Index

Download the EPA Smart Location Database / Walkability Index file.

Save under:

```text
data/raw/
```

#### Census TIGER Block Group Shapefile

Download the California block group shapefile.

Keep all shapefile sibling files together.

---

### Run notebooks

Run:

```text
notebooks/crime-df-preprocessing.ipynb
notebooks/walkability-df-preprocessing.ipynb
```

Expected outputs:

```text
data/processed/crime_final_gdf.gpkg
data/processed/walkability_final_gdf.gpkg
data/processed/geocode_cache.json
```

Warning:

The crime geocoding step can take several hours because Nominatim is rate-limited.

---

## Known preprocessing limitations

### Geocoding can be imperfect

Nominatim may return approximate or incorrect locations, especially for intersections, incomplete addresses, or ambiguous street names.

### Failed geocodes are dropped

Dropping failed geocodes may bias the data if failures are concentrated in certain neighborhoods or address formats.

### SDPD Calls for Service are imperfect

The raw data does not capture every unsafe event. It also may include calls that do not become confirmed crimes.

### Walkability is coarse

Walkability is measured at the Census block group level, which may be too broad for street-level routing.

### Time coverage may be limited

If the processed crime file only covers a few months, some streets may look safer simply because the time window is short.

---

## Minimum validation before scoring

Before using the processed files for edge scoring, confirm:

- [ ] crime file loads
- [ ] walkability file loads
- [ ] both files have valid geometry
- [ ] both files have CRS set
- [ ] crime points appear in San Diego
- [ ] walkability polygons cover San Diego
- [ ] `NatWalkInd` exists and has reasonable values
- [ ] geocoded crime locations pass a small spot check
- [ ] team understands the main limitations
