"""Vectorized fantasy scoring and canonical scored player-week construction."""

from __future__ import annotations

import pandas as pd

from fantasy_nfl.config.scoring import SCORING_FORMATS, SCORING_WEIGHTS, get_scoring_weights
from fantasy_nfl.transform.player_week import FANTASY_POSITIONS, normalize_id, normalize_team

IDENTITY_COLUMNS = [
    "player_id",
    "player_display_name",
    "season",
    "week",
    "season_type",
    "game_id",
    "team",
    "opponent_team",
    "position",
]

SCORING_STAT_COLUMNS = sorted(
    {column for weights in SCORING_WEIGHTS.values() for column in weights}
)


def calculate_fantasy_points(frame: pd.DataFrame, scoring_format: str = "ppr") -> pd.Series:
    """Calculate fantasy points from component statistics."""
    weights = get_scoring_weights(scoring_format)
    missing = sorted(set(weights) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing scoring columns: {missing}")
    points = pd.Series(0.0, index=frame.index, dtype="float64")
    for column, weight in weights.items():
        values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        points = points.add(values * weight, fill_value=0.0)
    return points


def build_player_week_scored(stats: pd.DataFrame) -> pd.DataFrame:
    """Create one independently scored row per regular-season fantasy player-week."""
    missing_identity = sorted(set(IDENTITY_COLUMNS) - set(stats.columns))
    if missing_identity:
        raise ValueError(f"Weekly stats missing identity columns: {missing_identity}")
    missing_stats = sorted(set(SCORING_STAT_COLUMNS) - set(stats.columns))
    if missing_stats:
        raise ValueError(f"Weekly stats missing scoring columns: {missing_stats}")

    work = stats.copy()
    work = work[
        work["season_type"].eq("REG") & work["position"].isin(FANTASY_POSITIONS)
    ].copy()
    work["player_id"] = normalize_id(work["player_id"])
    work["team"] = normalize_team(work["team"])
    work["opponent_team"] = normalize_team(work["opponent_team"])
    work["season"] = pd.to_numeric(work["season"], errors="raise").astype("int64")
    work["week"] = pd.to_numeric(work["week"], errors="raise").astype("int64")

    key = ["player_id", "season", "week"]
    if work[key].isna().any().any():
        raise ValueError("Scored player-week keys may not be missing")
    duplicate_rows = int(work.duplicated(key, keep=False).sum())
    if duplicate_rows:
        raise ValueError(f"Weekly stats contain {duplicate_rows} duplicate player-week rows")

    selected = IDENTITY_COLUMNS + SCORING_STAT_COLUMNS
    output = work[selected].copy()
    output = output.rename(
        columns={
            "player_display_name": "player_name",
            "opponent_team": "opponent",
        }
    )
    if "fantasy_points" in work:
        output["nflverse_fantasy_points_standard"] = pd.to_numeric(
            work["fantasy_points"], errors="coerce"
        )
    if "fantasy_points_ppr" in work:
        output["nflverse_fantasy_points_ppr"] = pd.to_numeric(
            work["fantasy_points_ppr"], errors="coerce"
        )

    for scoring_format in SCORING_FORMATS:
        output[f"fantasy_points_{scoring_format}"] = calculate_fantasy_points(
            work, scoring_format
        )

    output["fantasy_points"] = output["fantasy_points_ppr"]
    output["games_played_flag"] = 1
    return output.sort_values(["season", "week", "player_id"]).reset_index(drop=True)
