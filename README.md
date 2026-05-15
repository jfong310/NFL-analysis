# fantasy_nfl_model

## Project Purpose
`fantasy_nfl_model` is a public-data fantasy football analysis project. The long-term objective is to estimate probabilistic player outcomes and compare those projections against draft cost (ADP) to identify excess value.

## Current Status
This repository currently implements **Chunk 1: scaffolding + data audit**.

Included now:
- Package/repository scaffolding
- Centralized path and season configuration
- Defensive nflverse (`nflreadpy`) ingestion wrappers
- Data-source audit pipeline with CSV/Markdown outputs
- Basic tests and audit notebook

Not included yet:
- ML modeling
- Fantasy scoring engine
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

## Run Tests
```bash
pytest
```

## Expected Outputs
After the audit script runs, you should see:
- `data/audit/source_inventory.csv`
- `data/audit/data_audit.md`
- Sample dataset extracts in `data/audit/samples/` (parquet preferred, CSV fallback)

## Data Source Notes
- Core data source is `nflverse` via `nflreadpy`.
- Loader wrappers are intentionally defensive because `nflreadpy` APIs can evolve by version.
- The audit records explicit success/failure for each dataset and does not fail the whole run if one dataset is unavailable.


## Chunk 2: Fantasy Scoring + Target Construction

Chunk 2 adds reliable fantasy scoring and season-level target construction (no ADP ingestion or ML modeling yet).

### Run Scoring/Target Construction
```bash
python scripts/run_scoring_targets.py
```

Module mode:
```bash
python -m scripts.run_scoring_targets
```

Custom seasons:
```bash
python scripts/run_scoring_targets.py --start-season 2020 --end-season 2025
```

Custom input path:
```bash
python scripts/run_scoring_targets.py --input-path data/audit/samples/player_stats_weekly_sample.parquet
```

### Outputs
- `data/processed/player_week_scored.parquet` (CSV fallback)
- `data/processed/player_season_targets.parquet` (CSV fallback)
- `data/audit/scoring_validation_report.md`

### Scoring Assumptions
- Standard / half-PPR / PPR generated each run.
- Passing: 0.04/yard, 4 pass TD, -2 INT, +2 pass 2PT.
- Rushing: 0.1/yard, 6 rush TD, +2 rush 2PT.
- Receiving: receptions (0, 0.5, 1), 0.1/yard, 6 rec TD, +2 rec 2PT.
- Fumbles lost: -2.
- Optional return/special teams/offensive FR TD columns are included when present.

### Season Target Assumptions
- Season targets default to regular season rows (`season_type == "REG"`) unless `--include-postseason` is passed.
- `games_played` counts weeks with non-zero fantasy points OR offensive usage (attempts/carries/targets/receptions/snaps), with row-count fallback when needed.
- Replacement baselines are rank-based defaults: QB12, RB24, WR36, TE12.
- This chunk intentionally excludes ADP ingestion and ML model training; those are future chunks.
