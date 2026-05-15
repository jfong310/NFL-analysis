# fantasy_nfl_model

## Project Purpose
`fantasy_nfl_model` is a public-data fantasy football analysis project. The long-term objective is to estimate probabilistic player outcomes and compare those projections against draft cost (ADP) to identify excess value.

## Current Status
This repository now implements:
- **Chunk 1**: scaffolding + data audit
- **Chunk 2**: fantasy scoring + season-level target construction

Still intentionally not included yet:
- ADP ingestion / draft value scoring
- ML model training
- advanced feature engineering

## Installation
```bash
pip install -r requirements.txt
```

## Run the Data Audit (Chunk 1)
```bash
python scripts/run_data_audit.py
python -m scripts.run_data_audit
```

## Run Scoring + Target Construction (Chunk 2)
```bash
python scripts/run_scoring_targets.py
python -m scripts.run_scoring_targets
```

### Custom seasons
```bash
python scripts/run_scoring_targets.py --start-season 2020 --end-season 2025
```

### Explicit local input file
```bash
python scripts/run_scoring_targets.py --input-path data/audit/samples/player_stats_weekly_sample.parquet
```

## Expected Outputs
- `data/processed/player_week_scored.parquet` (or CSV fallback)
- `data/processed/player_season_targets.parquet` (or CSV fallback)
- `data/audit/scoring_validation_report.md`

## Scoring Assumptions
Scoring formats implemented:
- `standard`
- `half_ppr`
- `ppr` (default)

Core assumptions:
- Passing: 0.04/yard, 4 per pass TD, -2 INT, +2 passing 2PT (if present)
- Rushing: 0.1/yard, 6 per rush TD, +2 rushing 2PT (if present)
- Receiving: 0/0.5/1 per reception by format, 0.1/yard, 6 per receiving TD, +2 receiving 2PT (if present)
- Fumbles lost: -2 (if present)
- Optional return/special teams/offensive FR TDs: +6 when present

Missing optional columns are treated as zero and documented in the validation report.

## Season-Target Construction Assumptions
- By default, season targets use **regular season only** (`season_type == "REG"` when available).
- Postseason rows are excluded from target totals unless `--include-postseason` is explicitly passed.
- `games_played` uses a usage-aware flag: fantasy points non-zero OR usage columns (attempts/carries/targets/receptions) > 0 OR snap columns > 0.
- `weeks_active` counts deduplicated player-week rows used in season aggregation.
- Duplicate player-week rows are detected and de-duplicated using a documented key strategy.
- Replacement-level baselines (configurable): QB12, RB24, WR36, TE12.

## Run Tests
```bash
pytest
```
