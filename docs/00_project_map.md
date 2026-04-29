# Project map

Start here when you join the project, or any time you forget where something lives.

## What SafePath does

We recommend walking routes in San Diego that feel safer and more comfortable, not just the fastest. Users pick a start and end point, choose a preference (fastest, safest, balanced), and see a route with a plain explanation of why it scored that way.

## How the project flows

Read the docs in this order. Each step is a doc.

```
data sources        →  docs/01_data_sources.md
data cleaning       →  docs/02_data_cleaning.md
feature engineering →  docs/03_feature_engineering.md
scoring methodology →  docs/04_scoring_methodology.md
current status      →  docs/status.md
```

Plain English version:

1. We collect public datasets (crime, walkability, street lights, bike lanes, OpenStreetMap streets).
2. We clean each dataset so it loads and joins.
3. We attach features from those datasets to each street segment in the OSM walking network.
4. We turn the features into a single safety score per segment, then a route cost.
5. We pick three routes (fastest, safest, balanced) and explain why.

## Which doc do I read for my task?

| Your task this week | Read these |
| --- | --- |
| Cleaning street lights or bike lanes (Max) | `02_data_cleaning.md` |
| Feature engineering and initial scoring on sample routes (Ruan) | `03_feature_engineering.md`, `04_scoring_methodology.md` |
| Designing the weighted score for safety and convenience (Matthew) | `04_scoring_methodology.md` |
| Comparing how different weights change routes (AJ) | `04_scoring_methodology.md` |
| Anything else | `01_data_sources.md` first, then jump to the right doc above |

## Repo layout at a glance

```
SafePath/
├── README.md                  front door, points here
├── requirements.txt
├── .gitignore
├── data/                      local only, gitignored. See README data setup.
│   ├── raw/
│   └── processed/
├── notebooks/                 preprocessing notebooks live here
├── docs/                      you are here
│   ├── 00_project_map.md
│   ├── 01_data_sources.md
│   ├── 02_data_cleaning.md
│   ├── 03_feature_engineering.md
│   ├── 04_scoring_methodology.md
│   ├── status.md
│   ├── status/                older weekly snapshots, kept for history
│   └── references/            SDPD reference files (CSV/PDF)
├── src/                       planned, empty for now
└── app/                       planned, empty for now
```

## Where to ask, where to write

1. Quick question: Discord.
2. Final answers and instructions: this repo.
3. Large processed data files: team Google Drive (link in README).
4. Meeting brainstorming: Google Drive notes folder.

If a Google Doc starts to hold final project knowledge, port the short version into the right doc here.
