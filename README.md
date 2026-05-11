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
