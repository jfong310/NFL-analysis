"""Validation metrics and Markdown reporting for Chunk 2 scoring outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from fantasy_nfl.utils.io import write_markdown


def scoring_validation_metrics(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scoring_format in ("standard", "ppr"):
        calculated = scored[f"fantasy_points_{scoring_format}"]
        reference = scored[f"nflverse_fantasy_points_{scoring_format}"]
        error = (calculated - reference).abs()
        rows.append(
            {
                "scoring_format": scoring_format,
                "rows_compared": int(error.notna().sum()),
                "exact_match_rate": float((error.fillna(float("inf")) < 1e-9).mean()),
                "mean_absolute_error": float(error.mean()),
                "max_absolute_error": float(error.max()),
                "rows_over_tolerance": int((error > 1e-9).sum()),
            }
        )
    return pd.DataFrame(rows)


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def write_scoring_validation_report(
    scored: pd.DataFrame, targets: pd.DataFrame, path: Path
) -> Path:
    metrics = scoring_validation_metrics(scored)
    duplicate_weeks = int(scored.duplicated(["player_id", "season", "week"]).sum())
    duplicate_seasons = int(targets.duplicated(["player_id", "season"]).sum())
    lines = [
        "# Fantasy Scoring Validation Report",
        "",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Scored player-week rows: {len(scored)}",
        f"- Player-season target rows: {len(targets)}",
        f"- Seasons: {int(scored['season'].min())}-{int(scored['season'].max())}",
        f"- Duplicate player-week rows: {duplicate_weeks}",
        f"- Duplicate player-season rows: {duplicate_seasons}",
        "",
        "## Reference Reconciliation",
        "",
        _markdown_table(metrics),
        "",
        "Standard and PPR calculations are independently reconstructed from component statistics.",
        "Half-PPR is calculated from the same rules with 0.5 points per reception; nflverse has no half-PPR reference column.",
        "",
        "## Replacement-Level Assumption",
        "",
        "The replacement player is selected at the configured total-points positional rank in each season.",
        "Replacement-adjusted points equal player season points minus that replacement player's season points.",
        "",
        "Default ranks: QB13, RB37, WR49, TE13.",
    ]
    return write_markdown(path, "\n".join(lines))
