# SafePath — ground truth (validator-led reconstruction)

> Companion to [`SAFEPATH_OVERVIEW.md`](SAFEPATH_OVERVIEW.md) (per-file deep dive).
> This file answers: **what is the project actually doing, given that some docs are wrong?**
> Generated 2026-05-01 by 4 agents. **Trust order: code > notebooks > docs.**

**Agent file load:** `workflow-orchestrator.md` ✓, `data-engineer.md` ✓, `data-analyst.md` ✓, `validator.md` **MISSING** — substituted `ai-analyst-main/agents/validation.md` (same role).

**Reading rule used throughout:** *Simple first, professional second.* Plain English, then the technical term you'd use in a meeting.

---

## 1. Actual pipeline (ground truth from code, not docs)

Reconstructed by `workflow-orchestrator` from the code that **actually runs**, not the code described in markdown.

```
INGEST            CLEAN                       FEATURE             SCORE         ROUTE
                                              (NOT YET RUN)
streetlights ────► clean_streetlights.py ────►                      ┌───── safety_score ──── route_cost
(ArcGIS)          ✓ done                                            │       weighted          length × penalty
                                                                    │       sum
SDPD CSV  ───────► crime-df-preprocessing.ipynb ───── attach to ────┤                                ↓
                  ✓ done                            ─► OSM walking  │                       networkx.shortest_path
EPA CSV ─────────► walkability-df-preprocessing.ipynb   graph G     │                            × 3 weights
+ TIGER zip       ✓ done                              (Ruhan, in    │                                ↓
                                                       progress)    │                          fastest / safest
Clery PDF ───────► (manual extraction this session) ── validator    │                            / balanced
                  ✓ done                              only          │                                ↓
                                                                    │                            Streamlit
UCSD daily log ──► ✗ EMPTY (1 byte, P0 blocker)                     │                            (Week 6)
                                                                    │
bike lanes  ─────► ✗ NOT STARTED                                    │
```

**What code actually exists** (verified by `data-engineer`):

| File | Reality | Doc claim it contradicts |
| - | - | - |
| `src/data/get_streetlights.py` | downloads streetlights, paged ArcGIS calls, stdlib only | matches docs ✓ |
| `src/data/clean_streetlights.py` | filters `STATUS=A` AND `MAPNG_STAT_CD ∈ {AB,OP}`; writes interim + processed | matches **except** `drawing_date` column is sourced from non-existent key (always null) — doc lists it as a real kept column |
| `notebooks/crime-df-preprocessing.ipynb` | filters SDPD, geocodes via Nominatim, writes `crime_final_gdf.gpkg` | matches docs ✓ |
| `notebooks/walkability-df-preprocessing.ipynb` | filters EPA to SD county, joins TIGER polygons | matches docs ✓ |
| **everything else in src/** | doesn't exist | docs reference scoring, routing, app modules — none committed yet |
| **`tests/`** | doesn't exist | sprint Week-7 plan calls for pytest tests — not started |
| **`app/`** | empty (`.gitkeep` only) | Streamlit UI planned for Week 6 |

**The real status: only the cleaning layer exists in code.** Feature engineering, scoring, routing, and the Streamlit app are all documented as if they exist but currently live only in markdown. Notebooks for crime + walkability are real; everything past that is paper.

---

## 2. What each teammate likely worked on

Inferred by `workflow-orchestrator` from git log + doc owners + meeting minutes.

| Person | Role on paper | What you can actually verify they did |
| - | - | - |
| **Vanshika** | project lead | created the repo, owns the design doc, ran the GitHub workshop |
| **Matthew** | scoring weights + crime/walkability cleaning | crime + walkability notebooks committed and produce the two `.gpkg` files; weight design is in-progress per status doc but **no code commit yet** |
| **Max** (you) | streetlights + bike lanes + UCSD crime | streetlight downloader + cleaner committed (real); Clery aggregates extracted this session (real); bike lanes not started; UCSD daily log not started |
| **Ruhan** | feature engineering + initial scoring on sample routes | **no committed code yet** — the OSMnx graph wiring lives only in `03_feature_engineering.md` recipes, not in any `.py` or `.ipynb` |
| **Ajay** | weight comparison | blocked on Matthew; **no committed code yet** |

**Reality check by `data-analyst`:** the team is at the end of Week 4 / start of Week 5 per status.md. Per the design doc's sprint timeline, Week 5 is *"Move proven scoring and routing logic from notebooks into `src/` Python files."* That implies scoring + routing already work in notebooks. **They don't.** No notebook builds an OSMnx graph or computes a score. The Week-5 goal as stated is impossible — there's nothing in notebooks to lift into `src/` yet.

---

## 3. Where confusion or contradictions exist (validator pass)

Severity = how badly it would mislead a reader.

### HIGH — would cause wrong work

- **HIGH:** `clean_streetlights.py:102` reads `props.get("DRAWING_DATE")` — that field doesn't exist in the source. The processed file's `drawing_date` column is always `None`. **Simple version:** the script is asking the data for a column called "DRAWING_DATE" but the data only has "DRAWING_NO". Result: empty column. **Professional:** column-name mismatch between consumer (`clean_streetlights.py`) and source schema (ArcGIS layer descriptor); benignly null, but downstream code that filters on `drawing_date IS NOT NULL` would silently drop every row.
- **HIGH:** Sprint timeline says "Week 5 = move scoring/routing from notebooks to `src/`." There is no notebook with scoring or routing logic. Whoever picks up Week 5 will look for code that isn't there.
- **HIGH:** `docs/01_data_sources.md` (table row 7 added this session) says UCSD Clery is "done as validator only" — true for the aggregate CSV, but readers may interpret "done" to mean UCSD crime is ready as a feature input. It is not — the daily log is empty. The "Blocked" section in `status.md` says so, but the data-sources table is the more visible doc.

### MEDIUM — would slow you down but not produce wrong outputs

- **MEDIUM:** Cross-doc references to `docs/data/streetlights/CLEANING_AND_VALIDATION.md` and `docs/data/streetlights/FEATURE_CONTRACT.md` exist in `02_data_cleaning.md` and `03_feature_engineering.md`. Those target files are in your working tree but `.gitignore`'s `/data/` rule means they don't push unless `git add -f`. Right now: they're in your working tree, not on GitHub. A teammate cloning the repo will hit broken links.
- **MEDIUM:** `04_scoring_methodology.md` shows weights `w_crime, w_walk, w_light, w_bike, w_road` — five weights summing to 1. F10 (`campus_incident_score`) and F11 (`is_on_ucsd_campus`) exist as proposed features in the v0 handoff branch but **have no weight slot** in the scoring formula. Either F10 is excluded (then drop it from feature plans) or the formula is wrong (then add a 6th weight).
- **MEDIUM:** UCSD daily log placeholder file is `logs_20260501.csv` — date-stamped *future* (today), but contains no data. Could mislead a teammate into thinking a scrape ran on May 1 and failed silently.

### LOW — cosmetic / interpretation

- **LOW:** Design doc says "Team Size: 4 students." Repo has 5 (Matthew, Max, Ruhan, Ajay, Vanshika). Usually means "4 working students under Vanshika as lead." Not a bug, but new readers wonder.
- **LOW:** Some docs use `Ruhan`/`Ajay` (correct per meeting minutes), others used `Ruan`/`AJ` (fixed this session). If you find any old branch with these still — known drift.
- **LOW:** `04_scoring_methodology.md` has `crime_score_day if daytime else crime_score_night`. "Daytime" is defined nowhere in code. Sprint open question #1 in status.md asks the team to decide. Currently both columns are computed but only one is used per request — fine, but document the daytime cutoff before scoring runs.

### Missing pieces (validator's "things that should exist but don't")

| Missing | Should exist because |
| - | - |
| `data/lookup/ucsd_location_strings_to_latlon_v0.csv` | required to geocode UCSD daily-log free-text locations |
| UCSD campus polygon file | required for L4 (`lighting_data_quality_flag`) and F11 (`is_on_ucsd_campus`) |
| Bike lanes raw download | Max's open task |
| Bike lanes cleaning script | downstream of above |
| Any feature-engineering code | Ruhan's task; lives only as recipes in markdown |
| Any scoring code | Matthew's task; lives only as a formula in markdown |
| Any routing code | Ruhan's task; lives only as a sentence in markdown |
| `app/streamlit_app.py` (or similar) | Week-6 deliverable |
| `tests/` | Week-7 deliverable |
| `requirements.txt` lock | exists at root (`requirements.txt`) but not pinned versions |

---

## 4. What's reliable vs questionable

`data-analyst` ratings.

### Reliable (trust this) — code or data you can verify

- The streetlight raw → processed pipeline (1 download script + 1 cleaning script + 4 validation reports). Tie-out arithmetic holds; 5/5 source spot-checks PASS.
- The Clery aggregate CSV (this session). 5/5 spot-checks vs PDF; all logical invariants PASS.
- The crime + walkability `.gpkg` files (cited in docs, in team Drive, produced by committed notebooks). Not re-verified this session, but the notebook code exists and the doc claims match the design doc and sprint timeline.
- The 7 root markdown docs **as of after this session**: conflict markers resolved, names normalized, streetlight + bike + Clery merges applied, hyperlinks consistent.

### Questionable (verify before relying on)

- **Any claim about scoring or routing.** No code exists. The formula in `04_scoring_methodology.md` is a plan, not an implementation.
- **Any claim about features attached to OSM edges.** No code exists. The recipes in `03_feature_engineering.md` are pseudocode.
- **The `drawing_date` column** in processed streetlights — always null, documented bug.
- **`bike_buffer_score` proposal** (F6/F7/F8). Spec is internally consistent but unverified against real bike-lane data (which doesn't exist in repo).
- **`campus_incident_score` (F10) feasibility.** Cannot be computed without daily-log scrape + lookup table + campus polygon. Three blockers.

### Untrustworthy (don't rely on)

- The deleted `docs/data-prep/handoff_v0/` folder's content. It was the v0 plan, partially superseded by reality (UCSD interior was assumed empty — actual = 228 lights; `MAPNG_STAT_CD` was assumed long-form — actual = 2-letter codes). What was salvageable was merged to main this session; the rest is preserved only in branch git history.
- Any claim that "streetlights are not started" or "owner: Max | not started" anywhere in the repo. That was true 2026-04-29; it's wrong as of 2026-04-30. All such instances should have been fixed this session, but check before quoting.
- `00_NEXT_SESSION.md` §6 says daily-log raw schema is "drafted, no fields invented" — true, but it's a *draft* against an unreached endpoint. Real UCSD log fields will probably differ; treat the schema as the validation target, not a guarantee.

---

## 5. Where to read more (real, in-repo)

- [`docs/SAFEPATH_OVERVIEW.md`](SAFEPATH_OVERVIEW.md) — per-file deep dive (this file's companion)
- [`docs/data/ucsd_crime/00_NEXT_SESSION.md`](data/ucsd_crime/00_NEXT_SESSION.md) — UCSD workstream handoff
- [`docs/00_project_map.md`](00_project_map.md) — sprint timeline
- [`docs/status.md`](status.md) — current owners + blockers (last updated 2026-05-01)
- [`docs/data/streetlights/CLEANING_AND_VALIDATION.md`](data/streetlights/CLEANING_AND_VALIDATION.md) — the only fully-realized validation report in the repo (use as template)
