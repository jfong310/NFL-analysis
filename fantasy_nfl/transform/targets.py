"""Aggregate scored player-weeks into season-level training targets."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from fantasy_nfl.config.scoring import REPLACEMENT_RANKS, SCORING_FORMATS


def build_player_season_targets(
    player_week: pd.DataFrame,
    replacement_ranks: Mapping[str, int] = REPLACEMENT_RANKS,
) -> pd.DataFrame:
    """Build one row per player-season with PPR-primary and alternate-format targets."""
    required = {
        "player_id",
        "player_name",
        "season",
        "week",
        "position",
        "team",
        *[f"fantasy_points_{name}" for name in SCORING_FORMATS],
    }
    missing = sorted(required - set(player_week.columns))
    if missing:
        raise ValueError(f"Scored player-week data missing columns: {missing}")

    key = ["player_id", "season", "week"]
    duplicate_rows = int(player_week.duplicated(key, keep=False).sum())
    if duplicate_rows:
        raise ValueError(f"Scored data contain {duplicate_rows} duplicate player-week rows")

    work = player_week.sort_values(["player_id", "season", "week"]).copy()
    grouped = work.groupby(["player_id", "season"], as_index=False, sort=False)
    targets = grouped.agg(
        player_name=("player_name", "last"),
        position=("position", "last"),
        team=("team", "last"),
        games_played=("week", "size"),
        first_week=("week", "min"),
        last_week=("week", "max"),
        total_fantasy_points_standard=("fantasy_points_standard", "sum"),
        total_fantasy_points_half_ppr=("fantasy_points_half_ppr", "sum"),
        total_fantasy_points_ppr=("fantasy_points_ppr", "sum"),
        weekly_std_dev=("fantasy_points_ppr", lambda values: float(values.std(ddof=0))),
    )

    for scoring_format in SCORING_FORMATS:
        total_column = f"total_fantasy_points_{scoring_format}"
        targets[f"points_per_game_{scoring_format}"] = (
            targets[total_column] / targets["games_played"]
        )

    targets["total_fantasy_points"] = targets["total_fantasy_points_ppr"]
    targets["points_per_game"] = targets["points_per_game_ppr"]
    targets["positional_finish"] = (
        targets.groupby(["season", "position"])["total_fantasy_points"]
        .rank(method="min", ascending=False)
        .astype("int64")
    )
    for cutoff in (12, 24, 36):
        targets[f"top_{cutoff}_finish"] = (
            targets["positional_finish"] <= cutoff
        ).astype("int8")

    baselines: dict[tuple[int, str], tuple[int, float, float]] = {}
    for (season, position), group in targets.groupby(["season", "position"]):
        requested_rank = int(replacement_ranks[position])
        ordered = group.sort_values(
            ["total_fantasy_points", "points_per_game", "player_id"],
            ascending=[False, False, True],
        )
        index = min(requested_rank, len(ordered)) - 1
        replacement = ordered.iloc[index]
        baselines[(int(season), position)] = (
            min(requested_rank, len(ordered)),
            float(replacement["points_per_game"]),
            float(replacement["total_fantasy_points"]),
        )

    keys = list(zip(targets["season"].astype(int), targets["position"]))
    targets["replacement_rank"] = [baselines[key][0] for key in keys]
    targets["replacement_points_per_game"] = [baselines[key][1] for key in keys]
    targets["replacement_total_fantasy_points"] = [baselines[key][2] for key in keys]
    targets["replacement_adjusted_points"] = (
        targets["total_fantasy_points"] - targets["replacement_total_fantasy_points"]
    )
    targets["replacement_adjusted_points_per_game"] = (
        targets["replacement_adjusted_points"] / targets["games_played"]
    )

    return targets.sort_values(
        ["season", "position", "positional_finish", "player_id"]
    ).reset_index(drop=True)
