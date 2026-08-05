"""Human-readable report for the parallel boosted point-model benchmark."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from fantasy_nfl.models.boosting import ENSEMBLE_MODELS, STANDALONE_MODELS
from fantasy_nfl.utils.io import write_markdown


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for values in frame.itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(
                f"{value:.4f}" if isinstance(value, (float, np.floating)) else str(value)
                for value in values
            )
            + " |"
        )
    return "\n".join(lines)


def weighted_metric_summary(evaluation: pd.DataFrame) -> pd.DataFrame:
    """Aggregate season metrics while respecting different fold sizes."""
    rows = []
    for model, group in evaluation.groupby("model"):
        weights = group["n_test"].to_numpy(float)
        rows.append(
            {
                "model": model,
                "mae": np.average(group["mae"], weights=weights),
                "rmse": np.average(group["rmse"], weights=weights),
                "r2": np.average(group["r2"], weights=weights),
                "rank_correlation": np.average(group["rank_correlation"], weights=weights),
            }
        )
    return pd.DataFrame(rows).sort_values("mae", kind="stable").reset_index(drop=True)


def promotion_assessment(summary: pd.DataFrame) -> tuple[bool, str]:
    """Apply a conservative gate; benchmark output never promotes automatically."""
    standalone = summary.loc[summary["model"].isin(STANDALONE_MODELS)].sort_values("mae")
    ensemble = summary.loc[summary["model"] == "ensemble_validation_weighted"].iloc[0]
    best = standalone.iloc[0]
    eligible = bool(
        ensemble["mae"] <= best["mae"] * 0.995
        and ensemble["rmse"] <= best["rmse"] * 1.01
        and ensemble["rank_correlation"] >= best["rank_correlation"] - 0.005
    )
    if eligible:
        message = (
            "The validation-weighted ensemble clears the conservative promotion gate, "
            "but production outputs remain unchanged pending an explicit promotion step."
        )
    else:
        message = (
            f"The ensemble does not clearly beat the best standalone model ({best['model']}); "
            "retain parallel comparison outputs and do not promote it."
        )
    return eligible, message


def write_boosting_report(
    season_evaluation: pd.DataFrame,
    position_evaluation: pd.DataFrame,
    importance: pd.DataFrame,
    weights: pd.DataFrame,
    projections: pd.DataFrame,
    path: Path,
) -> Path:
    """Write model metrics, learned weights, importance, and promotion assessment."""
    summary = weighted_metric_summary(season_evaluation).round(4)
    position_summary = (
        position_evaluation.groupby(["position", "model"], as_index=False)
        .apply(
            lambda group: pd.Series(
                {
                    "mae": np.average(group["mae"], weights=group["n_test"]),
                    "rmse": np.average(group["rmse"], weights=group["n_test"]),
                    "rank_correlation": np.average(
                        group["rank_correlation"], weights=group["n_test"]
                    ),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
        .sort_values(["position", "mae"])
        .round(4)
    )
    final_weights = weights.loc[weights["scope"] == "final_2026", ["model", "weight"]].round(4)
    top_features = (
        importance.sort_values(["model", "importance"], ascending=[True, False])
        .groupby("model", as_index=False)
        .head(8)[["model", "feature", "importance"]]
        .round(5)
    )
    eligible, assessment = promotion_assessment(summary)
    lines = [
        "# Boosted Point-Model Benchmark",
        "",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Walk-forward test seasons: {int(season_evaluation.test_season.min())}-{int(season_evaluation.test_season.max())}",
        f"- Parallel 2026 projection rows: {len(projections)}",
        "- Production status: unchanged; these are comparison candidates.",
        "",
        "## Overall Walk-Forward Comparison",
        "",
        _markdown_table(summary),
        "",
        "## Promotion Gate",
        "",
        f"- Eligible: {'yes' if eligible else 'no'}",
        f"- {assessment}",
        "",
        "## Final 2026 Validation Weights",
        "",
        _markdown_table(final_weights),
        "",
        "Weights are inverse-squared-MAE weights learned from 2019-2025 out-of-fold predictions.",
        "During the backtest, each season's weighted ensemble uses only earlier out-of-fold seasons.",
        "",
        "## Position Comparison",
        "",
        _markdown_table(position_summary),
        "",
        "## Leading Features by Candidate",
        "",
        _markdown_table(top_features),
        "",
        "## Interpretation",
        "",
        "Squared-error boosting emphasizes large misses. Huber reduces the influence of extreme misses.",
        "Absolute-error and Q50 boosting target the conditional median and are naturally aligned with MAE.",
        "Model importance is reported separately; it is not averaged across incompatible importance scales.",
        "Absolute-error and Q50 are identical under the current hyperparameters, so only Q50 participates in ensembles.",
        "The existing draft board is intentionally not overwritten by this benchmark.",
    ]
    return write_markdown(path, "\n".join(lines))
