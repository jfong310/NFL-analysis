"""Leakage-safe preseason feature engineering for player-season prediction."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from fantasy_nfl.transform.player_week import normalize_id, normalize_team

IDENTITY_COLUMNS = [
    "player_id",
    "player_name",
    "position",
    "prediction_season",
    "feature_source_season",
    "prior_year_team",
    "target_observed",
    "is_training_row",
    "is_prediction_row",
]

FEATURE_DEFINITIONS: Mapping[str, tuple[str, str]] = {
    "age": ("profile", "Age on September 1 of the prediction season."),
    "years_experience": ("profile", "Prediction season minus rookie season; roster/career fallback."),
    "career_seasons": ("profile", "Number of NFL seasons observed through the feature cutoff."),
    "prior_year_games_played": ("availability", "Weekly-stat games in the immediately prior season."),
    "prior_year_games_missed": ("availability", "Scheduled season limit minus prior games played."),
    "prior_year_games_missed_rate": ("availability", "Prior games missed divided by season limit."),
    "career_games_missed_rate": ("availability", "Career missed games divided by career scheduled games."),
    "prior_year_injury_report_weeks": ("availability", "Prior weeks with an injury-report status."),
    "age_x_prior_missed_rate": ("availability", "Age multiplied by prior games-missed rate."),
    "prior_year_total_fantasy_points": ("production", "Prior-season PPR fantasy-point total."),
    "prior_year_points_per_game": ("production", "Prior-season PPR points per game."),
    "prior_year_positional_finish": ("production", "Prior-season PPR positional finish."),
    "prior_year_replacement_adjusted_points": ("production", "Prior PPR points above positional replacement."),
    "career_points_per_game": ("production", "Career PPR points divided by career games through cutoff."),
    "multi_year_weighted_points_per_game": ("production", "Recency-weighted PPG over up to three seasons (0.6/0.3/0.1)."),
    "recent_5_points_per_game": ("production", "Average PPR points over the last five prior-season games."),
    "recent_production_trend": ("production", "Last-five PPG minus full prior-season PPG."),
    "prior_year_targets_per_game": ("usage", "Prior targets per player-week."),
    "prior_year_carries_per_game": ("usage", "Prior carries per player-week."),
    "prior_year_receptions_per_game": ("usage", "Prior receptions per player-week."),
    "prior_year_passing_attempts_per_game": ("usage", "Prior passing attempts per player-week."),
    "prior_year_opportunities_per_game": ("usage", "Targets plus carries plus passing attempts per week."),
    "recent_5_opportunities_per_game": ("usage", "Average opportunities over the last five prior games."),
    "recent_usage_trend": ("usage", "Last-five opportunities minus full prior-season opportunities."),
    "multi_year_weighted_opportunities_per_game": ("usage", "Recency-weighted opportunities over up to three seasons."),
    "prior_year_expected_fantasy_points": ("usage", "Prior nflverse expected fantasy-point total."),
    "prior_year_expected_points_per_game": ("usage", "Prior expected fantasy points per player-week."),
    "prior_year_fantasy_points_over_expected": ("efficiency", "Prior actual PPR points minus expected points."),
    "prior_year_weekly_std_dev": ("volatility", "Population standard deviation of prior weekly PPR points."),
    "prior_year_coefficient_of_variation": ("volatility", "Prior weekly PPR standard deviation divided by mean."),
    "prior_year_boom_week_rate": ("volatility", "Share of prior weeks scoring at least 20 PPR points."),
    "prior_year_bust_week_rate": ("volatility", "Share of prior weeks scoring fewer than 5 PPR points."),
    "prior_year_usage_std_dev": ("volatility", "Population standard deviation of weekly opportunities."),
    "prior_year_snap_share": ("usage", "Mean offensive snap share in the prior season."),
    "prior_year_snap_share_std_dev": ("volatility", "Population standard deviation of offensive snap share."),
    "multi_year_weighted_snap_share": ("usage", "Recency-weighted snap share over up to three seasons."),
    "prior_team_pass_rate": ("team_context", "Prior team pass attempts divided by pass attempts plus carries."),
    "prior_team_rush_rate": ("team_context", "One minus prior team pass rate."),
    "prior_team_offensive_plays_per_game": ("team_context", "Prior team pass attempts plus carries per scheduled game."),
    "prior_team_points_per_game": ("team_context", "Prior team NFL points per scheduled game."),
}

MODEL_FEATURE_COLUMNS = list(FEATURE_DEFINITIONS)

TARGET_COLUMNS = [
    "target_games_played",
    "target_total_fantasy_points",
    "target_points_per_game",
    "target_weekly_std_dev",
    "target_positional_finish",
    "target_top_12_finish",
    "target_top_24_finish",
    "target_top_36_finish",
    "target_replacement_adjusted_points",
]


def enrich_scored_player_weeks(
    scored: pd.DataFrame, enriched: pd.DataFrame
) -> pd.DataFrame:
    """Add audited opportunity, snap, injury, and profile fields to scored weeks."""
    keys = ["player_id", "season", "week"]
    additions = [
        "targets",
        "carries",
        "passing_attempts",
        "snap_count",
        "snap_share",
        "injury_status",
        "total_fantasy_points_exp",
        "birth_date",
        "years_exp",
    ]
    right = enriched[keys + [c for c in additions if c in enriched.columns]].copy()
    right["player_id"] = normalize_id(right["player_id"])
    left = scored.copy()
    left["player_id"] = normalize_id(left["player_id"])
    for frame in (left, right):
        frame["season"] = pd.to_numeric(frame["season"], errors="raise").astype("int64")
        frame["week"] = pd.to_numeric(frame["week"], errors="raise").astype("int64")
    right = right.drop_duplicates(keys)
    merged = left.merge(right, on=keys, how="left", validate="1:1", suffixes=("", "_enriched"))
    for column in ("targets", "carries", "passing_attempts"):
        if column not in merged:
            merged[column] = 0.0
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)
    merged["opportunities"] = (
        merged["targets"] + merged["carries"] + merged["passing_attempts"]
    )
    return merged


def _safe_mean(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    return float(values.mean()) if values.notna().any() else np.nan


def aggregate_player_season_history(weeks: pd.DataFrame) -> pd.DataFrame:
    """Aggregate weekly feature inputs without using a future season."""
    rows: list[dict[str, Any]] = []
    for (player_id, season), group in weeks.groupby(["player_id", "season"], sort=True):
        group = group.sort_values("week")
        points = pd.to_numeric(group["fantasy_points_ppr"], errors="coerce").fillna(0.0)
        opportunities = pd.to_numeric(group["opportunities"], errors="coerce").fillna(0.0)
        recent = group.tail(5)
        recent_points = pd.to_numeric(recent["fantasy_points_ppr"], errors="coerce").fillna(0.0)
        recent_opportunities = pd.to_numeric(recent["opportunities"], errors="coerce").fillna(0.0)
        expected = pd.to_numeric(
            group.get("total_fantasy_points_exp", pd.Series(np.nan, index=group.index)),
            errors="coerce",
        )
        snap_share = pd.to_numeric(
            group.get("snap_share", pd.Series(np.nan, index=group.index)),
            errors="coerce",
        )
        mean_points = float(points.mean())
        row = {
            "player_id": player_id,
            "season": int(season),
            "history_games_played": int(len(group)),
            "history_targets_per_game": float(group["targets"].mean()),
            "history_carries_per_game": float(group["carries"].mean()),
            "history_receptions_per_game": float(
                pd.to_numeric(group["receptions"], errors="coerce").fillna(0.0).mean()
            ),
            "history_passing_attempts_per_game": float(group["passing_attempts"].mean()),
            "history_opportunities_per_game": float(opportunities.mean()),
            "history_recent_5_points_per_game": float(recent_points.mean()),
            "history_recent_5_opportunities_per_game": float(recent_opportunities.mean()),
            "history_usage_std_dev": float(opportunities.std(ddof=0)),
            "history_coefficient_of_variation": (
                float(points.std(ddof=0) / mean_points) if mean_points else 0.0
            ),
            "history_boom_week_rate": float((points >= 20.0).mean()),
            "history_bust_week_rate": float((points < 5.0).mean()),
            "history_expected_fantasy_points": (
                float(expected.sum()) if expected.notna().any() else np.nan
            ),
            "history_expected_points_per_game": (
                float(expected.mean()) if expected.notna().any() else np.nan
            ),
            "history_snap_share": _safe_mean(snap_share),
            "history_snap_share_std_dev": (
                float(snap_share.std(ddof=0)) if snap_share.notna().any() else np.nan
            ),
            "history_injury_report_weeks": int(
                group.get("injury_status", pd.Series(np.nan, index=group.index)).notna().sum()
            ),
            "history_birth_date": group.get(
                "birth_date", pd.Series(np.nan, index=group.index)
            ).dropna().iloc[-1]
            if group.get("birth_date", pd.Series(dtype=object)).notna().any()
            else np.nan,
            "history_years_exp": _safe_mean(
                group.get("years_exp", pd.Series(np.nan, index=group.index))
            ),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_team_context(weeks: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    """Create prior-season team environment features."""
    usage = (
        weeks.groupby(["season", "team"], as_index=False)
        .agg(
            team_passing_attempts=("passing_attempts", "sum"),
            team_carries=("carries", "sum"),
        )
    )
    schedule = schedules.copy()
    if "game_type" in schedule:
        schedule = schedule[schedule["game_type"].eq("REG")].copy()
    home = schedule[["season", "game_id", "home_team", "home_score"]].rename(
        columns={"home_team": "team", "home_score": "points_for"}
    )
    away = schedule[["season", "game_id", "away_team", "away_score"]].rename(
        columns={"away_team": "team", "away_score": "points_for"}
    )
    team_games = pd.concat([home, away], ignore_index=True)
    team_games["team"] = normalize_team(team_games["team"])
    context = (
        team_games.groupby(["season", "team"], as_index=False)
        .agg(team_games=("game_id", "nunique"), team_points=("points_for", "sum"))
    )
    usage["team"] = normalize_team(usage["team"])
    context = context.merge(usage, on=["season", "team"], how="left", validate="1:1")
    plays = context["team_passing_attempts"] + context["team_carries"]
    context["prior_team_pass_rate"] = context["team_passing_attempts"] / plays.replace(0, np.nan)
    context["prior_team_rush_rate"] = 1.0 - context["prior_team_pass_rate"]
    context["prior_team_offensive_plays_per_game"] = plays / context["team_games"]
    context["prior_team_points_per_game"] = context["team_points"] / context["team_games"]
    return context[
        [
            "season",
            "team",
            "prior_team_pass_rate",
            "prior_team_rush_rate",
            "prior_team_offensive_plays_per_game",
            "prior_team_points_per_game",
        ]
    ]


def _season_game_limit(season: int) -> int:
    return 17 if season >= 2021 else 16


def _weighted(history: pd.DataFrame, column: str) -> float:
    recent = history.sort_values("season", ascending=False).head(3)
    values = pd.to_numeric(recent[column], errors="coerce")
    weights = pd.Series([0.6, 0.3, 0.1][: len(recent)], index=recent.index)
    valid = values.notna()
    if not valid.any():
        return np.nan
    return float((values[valid] * weights[valid]).sum() / weights[valid].sum())


def _age_on_september_first(birth_date: Any, season: int) -> float:
    birth = pd.to_datetime(birth_date, errors="coerce")
    if pd.isna(birth):
        return np.nan
    cutoff = pd.Timestamp(datetime(season, 9, 1))
    return float((cutoff - birth).days / 365.2425)


def build_model_feature_table(
    weeks: pd.DataFrame,
    targets: pd.DataFrame,
    schedules: pd.DataFrame,
    players: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build player prediction rows using only seasons before prediction_season."""
    history_agg = aggregate_player_season_history(weeks)
    summary = targets.merge(
        history_agg, on=["player_id", "season"], how="left", validate="1:1"
    )
    profiles = players.copy() if players is not None else pd.DataFrame()
    rookie_map: dict[Any, Any] = {}
    if not profiles.empty and {"gsis_id", "rookie_season"}.issubset(profiles.columns):
        rookie_map = dict(
            zip(normalize_id(profiles["gsis_id"]), profiles["rookie_season"])
        )

    rows: list[dict[str, Any]] = []
    for player_id, player_history in summary.groupby("player_id", sort=True):
        player_history = player_history.sort_values("season")
        for index in range(len(player_history)):
            current = player_history.iloc[index]
            history = player_history.iloc[: index + 1]
            source_season = int(current["season"])
            prediction_season = source_season + 1
            scheduled = pd.Series(
                [_season_game_limit(int(value)) for value in history["season"]],
                index=history.index,
                dtype="float64",
            )
            games = pd.to_numeric(history["games_played"], errors="coerce").fillna(0.0)
            career_games = float(games.sum())
            career_scheduled = float(scheduled.sum())
            prior_limit = _season_game_limit(source_season)
            prior_games = int(current["games_played"])
            birth_date = current.get("history_birth_date", np.nan)
            age = _age_on_september_first(birth_date, prediction_season)
            rookie_season = pd.to_numeric(
                pd.Series([rookie_map.get(player_id)]), errors="coerce"
            ).iloc[0]
            if pd.notna(rookie_season):
                experience = max(0.0, float(prediction_season - rookie_season))
            elif pd.notna(current.get("history_years_exp", np.nan)):
                experience = float(current["history_years_exp"]) + 1.0
            else:
                experience = float(len(history))

            row = {
                "player_id": player_id,
                "player_name": current["player_name"],
                "position": current["position"],
                "prediction_season": prediction_season,
                "feature_source_season": source_season,
                "prior_year_team": current["team"],
                "age": age,
                "years_experience": experience,
                "career_seasons": int(len(history)),
                "prior_year_games_played": prior_games,
                "prior_year_games_missed": max(0, prior_limit - prior_games),
                "prior_year_games_missed_rate": max(0, prior_limit - prior_games)
                / prior_limit,
                "career_games_missed_rate": (
                    max(0.0, career_scheduled - career_games) / career_scheduled
                    if career_scheduled
                    else 0.0
                ),
                "prior_year_injury_report_weeks": current["history_injury_report_weeks"],
                "prior_year_total_fantasy_points": current["total_fantasy_points"],
                "prior_year_points_per_game": current["points_per_game"],
                "prior_year_positional_finish": current["positional_finish"],
                "prior_year_replacement_adjusted_points": current[
                    "replacement_adjusted_points"
                ],
                "career_points_per_game": (
                    float(history["total_fantasy_points"].sum()) / career_games
                    if career_games
                    else 0.0
                ),
                "multi_year_weighted_points_per_game": _weighted(
                    history, "points_per_game"
                ),
                "recent_5_points_per_game": current[
                    "history_recent_5_points_per_game"
                ],
                "recent_production_trend": current[
                    "history_recent_5_points_per_game"
                ]
                - current["points_per_game"],
                "prior_year_targets_per_game": current["history_targets_per_game"],
                "prior_year_carries_per_game": current["history_carries_per_game"],
                "prior_year_receptions_per_game": current[
                    "history_receptions_per_game"
                ],
                "prior_year_passing_attempts_per_game": current[
                    "history_passing_attempts_per_game"
                ],
                "prior_year_opportunities_per_game": current[
                    "history_opportunities_per_game"
                ],
                "recent_5_opportunities_per_game": current[
                    "history_recent_5_opportunities_per_game"
                ],
                "recent_usage_trend": current[
                    "history_recent_5_opportunities_per_game"
                ]
                - current["history_opportunities_per_game"],
                "multi_year_weighted_opportunities_per_game": _weighted(
                    history, "history_opportunities_per_game"
                ),
                "prior_year_expected_fantasy_points": current[
                    "history_expected_fantasy_points"
                ],
                "prior_year_expected_points_per_game": current[
                    "history_expected_points_per_game"
                ],
                "prior_year_fantasy_points_over_expected": current[
                    "total_fantasy_points"
                ]
                - current["history_expected_fantasy_points"]
                if pd.notna(current["history_expected_fantasy_points"])
                else np.nan,
                "prior_year_weekly_std_dev": current["weekly_std_dev"],
                "prior_year_coefficient_of_variation": current[
                    "history_coefficient_of_variation"
                ],
                "prior_year_boom_week_rate": current["history_boom_week_rate"],
                "prior_year_bust_week_rate": current["history_bust_week_rate"],
                "prior_year_usage_std_dev": current["history_usage_std_dev"],
                "prior_year_snap_share": current["history_snap_share"],
                "prior_year_snap_share_std_dev": current[
                    "history_snap_share_std_dev"
                ],
                "multi_year_weighted_snap_share": _weighted(
                    history, "history_snap_share"
                ),
            }
            row["age_x_prior_missed_rate"] = (
                age * row["prior_year_games_missed_rate"] if pd.notna(age) else np.nan
            )
            rows.append(row)

    table = pd.DataFrame(rows)
    team_context = build_team_context(weeks, schedules).rename(
        columns={"season": "feature_source_season", "team": "prior_year_team"}
    )
    table = table.merge(
        team_context,
        on=["feature_source_season", "prior_year_team"],
        how="left",
        validate="m:1",
    )

    target_source = targets[
        [
            "player_id",
            "season",
            "games_played",
            "total_fantasy_points",
            "points_per_game",
            "weekly_std_dev",
            "positional_finish",
            "top_12_finish",
            "top_24_finish",
            "top_36_finish",
            "replacement_adjusted_points",
        ]
    ].rename(
        columns={
            "season": "prediction_season",
            "games_played": "target_games_played",
            "total_fantasy_points": "target_total_fantasy_points",
            "points_per_game": "target_points_per_game",
            "weekly_std_dev": "target_weekly_std_dev",
            "positional_finish": "target_positional_finish",
            "top_12_finish": "target_top_12_finish",
            "top_24_finish": "target_top_24_finish",
            "top_36_finish": "target_top_36_finish",
            "replacement_adjusted_points": "target_replacement_adjusted_points",
        }
    )
    table = table.merge(
        target_source,
        on=["player_id", "prediction_season"],
        how="left",
        validate="1:1",
    )
    max_observed_season = int(targets["season"].max())
    table["target_observed"] = table["prediction_season"] <= max_observed_season
    zero_when_absent = [
        "target_games_played",
        "target_total_fantasy_points",
        "target_points_per_game",
        "target_weekly_std_dev",
        "target_top_12_finish",
        "target_top_24_finish",
        "target_top_36_finish",
        "target_replacement_adjusted_points",
    ]
    observed_missing = table["target_observed"]
    table.loc[observed_missing, zero_when_absent] = table.loc[
        observed_missing, zero_when_absent
    ].fillna(0.0)
    table["is_training_row"] = table["target_observed"]
    table["is_prediction_row"] = table["prediction_season"] == max_observed_season + 1

    ordered = IDENTITY_COLUMNS + MODEL_FEATURE_COLUMNS + TARGET_COLUMNS
    return table[ordered].sort_values(
        ["prediction_season", "position", "player_id"]
    ).reset_index(drop=True)
