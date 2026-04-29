# Streetlights data note

This note explains the streetlight dataset added as a proposed nighttime visibility signal for SafePath.

## Why this helps SafePath

Crime and walkability are useful, but they do not fully capture whether a route feels visible or comfortable at night. Streetlights add a practical safety and comfort signal for users walking after dark.

This matters for San Diego because some areas are car-dependent and can become quiet after businesses close. A route can be short and low-crime but still feel uncomfortable if it is poorly lit or isolated.

## Files and folders

We are testing City of San Diego streetlight locations as a future nighttime visibility signal. This helps SafePath move beyond crime and walkability by asking whether a route may feel visible and comfortable after dark.


The preprocessing notebook is:

```text
notebooks/streetlights-preprocessing.ipynb
```

It creates local data files:

```text
data/raw/streetlights_sandiego_raw.geojson
data/processed/streetlights_clean_all.gpkg
data/processed/streetlights_clean.gpkg
data/processed/streetlights_clean.csv
data/processed/streetlights_clean_3857.gpkg
```

It also creates:

```text
docs/streetlights_quality_report.md
```

## What each format is for

- `.geojson` is good for raw downloads and quick inspection.
- `.gpkg` is better for cleaned geospatial data that GeoPandas will read later.
- `.csv` is only for quick human checking because it does not preserve geometry as a real geospatial object.

## How this integrates later

For each street segment, draw a 30m or 50m buffer and count nearby usable streetlights.

Possible edge feature:

```text
streetlight_count_50m
```

Possible first-pass score(????):

```text
lighting_score = min(streetlight_count_50m / 3, 1)
```

This can be combined with crime score and walkability score in the route cost function.

## Limitation

A streetlight point means a city asset exists at that location. It does not guarantee the light is currently working, bright enough, or that every user would feel safe there. Treat this as a nighttime visibility proxy, not a complete safety measure.
