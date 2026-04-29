# SafePath Data Preprocessing

This document explains how the processed SafePath data files were created and how teammates can validate them. It focuses on data cleaning, preprocessing decisions, and sanity checks, not route scoring.

For project setup, use `README.md`. For the planned scoring and routing design, use `docs/methodology.md`. For weekly progress, use `docs/status/`.

## Purpose of this document

SafePath uses processed data files instead of asking every teammate to rerun the raw data pipeline. This document explains what those files contain, how they were created, and how to check whether they are reasonable.

The goal is not just to say that the data loads. The goal is to make it possible for teammates to validate whether the cleaned data makes sense for the project.

## Processed outputs

The processed files should live in:

```text
data/processed/
```

Expected files:

| File | What it contains | Why SafePath needs it |
|---|---|---|
| `crime_final_gdf.gpkg` | Geocoded SDPD incident points | Used to estimate crime or incident risk near street edges |
| `walkability_final_gdf.gpkg` | San Diego block group polygons with `NatWalkInd` | Used to estimate walkability and pedestrian comfort near street edges |
| `geocode_cache.json` | Cached Nominatim geocoding results | Prevents rerunning thousands of slow geocoding requests |

The processed files are shared through the team Google Drive because they are too large or too slow to recreate casually.

## Crime data preprocessing

The crime preprocessing pipeline turns SDPD Calls for Service records into geocoded point data.

### Input

Raw source:

```text
SDPD Calls for Service CSV
```

Important raw fields may include:

- incident date or time
- call type
- disposition code
- priority level
- address or intersection

### Main cleaning steps

1. Load the SDPD Calls for Service data.
2. Filter to relevant disposition codes so the file focuses on incidents with some confirmed outcome, such as arrest, report taken, or officer action.
3. Keep call types that may reasonably affect pedestrian safety.
4. Standardize address or intersection strings before geocoding.
5. Geocode unique addresses with Nominatim instead of geocoding every row.
6. Save successful geocoding results to `geocode_cache.json`.
7. Join cached coordinates back to the filtered crime records.
8. Drop rows where geocoding failed or coordinates are unusable.
9. Convert the result into a GeoDataFrame with point geometry.
10. Save the final processed file as `crime_final_gdf.gpkg`.

### Why geocode unique addresses

Many calls can happen at the same address or intersection. Geocoding every row wastes time and may hit rate limits. Geocoding each unique address once is faster and easier to resume.

Nominatim is rate-limited, so the first full run may take hours. Do not delete `geocode_cache.json` unless the team intentionally wants to rebuild the cache.

## Crime data validation checklist

A teammate validating `crime_final_gdf.gpkg` should check the following.

### Basic file checks

- File loads without error using GeoPandas.
- A geometry column exists.
- The CRS is set.
- Rows have latitude and longitude or point geometry.
- There are no obvious empty columns that should contain key information.

### Location checks

- Points appear in or near San Diego when plotted.
- A small random sample of addresses lands near the expected location.
- There are no obvious points in another city, state, or ocean unless expected.
- Duplicate addresses reuse cached coordinates consistently.

### Filtering checks

- The kept disposition codes match the intended definition of confirmed or relevant incidents.
- Pedestrian-relevant call types are included.
- Clearly irrelevant call types are excluded.
- Priority values, if used, still have interpretable values after cleaning.

### Suggested quick validation code

```python
import geopandas as gpd

crime = gpd.read_file("data/processed/crime_final_gdf.gpkg")
print(crime.shape)
print(crime.crs)
print(crime.geometry.geom_type.value_counts())
crime.head()
```

Optional map check:

```python
crime.sample(500, random_state=42).explore()
```

## Walkability data preprocessing

The walkability preprocessing pipeline turns EPA walkability scores and Census block group boundaries into one spatial file.

### Inputs

Raw sources:

```text
EPA Smart Location Database / Walkability Index
Census TIGER block group shapefile
```

Important fields:

- block group ID
- `NatWalkInd`
- block group geometry

### Main cleaning steps

1. Load the EPA walkability data.
2. Filter the national dataset down to San Diego County block groups.
3. Load the Census TIGER block group shapefile.
4. Standardize block group IDs in both datasets.
5. Merge the EPA scores onto the Census block group polygons.
6. Check that `NatWalkInd` is present after the merge.
7. Convert the result into a GeoDataFrame with polygon geometry.
8. Save the final processed file as `walkability_final_gdf.gpkg`.

### Important ID issue

Block group IDs should be treated as strings, not floats.

If a block group ID loads as a number like this:

```text
6.073017e+10
```

it should be converted back into a zero-padded string before merging. Otherwise, the merge can silently fail or create missing scores.

## Walkability data validation checklist

A teammate validating `walkability_final_gdf.gpkg` should check the following.

### Basic file checks

- File loads without error using GeoPandas.
- A geometry column exists.
- The CRS is set.
- Geometry type is polygon or multipolygon.
- `NatWalkInd` exists.
- `NatWalkInd` values are in the expected 1 to 20 range.

### Merge checks

- Block group IDs look like full Census GEOID strings.
- Most or all San Diego block groups have a non-null `NatWalkInd` value.
- The number of rows is reasonable for San Diego County block groups.
- The merge did not create many duplicated block groups.

### Map checks

- Polygons render over San Diego County.
- There are no obvious missing holes caused by failed joins.
- High and low walkability values appear plausible after mapping.

### Suggested quick validation code

```python
import geopandas as gpd

walk = gpd.read_file("data/processed/walkability_final_gdf.gpkg")
print(walk.shape)
print(walk.crs)
print(walk.geometry.geom_type.value_counts())
print(walk["NatWalkInd"].describe())
walk.head()
```

Optional map check:

```python
walk.explore(column="NatWalkInd", legend=True)
```

## Coordinate systems

Coordinate systems matter because SafePath uses distance-based operations.

### Common CRS values

| CRS | Meaning | Use |
|---|---|---|
| `EPSG:4326` | latitude and longitude | Good for storing and mapping web coordinates |
| projected CRS, such as `EPSG:3857` | meter-based coordinate system | Needed for buffers and distance operations |

Do not create a 50 meter buffer while the data is still in raw latitude and longitude degrees. Project the data first, then buffer.

Example:

```python
crime_projected = crime.to_crs("EPSG:3857")
walk_projected = walk.to_crs("EPSG:3857")
```

## Validation before scoring

Before route scoring starts, the team should be able to answer these questions.

### Crime data

- How many rows were in the raw file?
- How many rows remain after disposition filtering?
- How many rows remain after call type filtering?
- How many unique addresses were geocoded?
- How many rows were dropped because geocoding failed?
- Do sampled points appear in the correct places?

### Walkability data

- How many San Diego block groups are in the final file?
- How many have missing `NatWalkInd`?
- Are all scores inside the expected range?
- Do polygons render correctly?
- Did the GEOID merge behave as expected?

### Recommended validation table

Add a small table to the repo or notebook after validation.

```md
| Check | Expected | Actual | Pass? | Notes |
|---|---:|---:|---|---|
| Crime file loads | yes |  |  |  |
| Crime rows with geometry | all final rows |  |  |  |
| Walkability file loads | yes |  |  |  |
| Missing NatWalkInd | near zero |  |  |  |
| Points/polygons map correctly | yes |  |  |  |
```

## Known preprocessing limitations

The processed files are useful for the next project step, but they are not perfect.

Known limitations:

- SDPD Calls for Service are not the same as all crimes that happened.
- Some incidents are underreported.
- Some calls may not represent actual danger after investigation.
- Geocoding can be imperfect, especially for intersections or ambiguous addresses.
- Nominatim may return approximate locations.
- Walkability is measured at the block group level, which may be too coarse for a specific street segment.
- `NatWalkInd` is a national relative score, not a San Diego-only score.
- The data may cover a limited time window, so sparse areas may look safer than they really are.

These limitations should be considered when designing the scoring formula.

## Optional: rerun preprocessing from raw data

Most teammates do not need this section. Use it only if the team wants to refresh the processed files.

### Raw data sources

**SDPD Calls for Service**

- Download the relevant year from the City of San Diego open data portal.
- Save it under `data/raw/`.

**EPA Walkability Index**

- Download the EPA Smart Location Database / Walkability Index file.
- Save it under `data/raw/`.

**Census TIGER Block Group Shapefile**

- Download the California 2020 block group shapefile.
- Unzip it into `data/raw/`.
- Keep all shapefile sibling files together, such as `.shp`, `.dbf`, `.prj`, and `.shx`.

### Expected raw folder shape

```text
data/raw/
  pd_calls_for_service_YYYY_datasd.csv
  EPA_SmartLocationDatabase_V3_Jan_2021_Final.csv
  tl_2020_06_bg/
    tl_2020_06_bg.dbf
    tl_2020_06_bg.prj
    tl_2020_06_bg.shp
    tl_2020_06_bg.shx
```

### Notebooks to run

Run these from the top only if refreshing the data:

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

Warning: crime geocoding can take hours on the first run because Nominatim is rate-limited. Keep the cache so the process can resume.

## What does not belong in this document

To keep this file focused:

- route scoring design belongs in `docs/methodology.md`
- weekly progress belongs in `docs/status/`
- project setup belongs in `README.md`
- meeting notes and brainstorming belong in the team Google Doc or weekly status files
