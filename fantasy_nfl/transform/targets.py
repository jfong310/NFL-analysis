from __future__ import annotations

import pandas as pd

from fantasy_nfl.config.scoring import DEFAULT_SCORING_FORMAT, REPLACEMENT_BASELINES, TARGET_POSITIONS
from fantasy_nfl.transform.scoring import ScoringMetadata, score_player_weeks


USAGE_COLS = ["attempts", "carries", "targets", "receptions", "offensive_snaps", "snap_count"]


def _duplicate_key(df: pd.DataFrame) -> list[str]:
    preferred = ["player_id", "season", "week", "season_type"]
    if all(c in df.columns for c in preferred):
        return preferred
    fallback = [c for c in ["player_name", "season", "week", "team", "recent_team"] if c in df.columns]
    return fallback


def _dedupe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    key = _duplicate_key(df)
    if not key:
        return df.copy(), {"duplicate_count": 0, "duplicate_strategy": "no-key-no-dedupe"}
    dupes = int(df.duplicated(subset=key).sum())
    return df.drop_duplicates(subset=key, keep="first").copy(), {"duplicate_count": dupes, "duplicate_strategy": "drop_duplicates_keep_first", "duplicate_key": key}


def _primary_team(g: pd.DataFrame) -> object:
    team_col = "team" if "team" in g.columns else ("recent_team" if "recent_team" in g.columns else None)
    if team_col is None:
        return None
    grp = g.groupby(team_col, dropna=True).agg(active=("games_played", "sum"), latest_week=("week", "max")).reset_index()
    grp = grp.sort_values(["active", "latest_week"], ascending=[False, False])
    return grp.iloc[0][team_col] if not grp.empty else None


def build_player_week_scored(player_week_df: pd.DataFrame) -> tuple[pd.DataFrame, ScoringMetadata]:
    return score_player_weeks(player_week_df)


def calculate_positional_finishes(season_df: pd.DataFrame, scoring_col: str) -> pd.Series:
    return season_df.groupby(["season", "position"])[scoring_col].rank(method="min", ascending=False).astype("Int64")


def calculate_replacement_baselines(season_df: pd.DataFrame, scoring_col: str, baselines: dict[str, int] | None = None) -> tuple[pd.DataFrame, list[str]]:
    baselines = baselines or REPLACEMENT_BASELINES
    rows, warnings = [], []
    for (season, position), g in season_df.groupby(["season", "position"]):
        n = baselines.get(position)
        if n is None:
            continue
        vals = g.sort_values(scoring_col, ascending=False)[scoring_col].tolist()
        if not vals:
            continue
        idx = min(n, len(vals)) - 1
        if len(vals) < n:
            warnings.append(f"{season} {position}: only {len(vals)} players for baseline {n}.")
        rows.append({"season": season, "position": position, "replacement_baseline_points": vals[idx]})
    return pd.DataFrame(rows), warnings


def add_replacement_adjusted_points(season_df: pd.DataFrame, scoring_col: str, suffix: str) -> tuple[pd.DataFrame, list[str]]:
    base_df, warnings = calculate_replacement_baselines(season_df, scoring_col)
    out = season_df.merge(base_df, on=["season", "position"], how="left")
    out[f"replacement_baseline_points_{suffix}"] = out["replacement_baseline_points"]
    out[f"replacement_adjusted_points_{suffix}"] = out[scoring_col] - out["replacement_baseline_points"]
    return out.drop(columns=["replacement_baseline_points"]), warnings


def build_player_season_targets(player_week_scored_df: pd.DataFrame, scoring_format: str = DEFAULT_SCORING_FORMAT, include_postseason: bool = False) -> tuple[pd.DataFrame, dict]:
    df, dup_meta = _dedupe(player_week_scored_df)
    if not include_postseason and "season_type" in df.columns:
        df = df[df["season_type"] == "REG"].copy()

    usage_cols = [c for c in USAGE_COLS if c in df.columns]
    usage = sum((pd.to_numeric(df[c], errors="coerce").fillna(0) > 0) for c in usage_cols) > 0 if usage_cols else pd.Series(False, index=df.index)
    points_nonzero = pd.to_numeric(df.get("fantasy_points", 0), errors="coerce").fillna(0) != 0
    df["games_played"] = (points_nonzero | usage).astype(int)
    df["games_with_points"] = (pd.to_numeric(df.get("fantasy_points", 0), errors="coerce").fillna(0) > 0).astype(int)
    df["games_with_offensive_usage"] = usage.astype(int)

    group_cols = [c for c in ["player_id", "player_name", "position", "season"] if c in df.columns]
    season = df.groupby(group_cols, dropna=False).agg(
        weeks_active=("week", "count"),
        games_played=("games_played", "sum"),
        games_with_points=("games_with_points", "sum"),
        games_with_offensive_usage=("games_with_offensive_usage", "sum"),
        weekly_mean=("fantasy_points", "mean"),
        weekly_median=("fantasy_points", "median"),
        weekly_std=("fantasy_points", "std"),
        weekly_min=("fantasy_points", "min"),
        weekly_max=("fantasy_points", "max"),
    ).reset_index()
    for fmt in ["standard", "half_ppr", "ppr"]:
        col = f"fantasy_points_{fmt}"
        if col in df.columns:
            agg = df.groupby(group_cols, dropna=False)[col].sum().reset_index(name=f"total_fantasy_points_{fmt}")
            season = season.merge(agg, on=group_cols, how="left")
            season[f"points_per_game_{fmt}"] = season[f"total_fantasy_points_{fmt}"] / season["games_played"].where(season["games_played"] > 0)

    main_col = f"total_fantasy_points_{scoring_format}"
    season["total_fantasy_points"] = season[main_col]
    season["points_per_game"] = season[main_col] / season["games_played"].where(season["games_played"] > 0)

    if "position" in season.columns:
        season = season[season["position"].isin(TARGET_POSITIONS)].copy()

    season["primary_team"] = df.groupby(group_cols, dropna=False).apply(_primary_team).reset_index(name="primary_team")["primary_team"]
    for fmt in ["standard", "half_ppr", "ppr"]:
        tcol = f"total_fantasy_points_{fmt}"
        if tcol in season.columns:
            season[f"positional_finish_{fmt}"] = calculate_positional_finishes(season, tcol)
            season, warns = add_replacement_adjusted_points(season, tcol, fmt)
    if "total_fantasy_points_ppr" in season.columns:
        season["overall_finish_ppr"] = season.groupby("season")["total_fantasy_points_ppr"].rank(method="min", ascending=False).astype("Int64")
    return season, dup_meta
