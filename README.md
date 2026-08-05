# fantasy_nfl_model

## Project Purpose
`fantasy_nfl_model` is a public-data fantasy football analysis project. The long-term objective is to estimate probabilistic player outcomes and compare those projections against draft cost (ADP) to identify excess value.

## Current Status
**Chunks 1 through 4 are complete.** The pipeline covers 2016-2025 and produces leakage-safe 2026 point and quantile projections.

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
- Leakage-safe production, usage, volatility, availability, profile, and team-context features
- Walk-forward random-forest models for points, PPG, and games played
- Gradient-boosted 10th/50th/90th percentile season projections

Not included yet:
- ADP ingestion/value scoring

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
- ADP ingestion and market-value modeling remain future chunks.


## Chunk 3: Leakage-Safe Feature Engineering

Chunk 3 creates one row per player and prediction season using data through the prior season only.

### Run Feature Engineering

```bash
python scripts/run_feature_pipeline.py
```

The command accepts `--start-season`, `--end-season`, and `--refresh`.

### Outputs

- `data/processed/model_training_table.parquet`
- `data/audit/feature_dictionary.md`
- `data/audit/leakage_audit.md`

### Feature Families

- Player age, experience, and career history
- Prior-year and recency-weighted production
- Targets, carries, receptions, passing attempts, snaps, and expected opportunity
- Weekly production, usage, and snap volatility
- Games missed, injury-report frequency, and career availability
- Prior-team pass/rush rate, offensive plays, and points per game

Historical outcomes cover prediction seasons 2017-2025. Rows for 2026 have blank targets.


## Chunk 4: Baseline Model Training

Chunk 4 trains deterministic point and quantile models, evaluates them with walk-forward
season splits, and generates the first 2026 projections.

### Run Model Training

```bash
python scripts/run_model_training.py
```

The command supports `--min-train-seasons`, `--n-estimators`,
`--quantile-estimators`, and `--random-state`.

### Outputs

- `data/audit/model_eval_by_season.csv`
- `data/audit/model_eval_by_position.csv`
- `data/audit/feature_importance.csv`
- `data/audit/backtest_report.md`
- `models/baseline_model.pkl`
- `data/processed/backtest_predictions.parquet`
- `data/processed/baseline_2026_projections.parquet`

### Backtest Design and Results

- Walk-forward evaluation trains only on seasons before each test season.
- Test seasons cover 2019-2025 after two seed seasons.
- Point models predict total PPR points, PPR points per game, and games played.
- Quantile models predict 10th, 50th, and 90th percentile season points.
- Random forest MAE improves over the prior-year baseline for every target and position.
- Mean 80% interval coverage is 88.9%, indicating conservative baseline intervals.
- ADP remains excluded until Chunk 5 so projection skill and market value are evaluated separately.
True rookies and players returning after a full season away require a later rookie/offseason extension.

## Chunk 5: Market Value and Draft Board

Chunk 5 keeps market price separate from model training, snapshots the source date,
matches market players to nflverse IDs, and converts projection differences and
uncertainty into draft recommendations.

### Run Market Value Pipeline

```bash
python scripts/run_value_pipeline.py --refresh
```

FantasyPros exposes its current 2026 PPR consensus ADP page but limits anonymous
responses to five player rows. The default pipeline therefore attempts that official
ADP source first and, when the response is incomplete, uses the public nflverse copy
of FantasyPros PPR expert consensus rankings. Every row records `market_metric` as
either `adp` or `ecr`, so the fallback cannot be mistaken for actual ADP.

For a full authenticated FantasyPros export, run:

```bash
python scripts/run_value_pipeline.py --market-file path/to/FantasyPros_ADP.csv --snapshot-date 2026-08-05
```

### Outputs

- `data/snapshots/adp_snapshots.parquet`: append-only, idempotent dated market snapshots
- `data/audit/adp_join_report.csv`: ID/name match method, join status, and projection coverage
- `data/processed/draft_value_board.csv`: complete model-versus-market scoring table
- `data/processed/draft_value_board.html`: standalone searchable draft board

### Value Interpretation

- Positive `rank_value` means the model ranks a player earlier than the market.
- Model overall rank uses median points above position-specific replacement, not raw
  cross-position fantasy points.
- `beat_market_probability` and `bust_probability` approximate outcomes from the
  model's 10th/50th/90th percentile projections.
- `risk_adjusted_value_score` combines expected point value, upside, downside, bust
  probability, and market-cost-normalized rank value.
- Recommendations are screening labels, not guarantees. Current boards exclude players

## Parallel Boosted Point-Model Benchmark

Boosted point models are trained and evaluated alongside the existing Random Forest
without replacing production projections or the Draft Value Board.

```bash
python scripts/run_boosting_benchmark.py
```

Candidates use identical preprocessing and walk-forward 2019-2025 test seasons:

- Random Forest
- Gradient boosting with squared-error loss
- Gradient boosting with Huber loss
- Gradient boosting with absolute-error loss
- Gradient boosting with Q50 quantile loss
- Equal and prior-validation-weighted ensembles

The validation-weighted ensemble for each historical season uses weights learned only
from earlier out-of-fold seasons. Final 2026 weights use all 2019-2025 out-of-fold
predictions. Absolute-error and Q50 models are retained as separate comparison rows,
but only Q50 enters the ensembles because their current predictions are identical.

### Benchmark Outputs

- `data/audit/boosting_model_summary.csv`
- `data/audit/boosting_model_eval_by_season.csv`
- `data/audit/boosting_model_eval_by_position.csv`
- `data/audit/boosting_feature_importance.csv`
- `data/audit/boosting_ensemble_weights.csv`
- `data/audit/boosting_benchmark_report.md`
- `data/processed/boosting_backtest_predictions.parquet`
- `data/processed/boosting_2026_projections.parquet`
- `data/processed/boosting_2026_model_comparison.csv`
- `models/boosting_candidate_models.pkl`

The 2026 comparison contains separate point projections, positional ranks, overall
value-above-replacement ranks, projection spread, and rank spread for every candidate.
Promotion is deliberately separate from benchmarking: the current baseline projections
and draft board remain unchanged until a candidate passes the documented gate and is
