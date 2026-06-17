from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from fantasy_nfl.config.scoring import REPLACEMENT_BASELINES, TARGET_POSITIONS


def build_scoring_validation_report(
    player_week_input: pd.DataFrame,
    player_week_scored: pd.DataFrame,
    player_season_targets: pd.DataFrame,
    metadata: dict,
) -> str:
    def _safe_table(frame: pd.DataFrame) -> str:
        try:
            return frame.to_markdown(index=False)
        except Exception:  # noqa: BLE001
            return "```\n" + frame.to_string(index=False) + "\n```"

    now = datetime.now(timezone.utc).isoformat()
    seasons = sorted(player_week_scored["season"].dropna().unique().tolist()) if "season" in player_week_scored.columns else []
    top_by_season = []
    if {"season", "player_name", "total_fantasy_points_ppr"}.issubset(player_season_targets.columns):
        for s, g in player_season_targets.groupby("season"):
            top = g.sort_values("total_fantasy_points_ppr", ascending=False).head(10)[["player_name", "position", "total_fantasy_points_ppr"]]
            top_by_season.append(f"### Season {s}\n\n{_safe_table(top)}")

    lines = [
        "# Scoring Validation Report",
        f"- Audit timestamp (UTC): {now}",
        f"- Seasons used: {seasons}",
        f"- Input source: {metadata.get('input_source')}",
        f"- Postseason excluded from season targets: {not metadata.get('include_postseason', False)}",
        f"- Input weekly rows: {len(player_week_input)}",
        f"- Scored weekly rows: {len(player_week_scored)}",
        f"- Season target rows: {len(player_season_targets)}",
        f"- Duplicate player-week rows found: {metadata.get('duplicate_count', 0)}",
        f"- Duplicate handling strategy: {metadata.get('duplicate_strategy', 'unknown')}",
        f"- Target positions included: {TARGET_POSITIONS}",
        f"- Scoring formats generated: {metadata.get('scoring_formats_generated')}",
        f"- Scoring columns found: {metadata.get('scoring_columns_found')}",
        f"- Scoring columns missing treated as zero: {metadata.get('scoring_columns_missing')}",
        "- Games played logic: non-zero fantasy points OR offensive usage cols (attempts/carries/targets/receptions/snaps) > 0; row-count fallback.",
        f"- Replacement assumptions: {REPLACEMENT_BASELINES}",
        f"- Replacement warnings: {metadata.get('replacement_warnings', [])}",
        "- Primary team logic: most active weeks, latest-week tie-break.",
        "",
        "## Basic sanity checks",
        f"- No negative games_played: {(player_season_targets.get('games_played', pd.Series(dtype=float)) >= 0).all()}",
        f"- replacement_adjusted_points exists: {any(c.startswith('replacement_adjusted_points_') for c in player_season_targets.columns)}",
        f"- duplicate player-season rows: {int(player_season_targets.duplicated(subset=[c for c in ['player_id','player_name','season'] if c in player_season_targets.columns]).sum())}",
        "",
        "## Top 10 players by total PPR points (each season)",
        *top_by_season,
    ]
    return "\n".join(lines)
