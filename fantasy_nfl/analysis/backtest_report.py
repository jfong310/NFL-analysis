"""Markdown summary for baseline model backtests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from fantasy_nfl.utils.io import write_markdown


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        values = [
            f"{value:.4f}" if isinstance(value, float) else str(value)
            for value in row
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_backtest_report(
    season_evaluation: pd.DataFrame,
    position_evaluation: pd.DataFrame,
    predictions: pd.DataFrame,
    feature_importance: pd.DataFrame,
    path: Path,
) -> Path:
    point = season_evaluation[
        season_evaluation["model"].isin(["prior_year_baseline", "random_forest"])
    ]
    summary = (
        point.groupby(["target", "model"], as_index=False)
        .agg(
            mean_mae=("mae", "mean"),
            mean_rmse=("rmse", "mean"),
            mean_r2=("r2", "mean"),
            mean_rank_correlation=("rank_correlation", "mean"),
        )
        .round(4)
    )
    interval = season_evaluation[
        season_evaluation["model"].eq("quantile_interval_80")
    ]
    top_features = (
        feature_importance.sort_values(["target", "importance"], ascending=[True, False])
        .groupby("target", as_index=False)
        .head(10)[["target", "feature", "importance"]]
        .round(5)
    )
    lines = [
        "# Baseline Model Backtest Report",
        "",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Walk-forward test seasons: {int(point['test_season'].min())}-{int(point['test_season'].max())}",
        f"- Backtest prediction rows: {len(predictions)}",
        "- Models: prior-year baseline, random forest point estimates, gradient-boosted quantiles",
        "",
        "## Average Walk-Forward Metrics",
        "",
        _markdown_table(summary),
        "",
        "## Quantile Calibration",
        "",
        f"- Mean 80% interval coverage: {interval['interval_coverage'].mean():.4f}",
        f"- Mean 80% interval width: {interval['interval_width'].mean():.2f} points",
        "",
        "## Leading Features",
        "",
        _markdown_table(top_features),
        "",
        "## Evaluation Design",
        "",
        "Each test season is predicted using only earlier prediction seasons.",
        "The first two seasons seed training; walk-forward evaluation begins with 2019.",
        "Simple baselines reuse the immediately prior season's outcome.",
        "",
        "## Interpretation",
        "",
        "This is a baseline modeling milestone, not a claim of production-ready accuracy.",
        "ADP is intentionally excluded until Chunk 5 so model skill and market value remain separable.",
    ]
    return write_markdown(path, "\n".join(lines))
