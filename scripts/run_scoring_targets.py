"""Build scored weekly data and season-level fantasy targets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

try:
    import pandas as pd
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"pandas is required for scoring pipeline: {exc}")

from fantasy_nfl.config.paths import AUDIT_DIR, AUDIT_SAMPLES_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, ensure_data_dirs
from fantasy_nfl.config.seasons import get_season_range
from fantasy_nfl.ingest.nflverse import load_player_stats_safe
from fantasy_nfl.transform.targets import build_player_season_targets, build_player_week_scored
from fantasy_nfl.utils.io import save_dataframe
from fantasy_nfl.validation.scoring_validation import generate_scoring_validation_report


def _read_path(path: Path):
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input file type: {path}")


def _load_weekly_data(input_path: str | None, seasons: list[int]):
    if input_path:
        p = Path(input_path)
        if not p.exists():
            raise FileNotFoundError(f"Input path not found: {p}")
        return _read_path(p), str(p)
    candidates = [
        AUDIT_SAMPLES_DIR / "player_stats_weekly_sample.parquet",
        AUDIT_SAMPLES_DIR / "player_stats_weekly_sample.csv",
        RAW_DATA_DIR / "player_stats_weekly.parquet",
        RAW_DATA_DIR / "player_stats_weekly.csv",
    ]
    for p in candidates:
        if p.exists():
            return _read_path(p), str(p)
    result = load_player_stats_safe(seasons)
    if result["status"] != "success" or result["data"] is None:
        raise RuntimeError(f"Unable to load weekly player stats from local files or nflverse loader: {result.get('error')}")
    return result["data"], "nflverse:nflreadpy load_player_stats_safe"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-season", type=int)
    parser.add_argument("--end-season", type=int)
    parser.add_argument("--scoring-format", default="ppr", choices=["standard", "half_ppr", "ppr"])
    parser.add_argument("--include-postseason", action="store_true")
    parser.add_argument("--input-path")
    args = parser.parse_args()

    ensure_data_dirs()
    seasons = get_season_range(args.start_season, args.end_season)
    weekly_df, source = _load_weekly_data(args.input_path, seasons)
    scored_df, scoring_meta = build_player_week_scored(weekly_df)
    season_df, target_meta = build_player_season_targets(scored_df, scoring_format=args.scoring_format, include_postseason=args.include_postseason)

    week_path = save_dataframe(scored_df, PROCESSED_DATA_DIR / "player_week_scored")
    season_path = save_dataframe(season_df, PROCESSED_DATA_DIR / "player_season_targets")
    report_path = AUDIT_DIR / "scoring_validation_report.md"
    generate_scoring_validation_report(
        input_source=source,
        weekly_df=weekly_df,
        scored_df=scored_df,
        season_df=season_df,
        scoring_meta=scoring_meta,
        target_meta=target_meta,
        include_postseason=args.include_postseason,
        output_path=report_path,
    )

    print(f"Wrote weekly scored output: {week_path}")
    print(f"Wrote season targets output: {season_path}")
    print(f"Wrote validation report: {report_path}")


if __name__ == "__main__":
    main()
