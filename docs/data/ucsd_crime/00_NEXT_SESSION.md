# UCSD Crime — next-session handoff

> **Read this first** if you are an agent (or a person) picking up the UCSD campus-crime workstream. It captures what's done, what's blocked, and exactly where to resume so the DAG doesn't drift.

**Workstream:** UCSD campus crime, used to feed the eventual `campus_incident_score` route-level feature (F10 in [`docs/03_feature_engineering.md`](../../03_feature_engineering.md)).
**Last session date:** 2026-04-30 → 2026-05-01.
**Reading time:** 3 minutes. Sister doc: [`docs/data/streetlights/00_WORKFLOW_PLAN.md`](../streetlights/00_WORKFLOW_PLAN.md) — same pattern, different dataset.

## 1. State of work

| Item | Status | Where |
| - | - | - |
| Annual Clery PDF | downloaded | [`data/raw/ucsd_police_logs/annualclery.pdf`](../../../data/raw/ucsd_police_logs/annualclery.pdf) — UCSD Annual Security & Fire Safety Report 2025 (Reissued 2026-02-26), 459 pp, 8.8 MB |
| Clery §XVI Crime Statistics tables (2022–2024) | extracted, validated, **all PASS** | [`data/processed/ucsd_clery/ucsd_clery_stats_2022_2024.csv`](../../../data/processed/ucsd_clery/ucsd_clery_stats_2022_2024.csv) — 66 rows, 22 offenses × 3 years × 5 Clery-geography buckets |
| Daily Crime & Fire Log (point-level data) | **NOT downloaded** | placeholder file at [`data/raw/ucsd_police_logs/logs_20260501.csv`](../../../data/raw/ucsd_police_logs/logs_20260501.csv) is **1 byte** — single newline, no header |
| UCSD location-string lookup table | **NOT created** | expected at `data/lookup/ucsd_location_strings_to_latlon_v0.csv` |
| UCSD campus polygon | **NOT chosen** | candidates: [SANGIS regional GIS](https://rdw.sandag.org/Account/gisdtview) `university_boundary` layer **OR** hand-built bbox `(-117.245, 32.867, -117.220, 32.892)` |
| `SOURCE_METADATA.yaml` for UCSD raw | missing | analogous to [`data/raw/streetlights/SOURCE_METADATA.yaml`](../../../data/raw/streetlights/SOURCE_METADATA.yaml) |

## 2. Agent execution log (last session)

Mirrors the per-phase agent table in [`docs/data/streetlights/00_WORKFLOW_PLAN.md`](../streetlights/00_WORKFLOW_PLAN.md). All agents below are role-instruction `.md` files — none are spawned as live sub-agents.

| Phase | Agent | Location | Output |
| - | - | - | - |
| 0 | `project-manager` | [awesome-claude-code-subagents/categories/08-business-product/project-manager.md](https://github.com/VoltAgent/awesome-claude-code-subagents/blob/main/categories/08-business-product/project-manager.md) | scope: UCSD crime → F10 |
| 0 | `agent-organizer` | 09-meta-orchestration | agent-set selection (this table) |
| 0 | `workflow-orchestrator` | 09-meta-orchestration | DAG and checkpoints |
| 0 | `context-manager` | 09-meta-orchestration | this doc |
| 1 | `search-specialist` | 10-research-analysis | located Clery PDF in `data/raw/ucsd_police_logs/` |
| 1 | `data-researcher` | 10-research-analysis | confirmed PDF is UCSD ASFSR 2025 Reissued 2026-02-26 |
| 2 | `data-engineer` | 05-data-ai | `pdftotext -layout -f 141 -l 160` → structured long CSV |
| 3 | `data-explorer` | ai-analyst-main/agents | inventory: 66 rows, 22 offenses, 6 categories, 15 nullable cells (by design) |
| 5 | `validation` | ai-analyst-main/agents | schema + year/category domain + 2 logical invariants → PASS |
| 5 | `source-tieout` | ai-analyst-main/agents | 5 independent spot-checks vs fresh `pdftotext` → 5/5 PASS |
| 4, 5 | `qa-expert` | 04-quality-security | 3 WARN caveats logged (see §3) |
| 6 | `business-analyst` | 08-business-product | decision: Clery = validator, daily log = point source (see §4) |
| 7 | `technical-writer` | 08-business-product | this doc |

## 3. Validation status of the Clery CSV — what consumers must respect

| Check | Status |
| - | - |
| Schema (10 columns, see §6) | PASS |
| Year domain ⊆ {2022, 2023, 2024} | PASS |
| `total ≥ 0` everywhere | PASS |
| `on_campus_total ≥ on_campus_student_housing` (housing is a subset) | PASS, all 60 applicable rows |
| `total = on_campus_total + non_campus + public_property` | PASS, all 60 applicable rows |
| Source tie-out (5 spot-checks vs PDF) | PASS, 5/5 |

**WARN caveats — preserve in any downstream code:**

1. **Cross-category double-count risk.** Criminal Offenses (e.g. Rape) and VAWA Offenses (e.g. Domestic Violence) may refer to the same incident. **Sum within a single `category` only — never across.**
2. **Aggregation grain.** Each row is annual × Clery-geography. **Cannot become a per-edge or per-coordinate feature.** Use as a polygon attribute or as a year-end validator.
3. **Revised counts.** `revised_2022` / `revised_2023` flags mean prior-year reports had different (usually lower) numbers. Always use the latest report.

## 4. Key decision — Clery vs daily log (do not re-litigate)

The Clery PDF gives **annual aggregates over 4 named geographies** ([34 CFR 668.46(a)](https://www.ecfr.gov/current/title-34/section-668.46#p-668.46(a))):

| Bucket | Geometry | Source for points? |
| - | - | - |
| On-Campus | university polygon | no, polygon-level only |
| On-Campus Student Housing | dorm sub-polygons | no |
| Non-Campus | scattered off-site polygons | no |
| Public Property | ~305 m (1000 ft) buffer along campus boundary | no |

**Decision (`business-analyst`, 2026-05-01):**
- `campus_incident_score` (F10) gets its **points** from the UCSD Daily Crime & Fire Log (the still-empty daily scrape file).
- The Clery CSV is the **upper-bound validator** for that scrape: e.g. *"daily-log Rape incidents in 2024 should be ≤ 35"* (the Clery 2024 total).
- **Do NOT** divide aggregate counts by polygon area to fake per-edge densities — incidents cluster, they don't spread uniformly.

## 5. Blockers (P0 first)

| Severity | Blocker | What unblocks it |
| - | - | - |
| **P0** | Daily Crime & Fire Log not scraped | populate `data/raw/ucsd_police_logs/logs_YYYYMMDD.csv` with header + rows from [https://www.ucsdpolice.com/policelog/index.html](https://www.ucsdpolice.com/policelog/index.html). Add `SOURCE_METADATA.yaml` matching the streetlight template. |
| **P0** | UCSD campus polygon source not chosen | pick SANGIS layer (preferred, authoritative) **OR** hand-built bbox (faster, crude). Document choice in `ASSUMPTIONS_LOG_v0` style note. |
| **P1** | Location-string → lat/lon lookup not built | create `data/lookup/ucsd_location_strings_to_latlon_v0.csv` mapping ~20–30 most common free-text locations (Geisel, Price Center, RIMAC, Sun God Lawn, named lots, named colleges) to coordinates. Per the v0 plan this handles 70–80% of incidents. |
| **P2** | No scrape script | when writing it, follow the same urllib-only / 250 ms politeness / 3-retry pattern as [`src/data/get_streetlights.py`](../../../src/data/get_streetlights.py). UCSD's site has no documented API, so politeness matters more. |

## 6. Canonical schema for the daily-log scrape (drafted, awaiting data)

When the scrape produces real data, `data-engineer` should standardize to this shape. **Do not invent fields.**

| Column | Type | Format / domain | From | Notes |
| - | - | - | - | - |
| `incident_id` | string | unique, stable across re-scrapes | composite of `date + case#` | primary key |
| `report_dt_utc` | timestamp | ISO 8601, UTC | "Date Reported" + "Time Reported" | log is local PT — convert to UTC |
| `occurred_dt_utc` | timestamp | ISO 8601, UTC, nullable | "Date Occurred" + "Time Occurred" | many calls list only the report time |
| `category` | string | controlled vocab from UCSD dispatch codes | "Incident Type" | TBD value-domain after first pull |
| `disposition_initial` | string | controlled vocab | "Disposition" | log is the **initial** disposition; final can change |
| `location_text` | string | free text | "Location" | NOT geocoded yet |
| `location_resolved` | enum | `geisel` / `price_center` / `rimac` / `sungod` / `lot_*` / `college_*` / `unknown` | derived from lookup table | drives `data_quality_flag` |
| `lat` | float, nullable | EPSG:4326 | derived from `location_resolved` | null when `unknown` |
| `lon` | float, nullable | EPSG:4326 | derived from `location_resolved` | null when `unknown` |
| `data_quality_flag` | enum | `ok` / `unresolved_location` / `parse_error` | derived | downstream filter |
| `scrape_dt_utc` | timestamp | ISO 8601, UTC | filename / wrapper | for snapshot lineage |

## 7. Clery CSV schema (the file that already exists)

`data/processed/ucsd_clery/ucsd_clery_stats_2022_2024.csv` — 66 rows, 10 columns:

| Column | Type | Note |
| - | - | - |
| `offense` | string | e.g. `Rape`, `Aggravated Assault`, `Stalking`, `Drug Abuse Arrests` |
| `category` | enum | `criminal` / `vawa` / `arrest` / `disciplinary` / `hate` / `unfounded` |
| `year` | int | 2022, 2023, 2024 |
| `on_campus_student_housing` | int (nullable on `hate`/`unfounded`) | Clery geography subset of on-campus |
| `on_campus_total` | int (nullable on `unfounded`) | includes housing |
| `non_campus` | int (nullable on `unfounded`) | Clery non-campus property |
| `public_property` | int (nullable on `unfounded`) | Clery public property buffer |
| `total` | int | row sum across the four geographies |
| `revised_flag` | string | `revised_2022` / `revised_2023` / `note_increase_escooter` / `note_transit_access` etc. — preserves the asterisk/cross footnotes |
| `source` | string | `UCSD ASFSR 2025 (Reissued 2026-02-26) §XVI pp.141-144` |

## 8. First action for the next session

If you are the next agent picking this up, here is the **exact** thing to do first — do not re-validate the CSV (it's done) and do not re-extract the PDF (it's done):

1. Check whether [`data/raw/ucsd_police_logs/logs_20260501.csv`](../../../data/raw/ucsd_police_logs/logs_20260501.csv) is still 1 byte. If yes → blocker P0 unchanged → ask user to run the scrape or paste a sample of real rows.
2. If file has real rows: invoke `data-engineer` to standardize to the schema in §6 of this doc. Then `validation` + `source-tieout` to check counts against this Clery CSV (the validator).
3. If user has chosen a UCSD campus polygon source: invoke `data-researcher` to fetch it, then `data-engineer` to write it to `data/processed/ucsd_campus/campus_polygon.geojson`. After that, F10 + F11 can be computed.
4. Update §1 of this doc with the new state. Append a row to §2 with the agents you used.

**Do not** add new agents, restructure the repo, or re-merge content from `docs/data-prep-handoff-v0` — that branch's deletable content was already absorbed into [`docs/01_data_sources.md`](../../01_data_sources.md) §5 and [`docs/03_feature_engineering.md`](../../03_feature_engineering.md). The UCSD planning content (U-section assumptions, F10/F11 spec) was intentionally not absorbed into main; it lives in that branch's git history if you need it.

## 9. Cross-references (clickable)

- [`docs/01_data_sources.md`](../../01_data_sources.md) — main dataset catalog (UCSD crime is **not** listed there yet; that's intentional, it's premature)
- [`docs/03_feature_engineering.md`](../../03_feature_engineering.md) — feature spec (F10/F11 not yet present in main; live in `docs/data-prep-handoff-v0` branch git history)
- [`docs/04_scoring_methodology.md`](../../04_scoring_methodology.md) — scoring formula (does not weight `campus_incident_score` yet)
- [`docs/data/streetlights/00_WORKFLOW_PLAN.md`](../streetlights/00_WORKFLOW_PLAN.md) — sister workstream, identical pattern
- [`docs/data/streetlights/CLEANING_AND_VALIDATION.md`](../streetlights/CLEANING_AND_VALIDATION.md) — exemplar for what a finished validation report looks like
- [UCSD Police daily log](https://www.ucsdpolice.com/policelog/index.html) — the scrape target
- [UCSD Clery report (2025)](https://police.ucsd.edu/clery/index.html) — source for the validated CSV
- [34 CFR 668.46(a)](https://www.ecfr.gov/current/title-34/section-668.46#p-668.46(a)) — Clery geography legal definitions
