"""Build Chunk 2 scored player-week and player-season target artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_nfl.audit.scoring_validation import write_scoring_validation_report
from fantasy_nfl.config.paths import AUDIT_DIR, PROCESSED_DATA_DIR, ensure_data_dirs
from fantasy_nfl.config.seasons import DEFAULT_END_SEASON, DEFAULT_START_SEASON
from fantasy_nfl.ingest.cache import load_or_fetch
from fantasy_nfl.ingest.nflverse import load_player_stats_safe
from fantasy_nfl.transform.scoring import build_player_week_scored
from fantasy_nfl.transform.targets import build_player_season_targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run fantasy scoring and target construction.")
    parser.add_argument("--start-season", type=int, default=DEFAULT_START_SEASON)
    parser.add_argument("--end-season", type=int, default=DEFAULT_END_SEASON)
    parser.add_argument("--refresh", action="store_true", help="Ignore the weekly-stat cache.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_season > args.end_season:
        raise ValueError("start-season must be <= end-season")

    seasons = list(range(args.start_season, args.end_season + 1))
    ensure_data_dirs()
    result = load_or_fetch(
        "player_stats_weekly",
        seasons,
        lambda: load_player_stats_safe(seasons),
        refresh=args.refresh,
    )
    if result.get("status") != "success" or result.get("data") is None:
        raise RuntimeError(f"Unable to load weekly stats: {result.get('error', 'unknown error')}")

    scored = build_player_week_scored(result["data"])
    targets = build_player_season_targets(scored)

    player_week_path = PROCESSED_DATA_DIR / "player_week_scored.parquet"
    player_season_path = PROCESSED_DATA_DIR / "player_season_targets.parquet"
    report_path = AUDIT_DIR / "scoring_validation_report.md"
    scored.to_parquet(player_week_path, index=False)
    targets.to_parquet(player_season_path, index=False)
    write_scoring_validation_report(scored, targets, report_path)

    print(f"player_week_scored.parquet saved to: {player_week_path}")
    print(f"player_season_targets.parquet saved to: {player_season_path}")
    print(f"scoring_validation_report.md saved to: {report_path}")


if __name__ == "__main__":
    main()
