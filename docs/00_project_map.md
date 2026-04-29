# 00. Project map

> **TL;DR.** SafePath turns public datasets (crime, walkability, lights, bike lanes, OpenStreetMap streets) into a per segment safety score, then picks three routes (fastest, safest, balanced) and explains why. This file tells you which doc to read for your task.

## What SafePath does, in 3 lines

1. User enters a **start** and a **destination** in San Diego.
2. SafePath returns **3 routes**: fastest, safest, balanced.
3. Each route has a **plain English explanation** of why it scored that way.

## The 5 step project flow

Read each step in order. Every step has its own doc.

```
data sources           →   01_data_sources.md
data cleaning          →   02_data_cleaning.md
feature engineering    →   03_feature_engineering.md
scoring methodology    →   04_scoring_methodology.md
current team status    →   status.md
```

Plain English version:

| Step | Question it answers | Doc |
| - | - | - |
| 1 | What public datasets do we use and why? | [`01_data_sources.md`](01_data_sources.md) |
| 2 | How do we clean each dataset so it loads and joins? | [`02_data_cleaning.md`](02_data_cleaning.md) |
| 3 | How do we attach features to OSM street edges? | [`03_feature_engineering.md`](03_feature_engineering.md) |
| 4 | How do we score edges and pick routes? | [`04_scoring_methodology.md`](04_scoring_methodology.md) |
| 5 | Who is doing what right now? | [`status.md`](status.md) |

## Pick the right doc for your task

| Your task | Read these |
| - | - |
| Cleaning street lights or bike lanes (Max) | [`02_data_cleaning.md`](02_data_cleaning.md) |
| Feature engineering and initial scoring on sample routes (Ruan) | [`03_feature_engineering.md`](03_feature_engineering.md), [`04_scoring_methodology.md`](04_scoring_methodology.md) |
| Designing the weighted score for safety and convenience (Matthew) | [`04_scoring_methodology.md`](04_scoring_methodology.md) |
| Comparing how different weights change routes (AJ) | [`04_scoring_methodology.md`](04_scoring_methodology.md) |
| New teammate, no specific task yet | [`01_data_sources.md`](01_data_sources.md), then [`status.md`](status.md) |

## Where things live

| Type of thing | Lives in |
| - | - |
| Final code, instructions, and project knowledge | this GitHub repo |
| Large processed data files | team [Google Drive](https://drive.google.com/drive/folders/1DSxQlvn6lq-D_tax9uDd42b5rNIIyQQ8?usp=sharing) |
| Quick chat | Discord |
| Meeting notes and brainstorming | team Google Drive notes folder |
| GitHub crash course materials | [GitHub workshop slides](https://docs.google.com/presentation/d/1WPHBVzyirhDXo6mF61rogD_oO6OWuwoV/edit?slide=id.p1#slide=id.p1) |

If a Google Doc starts holding final project knowledge, port the short version into the right doc here.

## Sprint timeline (from the [original design doc](https://docs.google.com/document/d/1gufXZGHToZtFlsREL3u_rizqxXCKs3DR3LbKhO05fSc/edit?usp=sharing))

| Week | Goal |
| - | - |
| 1 | Research, setup, define safety features |
| 2 | Filter and clean crime + walkability data to San Diego |
| 3 | Design route scoring (weighted scores per neighborhood) |
| 4 | Prototype routing engine, generate route alternatives |
| 5 | Move scoring + routing logic out of notebooks into reusable Python modules. Let users prioritize speed, safety, or balance |
| 6 | Build map based web app (Streamlit) |
| 7 | Write unit tests, validate routes across neighborhoods |
| 8 | Deploy, prepare demo + final docs |

We are in Week 4 → Week 5 transition. See [`status.md`](status.md).

## Repo at a glance

```
SafePath/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/
│   ├── crime-df-preprocessing.ipynb
│   └── walkability-df-preprocessing.ipynb
├── docs/                       you are here
│   ├── 00_project_map.md
│   ├── 01_data_sources.md
│   ├── 02_data_cleaning.md
│   ├── 03_feature_engineering.md
│   ├── 04_scoring_methodology.md
│   ├── status.md
│   ├── status/                 older weekly snapshots
│   └── references/             SDPD code books (CSV/PDF)
├── src/                        planned, empty for now
└── app/                        planned, empty for now
```
