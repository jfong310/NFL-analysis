"""Run the fantasy_nfl data audit from CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fantasy_nfl.audit.data_audit import run_data_audit
from fantasy_nfl.config.seasons import DEFAULT_END_SEASON, DEFAULT_START_SEASON


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run nflverse/nflreadpy data audit.")
    parser.add_argument("--start-season", type=int, default=DEFAULT_START_SEASON)
    parser.add_argument("--end-season", type=int, default=DEFAULT_END_SEASON)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_season > args.end_season:
        raise ValueError("start-season must be <= end-season")

    seasons = list(range(args.start_season, args.end_season + 1))
    inventory_path, markdown_path, _ = run_data_audit(seasons)

    print(f"source_inventory.csv saved to: {inventory_path}")
    print(f"data_audit.md saved to: {markdown_path}")


if __name__ == "__main__":
    main()
