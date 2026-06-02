# Streetlight CLEANING_AND_VALIDATION

> **Status (2026-04-30):** Cleaning ran. Tie-out and validation **all PASS**, zero FAIL. Real numbers below — placeholders are gone.

The cleaning + validation logic ran as a one-shot Python script (no notebook committed). It's reproducible from this doc: load raw GeoJSON → filter → write interim and processed → re-read and verify metrics. The five validation helper modules from `ai-analyst-main/helpers/` (`structural_validator`, `logical_validator`, `deep_profiler`, `tieout_helpers`, `data_helpers`) define the rubric.

## 1. Cleaning checklist (raw → interim → processed)

| # | What | Rationale | done_at |
| - | - | - | - |
| 1 | Load raw GeoJSON; assert CRS hint = WGS84; assert row count > 0 | catch a bad download early | 2026-04-30 |
| 2 | Standardize column names to snake_case for the columns scoring code reads (`sap_obj_nr`, `status`, `mapng_stat_cd`, `drawing_date`); originals kept in interim | downstream code is easier to read | 2026-04-30 |
| 3 | Drop rows where geometry is null OR coords are outside SD bbox `(-117.4, 32.4, -116.8, 33.2)` | a streetlight without a usable location can't help with route scoring | 2026-04-30 (no rows dropped — 0 nulls, all 56,049 in bbox) |
| 4 | Flag (do not drop) rows with duplicate `sap_obj_nr` via column `dup_sapobjnr_flag` (0/1) | duplicates may be paired SAP records, not asset duplicates | 2026-04-30 (0 duplicates flagged — every non-null `sap_obj_nr` is unique) |
| 5 | Filter active set: `status == "A"` AND `mapng_stat_cd ∈ {"AB", "OP"}` (the actual codes, not the long-form strings — descriptor confirmed `AB`=AS BUILT, `OP`=OPERATIONAL) | working "operational lights" set | 2026-04-30 (kept 55,506 of 56,049) |
| 6 | Save interim: `data/interim/streetlights/streetlights_active_wgs84.geojson` | preserves raw separately, keeps all original fields | 2026-04-30 (55.6 MB) |
| 7 | Drop columns not used by feature engineering. Keep: `sap_obj_nr`, `status`, `mapng_stat_cd`, `drawing_date`, `dup_sapobjnr_flag`, `data_quality_flag`, geometry | smaller, faster | 2026-04-30 |
| 8 | Add `data_quality_flag`: `ok` for clean rows. (`dup_kept` and `bbox_clipped` reserved for future re-runs; not needed in this snapshot.) | downstream consumers can filter | 2026-04-30 (all 55,506 rows = `ok`) |
| 9 | Save processed: `data/processed/streetlights/streetlights_processed.geojson` | feeds feature engineering | 2026-04-30 (15.3 MB) |

What this step does **not** do: buffering, reprojecting to `EPSG:3857`, joining to OSM. Those happen in feature engineering.

## 2. Tie-out (raw vs processed agreement)

Two independent reads of the data confirm cleaning didn't lose or invent rows. Patterned on `helpers/tieout_helpers.py`.

| Metric | Raw | Filtered out | Processed | Tie-out (raw − filtered = processed) | Status |
| - | - | - | - | - | - |
| Row count | 56,049 | 543 | 55,506 | 56,049 − 543 = 55,506 ✓ | **PASS** |
| Distinct `sap_obj_nr` | 56,048 (1 null) | 543 (all `STATUS == "I"`) | 55,506 | matches | **PASS** |
| Null geometry rows | 0 | 0 | 0 | n/a | **PASS** |
| Lon mean | −117.136782 | (filtered subset) | −117.136815 | within filter-induced drift | **PASS** |
| Lat mean | 32.794092 | (filtered subset) | 32.794312 | within filter-induced drift | **PASS** |
| `STATUS == "A"` count | 55,506 | 0 | 55,506 | exact | **PASS** |
| `MAPNG_STAT_CD` values in processed | n/a | n/a | `{AB: 55,409; OP: 97}` | matches expected filter | **PASS** |

The lon/lat means drift slightly between raw and processed because the 543 filtered-out `STATUS == "I"` rows are not uniformly distributed. That's expected and not a tie-out failure. The strict tie-out rule — "raw rows that pass the filter" should equal "processed rows" — holds exactly: 55,506 = 55,506.

**Overall tie-out: PASS.**

## 3. Validation

Layer 1 (structural) + Layer 2 (logical) + business-rule checks.

### 3.1 Structural

| Check | Rule | Observed | Status |
| - | - | - | - |
| Schema present | columns include `sap_obj_nr`, `status`, `mapng_stat_cd`, `geometry` | present | **PASS** |
| Primary key | `sap_obj_nr` unique among non-null rows | 56,048 distinct values across 56,048 non-null rows | **PASS** |
| Completeness — `status` (raw) | null rate ≤ 1% | 0% | **PASS** |
| Completeness — `mapng_stat_cd` (raw) | null rate ≤ 1% | 0% | **PASS** |
| Completeness — `geometry` (processed) | null rate = 0 | 0 | **PASS** |
| Value domain — `status` | values ⊆ `{A, I, W}` | `{A, I}` (no `W` this snapshot) | **PASS** |
| Value domain — `mapng_stat_cd` | values ⊆ descriptor codes `{AB, AN, OP, RM, NM, PR}` | `{AB, AN, OP, RM}` | **PASS** |
| Row count | > 1,000 | 56,049 raw / 55,506 processed | **PASS** |

### 3.2 Logical

| Check | Rule | Observed | Status |
| - | - | - | - |
| Coordinate plausibility | every row: lon ∈ [-117.4, -116.8], lat ∈ [32.4, 33.2] | all 56,049 rows inside | **PASS** |
| Subset relation | every processed row has a matching `sap_obj_nr` in raw | by construction (filter only) | **PASS** |
| Active filter held | every processed row has `status == "A"` and `mapng_stat_cd ∈ {"AB","OP"}` | 100% | **PASS** |
| Duplicate flag honored | `dup_sapobjnr_flag == 1` iff `sap_obj_nr` repeats | flag set on 0 rows; 0 actual duplicates → consistent | **PASS** |
| `MAPNG_STAT_CD` rows that ARE active but mapping not in {AB,OP} | should be 0 (otherwise filter loses real lights) | 0 | **PASS** |

### 3.3 Business rules

| Check | Rule | Observed | Status |
| - | - | - | - |
| UCSD perimeter coverage | active count inside UCSD perimeter strip (bbox `−117.260..−117.205, 32.855..32.905`) ≥ 100 | 1,194 lights | **PASS** |
| UCSD interior coverage | active count inside UCSD interior bbox (`−117.245..−117.220, 32.867..32.892`) is documented | 229 lights — **higher than expected**; assumption A-3 was too pessimistic. The neutral fallback for L4 is still recommended because coverage is uneven, not because it's zero. | **PASS (with note)** |
| Density ordering | downtown SD cell has higher active density per km² than a sparse residential cell | not yet computed (needs OSM grid; doesn't block source-data sign-off) | DEFERRED |
| Feature feasibility | `streetlight_count_50m` returns plausible non-zero values for 3 hand-picked OSM walking edges | not yet computed (depends on OSM walking graph) | DEFERRED to feature engineering |

## 4. PASS / WARN / FAIL criteria

- **PASS** — check ran, condition holds.
- **WARN** — check ran, condition is borderline. Document the borderline reason in a one-sentence note.
- **FAIL** — check ran, condition violated. **Stop and fix.**
- **DEFERRED** — check belongs to a later phase (feature engineering against OSM edges).

A processed file is "ready for feature engineering" when **all** of these hold:
1. Zero FAILs in §2 (tie-out) and §3 (validation). ✓ holds.
2. Every check is PASS, WARN, or DEFERRED (no PENDING). ✓ holds.
3. A teammate other than the runner has eyeballed the lat/lon distribution at least once.

## 5. Real results (one-page summary)

| Item | Value |
| - | - |
| Snapshot date | 2026-04-30 |
| Raw row count | 56,049 |
| Processed row count | 55,506 |
| Filtered out | 543 (all `STATUS == "I"`; 0 dropped for null geometry; 0 dropped for out-of-bbox) |
| `STATUS` value-counts (raw) | `A: 55,506`; `I: 543` |
| `MAPNG_STAT_CD` value-counts (raw) | `AB: 55,409`; `RM: 465`; `OP: 97`; `AN: 78` |
| `MAPNG_STAT_CD` value-counts (processed) | `AB: 55,409`; `OP: 97` |
| Lon range | `−117.281581 .. −116.927717` |
| Lat range | `32.541784 .. 33.112032` |
| Lon mean (raw / processed) | `−117.136782 / −117.136815` |
| Lat mean (raw / processed) | `32.794092 / 32.794312` |
| Null geometry | 0 |
| `SAPOBJNR` duplicates | 0 (one null `SAPOBJNR` row was a `STATUS == "I"` and got filtered) |
| Active count in UCSD interior bbox | 229 |
| Active count in UCSD perimeter strip | 1,194 |
| 100%-null fields (ignored downstream) | `DRAWING_NO`, `EVARI_POLE_NO`, `NOTES`, `POLE_HEIGHT_FT`, `SERIES_CIRCUIT_NAME`, `SG_FLOC`, `SG_INT_FLOC`, `SVC_PT_LOC` |
| Mostly-empty fields (do not rely on) | `WHERE_INSTALLED` (96% null), `SDGE_WORK_ORDER_NO` (97% null), `created_*` (93% null), `last_edited_*` (69% null) |
| **Overall status** | **PASS** |

### Notes / surprises

- The original assumption A-3 ("UCSD campus interior is uncovered by the City streetlight layer") was wrong as stated. There are 229 city-maintained lights inside the UCSD interior bbox in this snapshot. The neutral-fallback rule for L4 should still apply, because coverage is **uneven** rather than zero — but the rationale needs an update in the upstream `ASSUMPTIONS_LOG_v0.md`.
- `WHERE_INSTALLED` is 96% null. Earlier docs treated it as a primary descriptive field. The actual human-readable location field is `LOC_DESC` (99.94% populated).
- The `MAPNG_STAT_CD` codes are 2-letter abbreviations (`AB`, `OP`, `RM`, `AN`), not the long forms (`AS BUILT`, `OPERATIONAL`). The filter uses the codes.
- One row in the raw file has a null `SAPOBJNR`. It was a `STATUS == "I"` row, so it dropped out at step 5 and didn't reach the processed file. We did not write a special rule for null IDs in v0; if a future snapshot has more, the dedup logic will need to handle them.
