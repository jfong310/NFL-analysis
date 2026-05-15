from __future__ import annotations

from fantasy_nfl.config.scoring import DEFAULT_SCORING_FORMAT, REPLACEMENT_BASELINES, TARGET_POSITIONS
from fantasy_nfl.transform.scoring import score_player_weeks


def _detect_duplicate_key(df):
    preferred = ["player_id", "season", "week", "season_type"]
    if all(c in df.columns for c in preferred):
        return preferred
    fallback = ["player_name", "season", "week"] + (["team"] if "team" in df.columns else ["recent_team"] if "recent_team" in df.columns else [])
    return [c for c in fallback if c in df.columns]


def _primary_team(group):
    if "team" not in group.columns:
        return None
    counts = group.groupby("team").size().reset_index(name="n")
    max_n = counts["n"].max()
    tied = counts[counts["n"] == max_n]["team"].tolist()
    if len(tied) == 1 or "week" not in group.columns:
        return tied[0]
    latest = group[group["team"].isin(tied)].sort_values("week").iloc[-1]
    return latest["team"]


def build_player_week_scored(player_week_df):
    return score_player_weeks(player_week_df)


def calculate_positional_finishes(season_df, scoring_col):
    rank_col = scoring_col.replace("total_fantasy_points", "positional_finish")
    season_df[rank_col] = season_df.groupby(["season", "position"])[scoring_col].rank(method="min", ascending=False).astype(int)
    return season_df


def calculate_replacement_baselines(season_df, scoring_col, baselines=None):
    baselines = baselines or REPLACEMENT_BASELINES
    warnings = []
    rows = []
    for (season, position), grp in season_df.groupby(["season", "position"]):
        n = baselines.get(position)
        if n is None:
            continue
        s = grp.sort_values(scoring_col, ascending=False)
        idx = min(n, len(s)) - 1
        if len(s) < n:
            warnings.append(f"{season} {position}: only {len(s)} players for baseline {n}; using lowest available")
        rows.append({"season": season, "position": position, "baseline_points": s.iloc[idx][scoring_col]})
    return rows, warnings


def add_replacement_adjusted_points(season_df, scoring_col, baselines=None):
    rows, warnings = calculate_replacement_baselines(season_df, scoring_col, baselines)
    baseline_col = scoring_col.replace("total_fantasy_points", "replacement_baseline_points")
    adjusted_col = scoring_col.replace("total_fantasy_points", "replacement_adjusted_points")
    bdf = season_df.__class__(rows)
    if len(bdf) > 0:
        bdf = bdf.rename(columns={"baseline_points": baseline_col})
        season_df = season_df.merge(bdf, on=["season", "position"], how="left")
    else:
        season_df[baseline_col] = None
    season_df[adjusted_col] = season_df[scoring_col] - season_df[baseline_col]
    return season_df, warnings


def build_player_season_targets(player_week_scored_df, scoring_format=DEFAULT_SCORING_FORMAT, include_postseason=False):
    df = player_week_scored_df.copy()
    key = _detect_duplicate_key(df)
    dup_count = int(df.duplicated(subset=key).sum()) if key else 0
    if key:
        df = df.drop_duplicates(subset=key, keep="first")
    if (not include_postseason) and "season_type" in df.columns:
        df = df[df["season_type"] == "REG"].copy()
    if "position" in df.columns:
        df = df[df["position"].isin(TARGET_POSITIONS)].copy()
    usage_cols = [c for c in ["attempts", "carries", "targets", "receptions"] if c in df.columns]
    snap_cols = [c for c in ["snap_count", "offensive_snaps", "offense_snaps"] if c in df.columns]
    usage_sum = sum((df[c].fillna(0) for c in usage_cols), start=0) if usage_cols else 0
    snap_sum = sum((df[c].fillna(0) for c in snap_cols), start=0) if snap_cols else 0
    df["games_played_flag"] = ((df["fantasy_points"].fillna(0) != 0) | (usage_sum > 0) | (snap_sum > 0)).astype(int)
    df["games_with_points_flag"] = (df["fantasy_points"].fillna(0) > 0).astype(int)
    df["games_with_offensive_usage_flag"] = (usage_sum > 0).astype(int) if usage_cols else 0
    id_cols = [c for c in ["player_id", "player_name", "position", "season"] if c in df.columns]
    grouped = df.groupby(id_cols, dropna=False)
    season_df = grouped.agg(
        weeks_active=("fantasy_points", "size"),
        games_played=("games_played_flag", "sum"),
        games_with_points=("games_with_points_flag", "sum"),
        games_with_offensive_usage=("games_with_offensive_usage_flag", "sum"),
        total_fantasy_points=("fantasy_points", "sum"),
        total_fantasy_points_standard=("fantasy_points_standard", "sum"),
        total_fantasy_points_half_ppr=("fantasy_points_half_ppr", "sum"),
        total_fantasy_points_ppr=("fantasy_points_ppr", "sum"),
        weekly_mean=("fantasy_points", "mean"),
        weekly_median=("fantasy_points", "median"),
        weekly_std=("fantasy_points", "std"),
        weekly_min=("fantasy_points", "min"),
        weekly_max=("fantasy_points", "max"),
    ).reset_index()
    for suf in ["", "_standard", "_half_ppr", "_ppr"]:
        tot = f"total_fantasy_points{suf}"
        ppg = f"points_per_game{suf}"
        season_df[ppg] = season_df[tot] / season_df["games_played"].replace(0, float("nan"))
    if "team" in df.columns:
        primary = grouped.apply(_primary_team).reset_index(name="primary_team")
        season_df = season_df.merge(primary, on=id_cols, how="left")
    else:
        season_df["primary_team"] = None
    season_df = calculate_positional_finishes(season_df, "total_fantasy_points_ppr")
    season_df = calculate_positional_finishes(season_df, "total_fantasy_points_half_ppr")
    season_df = calculate_positional_finishes(season_df, "total_fantasy_points_standard")
    season_df["overall_finish_ppr"] = season_df.groupby(["season"])["total_fantasy_points_ppr"].rank(method="min", ascending=False).astype(int)
    warnings = []
    for col in ["total_fantasy_points_ppr", "total_fantasy_points_half_ppr", "total_fantasy_points_standard"]:
        season_df, w = add_replacement_adjusted_points(season_df, col)
        warnings.extend(w)
    meta = {"duplicate_count": dup_count, "duplicate_key": key, "duplicate_strategy": "keep_first", "warnings": warnings, "usage_cols": usage_cols, "snap_cols": snap_cols}
    return season_df, meta
