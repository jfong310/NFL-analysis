"""Feature dictionary and future-leakage audit reporting."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from fantasy_nfl.transform.features import (
    FEATURE_DEFINITIONS,
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMNS,
)
from fantasy_nfl.utils.io import write_markdown


def build_leakage_checks(table: pd.DataFrame) -> pd.DataFrame:
    numeric_features = table[MODEL_FEATURE_COLUMNS].select_dtypes(include="number")
    numeric_values = numeric_features.to_numpy(dtype=float)
    checks = [
        {
            "check": "feature_source_is_prior_season",
            "passed": bool(
                (table["feature_source_season"] == table["prediction_season"] - 1).all()
            ),
            "details": f"violations={int((table['feature_source_season'] != table['prediction_season'] - 1).sum())}",
        },
        {
            "check": "unique_player_prediction_rows",
            "passed": not table.duplicated(["player_id", "prediction_season"]).any(),
            "details": f"duplicates={int(table.duplicated(['player_id', 'prediction_season']).sum())}",
        },
        {
            "check": "prediction_targets_are_blank",
            "passed": not table.loc[table["is_prediction_row"], TARGET_COLUMNS].notna().any().any(),
            "details": f"non_null_cells={int(table.loc[table['is_prediction_row'], TARGET_COLUMNS].notna().sum().sum())}",
        },
        {
            "check": "historical_outcomes_are_observed",
            "passed": bool(table.loc[table["is_training_row"], "target_observed"].all()),
            "details": f"training_rows={int(table['is_training_row'].sum())}",
        },
        {
            "check": "feature_values_are_finite",
            "passed": not np.isinf(numeric_values).any(),
            "details": f"infinite_values={int(np.isinf(numeric_values).sum())}",
        },
        {
            "check": "declared_feature_schema",
            "passed": set(MODEL_FEATURE_COLUMNS).issubset(table.columns),
            "details": f"declared_features={len(MODEL_FEATURE_COLUMNS)}",
        },
    ]
    return pd.DataFrame(checks)


def write_feature_dictionary(path: Path) -> Path:
    lines = [
        "# Feature Dictionary",
        "",
        "All features are calculated using information available no later than feature_source_season,",
        "which must equal prediction_season minus one for the current pipeline.",
        "",
        "| feature | family | definition |",
        "| --- | --- | --- |",
    ]
    for feature, (family, definition) in FEATURE_DEFINITIONS.items():
        lines.append(f"| {feature} | {family} | {definition} |")
    lines.extend(
        [
            "",
            "## Target Columns",
            "",
            "Target columns are outcomes from prediction_season. They are populated only for",
            "historical training rows and are blank for 2026 prediction rows.",
            "",
        ]
    )
    lines.extend(f"- {column}" for column in TARGET_COLUMNS)
    return write_markdown(path, "\n".join(lines))


def write_leakage_audit(table: pd.DataFrame, path: Path) -> tuple[Path, pd.DataFrame]:
    checks = build_leakage_checks(table)
    missingness = table[MODEL_FEATURE_COLUMNS].isna().mean().sort_values(ascending=False)
    lines = [
        "# Future-Leakage Audit",
        "",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Rows: {len(table)}",
        f"- Training rows: {int(table['is_training_row'].sum())}",
        f"- Prediction rows: {int(table['is_prediction_row'].sum())}",
        f"- Prediction seasons: {int(table['prediction_season'].min())}-{int(table['prediction_season'].max())}",
        f"- Feature count: {len(MODEL_FEATURE_COLUMNS)}",
        "",
        "## Guardrail Results",
        "",
        "| check | passed | details |",
        "| --- | --- | --- |",
    ]
    for row in checks.itertuples(index=False):
        lines.append(f"| {row.check} | {row.passed} | {row.details} |")
    lines.extend(
        [
            "",
            "## Feature Missingness",
            "",
            "| feature | missing_rate |",
            "| --- | --- |",
        ]
    )
    for feature, rate in missingness.items():
        lines.append(f"| {feature} | {rate:.4f} |")
    lines.extend(
        [
            "",
            "## Known Scope Limitation",
            "",
            "Rows require a prior NFL season, so true rookies and players returning after a full",
            "season away are not represented in this v1 table. Rookie-specific data is deferred.",
        ]
    )
    return write_markdown(path, "\n".join(lines)), checks
