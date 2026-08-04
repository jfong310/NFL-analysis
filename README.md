# fantasy_nfl_model

## Project Purpose
`fantasy_nfl_model` is a public-data fantasy football analysis project. The long-term objective is to estimate probabilistic player outcomes and compare those projections against draft cost (ADP) to identify excess value.

## Current Status
**Chunks 1 and 2 are complete.** The accepted audit, scoring, and target pipeline covers 2016-2025.

Included now:
- Package/repository scaffolding
- Centralized path and season configuration
- Defensive nflverse (`nflreadpy`) ingestion wrappers
- Parquet raw-data cache with JSON provenance
- Canonical QB/RB/WR/TE player-week table built on normalized IDs
- Join cardinality, match-rate, schema, and duplicate-row guardrails
- Independently calculated standard, half-PPR, and PPR scoring
- Player-season targets, volatility, positional finishes, and replacement value
- Exact standard/PPR reconciliation against nflverse

Not included yet:
- ML modeling
- ADP ingestion/value scoring
- Advanced feature engineering

## Installation
```bash
pip install -r requirements.txt
```

## Run the Data Audit
```bash
python scripts/run_data_audit.py
```

Module mode is also supported:
```bash
python -m scripts.run_data_audit
```

## Run with Custom Seasons
```bash
python scripts/run_data_audit.py --start-season 2020 --end-season 2025
```


Cached pulls are reused by default. Force a fresh download when required:
```bash
python scripts/run_data_audit.py --refresh
```

## Run Tests
```bash
pytest
```

## Chunk 1 Outputs

- `data/audit/source_inventory.csv`
- `data/audit/data_audit.md`
- `data/audit/sample_player_week.parquet`
- `data/audit/player_id_join_report.csv`
- Sample dataset extracts in `data/audit/samples/` (parquet preferred, CSV fallback)
- Raw parquet caches and provenance records in `data/raw/`

## Data Source Notes
- Core data source is `nflverse` via `nflreadpy`.
- Loader wrappers are intentionally defensive because `nflreadpy` APIs can evolve by version.
- The audit records explicit success/failure for each dataset and does not fail the whole run if one dataset is unavailable.

- Source enrichment uses IDs and explicit join keys rather than player-name matching.
- Injury matches are expected to be sparse because healthy players have no injury row.
- Raw source pulls record the installed `nflreadpy` version.

## Chunk 2: Fantasy Scoring + Target Construction

Chunk 2 independently reconstructs fantasy scoring and creates regular-season player targets for 2016-2025.

### Run Scoring/Target Construction

```bash
python scripts/run_scoring_pipeline.py
```

The command accepts `--start-season`, `--end-season`, and `--refresh`.

### Outputs

- `data/processed/player_week_scored.parquet`
- `data/processed/player_season_targets.parquet`
- `data/audit/scoring_validation_report.md`

### Assumptions

- Standard, half-PPR, and PPR scores are generated every run.
- Standard and PPR calculations reconcile exactly with nflverse reference scores.
- Only offensive sack, rushing, and receiving fumbles lost receive the -2 penalty.
- Targets include regular-season QB, RB, WR, and TE player-weeks.
- Games played count scored weekly-stat rows.
- Replacement ranks default to QB13, RB37, WR49, and TE13.
- Replacement-adjusted points compare season totals with the replacement-ranked player's season total.
- ADP ingestion and ML modeling remain future chunks.
