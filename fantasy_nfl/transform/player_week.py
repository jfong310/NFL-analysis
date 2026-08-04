"""Construct and validate the canonical historical player-week table."""

from __future__ import annotations

from typing import Any

import pandas as pd

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}
TEAM_ALIASES = {"OAK": "LV", "SD": "LAC", "STL": "LA", "JAC": "JAX"}


def normalize_id(series: pd.Series) -> pd.Series:
    """Normalize nullable identifiers without converting missing values to strings."""
    return series.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})


def normalize_team(series: pd.Series) -> pd.Series:
    return series.astype("string").str.upper().str.strip().replace(TEAM_ALIASES)


def _dedupe(
    frame: pd.DataFrame, keys: list[str], order_by: str | None = None
) -> tuple[pd.DataFrame, int]:
    if any(key not in frame.columns for key in keys):
        return frame.iloc[0:0].copy(), 0
    work = frame.dropna(subset=keys).copy()
    duplicates = int(work.duplicated(keys, keep=False).sum())
    if order_by and order_by in work.columns:
        work = work.sort_values(order_by)
    return work.drop_duplicates(keys, keep="last"), duplicates


def _left_join(
    left: pd.DataFrame,
    right: pd.DataFrame,
    keys: list[str],
    dataset: str,
    value_columns: list[str],
    report: list[dict[str, Any]],
    order_by: str | None = None,
) -> pd.DataFrame:
    if any(key not in right.columns for key in keys):
        report.append(
            {
                "dataset": dataset,
                "left_rows": len(left),
                "eligible_rows": 0,
                "matched_rows": 0,
                "match_rate": 0.0,
                "unmatched_rows": len(left),
                "right_rows": len(right),
                "right_duplicate_key_rows": 0,
                "notes": f"missing join keys: {keys}",
            }
        )
        return left
    left = left.copy()
    right = right.copy()
    for key in keys:
        if key in {"season", "week"}:
            left[key] = pd.to_numeric(left[key], errors="coerce").astype("Int64")
            right[key] = pd.to_numeric(right[key], errors="coerce").astype("Int64")
        elif key in {"player_id", "game_id"}:
            left[key] = normalize_id(left[key])
            right[key] = normalize_id(right[key])
    selected = keys + [
        column for column in value_columns if column in right.columns and column not in keys
    ]
    right_unique, duplicates = _dedupe(right[selected], keys, order_by)
    marker = f"__matched_{dataset}"
    right_unique[marker] = True
    eligible = left[keys].notna().all(axis=1)
    joined = left.merge(
        right_unique, how="left", on=keys, validate="m:1", suffixes=("", f"_{dataset}")
    )
    matched = joined[marker].fillna(False).astype(bool)
    report.append(
        {
            "dataset": dataset,
            "left_rows": int(len(left)),
            "eligible_rows": int(eligible.sum()),
            "matched_rows": int(matched.sum()),
            "match_rate": float(matched.sum() / eligible.sum()) if eligible.sum() else 0.0,
            "unmatched_rows": int(eligible.sum() - matched.sum()),
            "right_rows": int(len(right)),
            "right_duplicate_key_rows": duplicates,
            "notes": "",
        }
    )
    return joined.drop(columns=[marker])


def build_player_week(
    datasets: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join audited sources and return a canonical table plus join-quality metrics."""
    if "player_stats_weekly" not in datasets:
        raise ValueError("player_stats_weekly is required")

    base = datasets["player_stats_weekly"].copy()
    required = {"player_id", "season", "week", "game_id", "position", "team"}
    missing = sorted(required - set(base.columns))
    if missing:
        raise ValueError(f"player stats missing required columns: {missing}")
    base["player_id"] = normalize_id(base["player_id"])
    base["team"] = normalize_team(base["team"])
    if "opponent_team" in base:
        base["opponent_team"] = normalize_team(base["opponent_team"])
    base = base[base["position"].isin(FANTASY_POSITIONS)].copy()
    if "season_type" in base:
        base = base[base["season_type"].eq("REG")].copy()
    key = ["player_id", "season", "week"]
    duplicate_rows = int(base.duplicated(key, keep=False).sum())
    if duplicate_rows:
        raise ValueError(f"player stats contain {duplicate_rows} duplicate player-week rows")

    report: list[dict[str, Any]] = [
        {
            "dataset": "player_stats_weekly",
            "left_rows": len(base),
            "eligible_rows": len(base),
            "matched_rows": len(base),
            "match_rate": 1.0,
            "unmatched_rows": 0,
            "right_rows": len(base),
            "right_duplicate_key_rows": duplicate_rows,
            "notes": "base table",
        }
    ]

    players = datasets.get("players", pd.DataFrame()).copy()
    if not players.empty and "gsis_id" in players:
        players["player_id"] = normalize_id(players["gsis_id"])
        base = _left_join(
            base,
            players,
            ["player_id"],
            "players",
            ["birth_date", "rookie_season", "years_of_experience", "pfr_id"],
            report,
        )

    rosters = datasets.get("rosters", pd.DataFrame()).copy()
    if not rosters.empty and "gsis_id" in rosters:
        rosters["player_id"] = normalize_id(rosters["gsis_id"])
        base = _left_join(
            base,
            rosters,
            ["player_id", "season"],
            "rosters",
            ["status", "years_exp", "depth_chart_position"],
            report,
        )

    schedules = datasets.get("schedules", pd.DataFrame()).copy()
    if not schedules.empty:
        base = _left_join(
            base,
            schedules,
            ["game_id"],
            "schedules",
            ["gameday", "home_team", "away_team", "location", "roof", "surface"],
            report,
        )

    injuries = datasets.get("injuries", pd.DataFrame()).copy()
    if not injuries.empty and "gsis_id" in injuries:
        injuries["player_id"] = normalize_id(injuries["gsis_id"])
        base = _left_join(
            base,
            injuries,
            ["player_id", "season", "week"],
            "injuries",
            ["report_status", "report_primary_injury", "practice_status"],
            report,
            "date_modified",
        )

    opportunity = datasets.get("ff_opportunity_weekly", pd.DataFrame()).copy()
    if not opportunity.empty and "player_id" in opportunity:
        opportunity["player_id"] = normalize_id(opportunity["player_id"])
        base = _left_join(
            base,
            opportunity,
            ["player_id", "season", "week"],
            "ff_opportunity_weekly",
            ["total_fantasy_points_exp", "total_fantasy_points_diff"],
            report,
        )

    snaps = datasets.get("snap_counts", pd.DataFrame()).copy()
    crosswalk = datasets.get("fantasy_player_ids", pd.DataFrame()).copy()
    if (
        not snaps.empty
        and not crosswalk.empty
        and {"pfr_id", "gsis_id"}.issubset(crosswalk.columns)
        and "pfr_player_id" in snaps
    ):
        crosswalk["pfr_player_id"] = normalize_id(crosswalk["pfr_id"])
        crosswalk["player_id"] = normalize_id(crosswalk["gsis_id"])
        xwalk, _ = _dedupe(crosswalk[["pfr_player_id", "player_id"]], ["pfr_player_id"])
        snaps["pfr_player_id"] = normalize_id(snaps["pfr_player_id"])
        snaps = snaps.merge(xwalk, how="left", on="pfr_player_id", validate="m:1")
        base = _left_join(
            base,
            snaps,
            ["player_id", "game_id"],
            "snap_counts",
            ["offense_snaps", "offense_pct"],
            report,
        )

    rename = {
        "player_display_name": "player_name",
        "opponent_team": "opponent",
        "attempts": "passing_attempts",
        "fantasy_points_ppr": "fantasy_points",
        "offense_snaps": "snap_count",
        "offense_pct": "snap_share",
        "report_status": "injury_status",
    }
    for old, new in rename.items():
        if old in base.columns:
            if new in base.columns and old != new:
                base = base.drop(columns=[new])
            base = base.rename(columns={old: new})
    base["games_played_flag"] = 1
    preferred = [
        "player_id", "player_name", "season", "week", "team", "opponent", "position",
        "game_id", "fantasy_points", "targets", "receptions", "receiving_yards",
        "receiving_tds", "carries", "rushing_yards", "rushing_tds", "passing_attempts",
        "passing_yards", "passing_tds", "passing_interceptions", "snap_count", "snap_share",
        "injury_status", "games_played_flag", "total_fantasy_points_exp", "birth_date",
        "years_exp", "gameday", "home_team", "away_team",
    ]
    output = base[[column for column in preferred if column in base.columns]].copy()
    output = output.sort_values(["season", "week", "player_id"]).reset_index(drop=True)
    return output, pd.DataFrame(report)
