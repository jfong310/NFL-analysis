from __future__ import annotations

from datetime import datetime, timezone

from fantasy_nfl.config.scoring import REPLACEMENT_BASELINES, TARGET_POSITIONS


def _top10_tables(season_df):
    lines = []
    if season_df.empty:
        return ["No season targets available."]
    for season in sorted(season_df["season"].dropna().unique().tolist()):
        lines.append(f"### Top 10 PPR Total - {season}")
        top = season_df[season_df["season"] == season].nlargest(10, "total_fantasy_points_ppr")
        for _, r in top.iterrows():
            lines.append(f"- {r.get('player_name', 'unknown')} ({r.get('position')}): {r['total_fantasy_points_ppr']:.2f}")
    latest = max(season_df["season"].dropna().unique().tolist())
    lines.append(f"### Top 10 by Position - {latest}")
    subset = season_df[season_df["season"] == latest]
    for pos in TARGET_POSITIONS:
        lines.append(f"#### {pos}")
        top = subset[subset["position"] == pos].nlargest(10, "total_fantasy_points_ppr")
        for _, r in top.iterrows():
            lines.append(f"- {r.get('player_name', 'unknown')}: {r['total_fantasy_points_ppr']:.2f}")
    return lines


def generate_scoring_validation_report(*, input_source, weekly_df, scored_df, season_df, scoring_meta, target_meta, include_postseason, output_path):
    sane_games = bool((season_df["games_played"] >= 0).all()) if "games_played" in season_df.columns else False
    ppg_ok = True
    if {"points_per_game", "total_fantasy_points", "games_played"}.issubset(season_df.columns):
        check = season_df[season_df["games_played"] > 0]
        ppg_ok = ((check["points_per_game"] - (check["total_fantasy_points"] / check["games_played"]))
                  .abs().fillna(0) < 1e-9).all()
    pos_ok = all((season_df[c] > 0).all() for c in ["positional_finish_ppr", "positional_finish_half_ppr", "positional_finish_standard"] if c in season_df.columns)
    report = [
        "# Scoring Validation Report",
        f"- Audit timestamp (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Input source: {input_source}",
        f"- Seasons used: {sorted(scored_df['season'].dropna().unique().tolist()) if 'season' in scored_df.columns else 'unknown'}",
        f"- Postseason excluded from season targets: {not include_postseason}",
        f"- Input weekly rows: {len(weekly_df)}",
        f"- Scored weekly rows: {len(scored_df)}",
        f"- Season target rows: {len(season_df)}",
        f"- Duplicate player-week count: {target_meta.get('duplicate_count', 0)}",
        f"- Duplicate handling strategy: {target_meta.get('duplicate_strategy', 'unknown')} using key {target_meta.get('duplicate_key')}",
        f"- Target positions included: {TARGET_POSITIONS}",
        "- Non-target positions are excluded from season target output.",
        f"- Scoring formats generated: {scoring_meta.scoring_formats_generated}",
        f"- Scoring columns found: {scoring_meta.scoring_columns_found}",
        f"- Scoring columns missing (treated as zero): {scoring_meta.scoring_columns_missing}",
        f"- Games played logic: fantasy_points != 0 OR usage columns > 0 OR snap columns > 0; fallback row count via weeks_active.",
        f"- Replacement-level assumptions: {REPLACEMENT_BASELINES}",
        "- Primary team logic: most active weeks, latest-week tie-break.",
        "## Sanity Checks",
        f"- No negative games_played: {sane_games}",
        f"- points_per_game consistency: {bool(ppg_ok)}",
        f"- positional finish positive integers: {bool(pos_ok)}",
        f"- replacement_adjusted_points columns present: {all(c in season_df.columns for c in ['replacement_adjusted_points_ppr','replacement_adjusted_points_half_ppr','replacement_adjusted_points_standard'])}",
        f"- duplicate player-season rows: {int(season_df.duplicated(subset=[c for c in ['player_id','season'] if c in season_df.columns]).sum())}",
        "## Replacement baseline warnings",
    ]
    report.extend([f"- {w}" for w in target_meta.get("warnings", [])] or ["- None"])
    report.append("## Leaderboards")
    report.extend(_top10_tables(season_df))
    report.append("## Limitations")
    report.append("- Chunk 2 output only; ADP ingestion and ML modeling are intentionally not included yet.")
    output_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    return output_path
