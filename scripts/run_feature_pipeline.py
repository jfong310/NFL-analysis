"""Build leakage-safe Chunk 3 model features and audit artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_nfl.audit.feature_audit import (
    write_feature_dictionary,
    write_leakage_audit,
)
from fantasy_nfl.config.paths import AUDIT_DIR, PROCESSED_DATA_DIR, ensure_data_dirs
from fantasy_nfl.config.seasons import DEFAULT_END_SEASON, DEFAULT_START_SEASON
from fantasy_nfl.ingest.cache import load_or_fetch
from fantasy_nfl.ingest.nflverse import (
    load_ff_opportunity_safe,
    load_ff_playerids_safe,
    load_injuries_safe,
    load_player_stats_safe,
    load_players_safe,
    load_rosters_safe,
    load_schedules_safe,
    load_snap_counts_safe,
)
from fantasy_nfl.transform.features import (
    build_model_feature_table,
    enrich_scored_player_weeks,
)
from fantasy_nfl.transform.player_week import build_player_week
from fantasy_nfl.transform.scoring import build_player_week_scored
from fantasy_nfl.transform.targets import build_player_season_targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build leakage-safe player-season features.")
    parser.add_argument("--start-season", type=int, default=DEFAULT_START_SEASON)
    parser.add_argument("--end-season", type=int, default=DEFAULT_END_SEASON)
    parser.add_argument("--refresh", action="store_true", help="Ignore local raw-data caches.")
    return parser.parse_args()


def _load_sources(seasons: list[int], refresh: bool) -> dict:
    loaders = [
        ("player_stats_weekly", seasons, lambda: load_player_stats_safe(seasons)),
        ("rosters", seasons, lambda: load_rosters_safe(seasons)),
        ("players", None, load_players_safe),
        ("schedules", seasons, lambda: load_schedules_safe(seasons)),
        ("snap_counts", seasons, lambda: load_snap_counts_safe(seasons)),
        ("injuries", seasons, lambda: load_injuries_safe(seasons)),
        ("fantasy_player_ids", None, load_ff_playerids_safe),
        ("ff_opportunity_weekly", seasons, lambda: load_ff_opportunity_safe(seasons)),
    ]
    datasets = {}
    failures = []
    for name, cache_seasons, loader in loaders:
        result = load_or_fetch(name, cache_seasons, loader, refresh=refresh)
        if result.get("status") == "success" and result.get("data") is not None:
            datasets[name] = result["data"]
        else:
            failures.append(f"{name}: {result.get('error', 'unknown error')}")
    if failures:
        raise RuntimeError("Unable to build features; source failures: " + "; ".join(failures))
    return datasets


def main() -> None:
    args = parse_args()
    if args.start_season > args.end_season:
        raise ValueError("start-season must be <= end-season")
    seasons = list(range(args.start_season, args.end_season + 1))
    ensure_data_dirs()

    datasets = _load_sources(seasons, args.refresh)
    enriched, _ = build_player_week(datasets)
    scored = build_player_week_scored(datasets["player_stats_weekly"])
    targets = build_player_season_targets(scored)
    feature_weeks = enrich_scored_player_weeks(scored, enriched)
    table = build_model_feature_table(
        feature_weeks,
        targets,
        datasets["schedules"],
        datasets["players"],
    )

    table_path = PROCESSED_DATA_DIR / "model_training_table.parquet"
    dictionary_path = AUDIT_DIR / "feature_dictionary.md"
    leakage_path = AUDIT_DIR / "leakage_audit.md"
    table.to_parquet(table_path, index=False)
    write_feature_dictionary(dictionary_path)
    _, checks = write_leakage_audit(table, leakage_path)
    if not checks["passed"].all():
        failures = checks.loc[~checks["passed"], "check"].tolist()
        raise RuntimeError(f"Feature leakage guardrails failed: {failures}")

    print(f"model_training_table.parquet saved to: {table_path}")
    print(f"feature_dictionary.md saved to: {dictionary_path}")
    print(f"leakage_audit.md saved to: {leakage_path}")


if __name__ == "__main__":
    main()
