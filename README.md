# SafePath
SafePath is a route recommendation tool that prioritizes safety and comfort over speed, helping users, especially those who feel vulnerable, choose safer walking paths. It uses factors like lighting, sidewalks, traffic, nearby businesses, and crime data to suggest more visible and active routes, supporting safer and more informed travel decisions.


## Project structure

```
SafePath/
├── data/
│   ├── raw/          # Downloaded source files (not tracked in git — see Data Setup)
│   └── processed/    # Cleaned and merged outputs ready for modeling
├── notebooks/        # Exploratory analysis and sprint-by-sprint prototyping
├── src/              # Reusable Python modules imported by the app and notebooks
├── app/              # Streamlit frontend and map display logic
└── README.md
```

**`notebooks/`** — Where we explore and validate ideas. Each notebook maps to a sprint week. Messy and experimental by design; once logic is proven here it gets cleaned up and moved to `src/`.

**`src/`** — The core of the project. Clean, importable Python modules for data loading, safety scoring, and routing. Nothing Streamlit-specific lives here — just reusable logic that can be tested independently.

**`app/`** — Everything the user sees. `main.py` is the Streamlit entry point and stays thin by calling functions from `src/`. Map rendering and UI components are broken into separate files to keep things organized.

## Datasets

**San Diego Police Calls for Service** — City-level crime and incident reports logged by the SD Police Department. Each row is a call with a date, time, incident type, and coordinates. We use this to measure crime density across neighborhoods and flag high-risk areas along walking routes.

**U.S. Walkability Index** — A neighborhood-level walkability score published by the EPA, covering factors like street connectivity, proximity to transit, and land use mix. Filtered down to San Diego's block groups, this gives us a baseline measure of how pedestrian-friendly each area is.

**Census TIGER Block Group Shapefile (CA, 2020)** — Polygon boundary files for every Census block group in California. We merge these with the Walkability Index using a shared GEOID to give each neighborhood a geographic shape, which lets us assign scores to street edges in the routing algorithm.

## Data Setup
1. Download SD Crime data from: https://data.sandiego.gov/datasets/police-calls-for-service/
2. Download Walkability Index from: https://www.kaggle.com/datasets/stacey06/u-s-walkability-index
3. Download TIGER shapefile: https://www2.census.gov/geo/tiger/TIGER2020/BG/tl_2020_06_bg.zip
4. Place all files in data/raw/ before running any notebooks.