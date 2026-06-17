from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import pandas as pd
except Exception as exc:  # noqa: BLE001
    raise ImportError(f"pandas is required to run scoring/targets pipeline: {exc}")

from fantasy_nfl.config.paths import AUDIT_DIR, AUDIT_SAMPLES_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, ensure_data_dirs
from fantasy_nfl.config.scoring import DEFAULT_SCORING_FORMAT
from fantasy_nfl.config.seasons import DEFAULT_END_SEASON, DEFAULT_START_SEASON
from fantasy_nfl.ingest.nflverse import load_player_stats_safe
from fantasy_nfl.transform.targets import build_player_season_targets, build_player_week_scored
from fantasy_nfl.utils.io import save_dataframe, write_markdown
from fantasy_nfl.validation.scoring_validation import build_scoring_validation_report


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build scored weekly player table + season targets.")
    p.add_argument("--start-season", type=int, default=DEFAULT_START_SEASON)
    p.add_argument("--end-season", type=int, default=DEFAULT_END_SEASON)
    p.add_argument("--scoring-format", default=DEFAULT_SCORING_FORMAT, choices=["standard", "half_ppr", "ppr"])
    p.add_argument("--include-postseason", action="store_true")
    p.add_argument("--input-path", type=str, default=None)
    return p.parse_args()


def _load_local(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def load_weekly_data(args: argparse.Namespace) -> tuple[pd.DataFrame, str]:
    candidates = []
    if args.input_path:
        candidates.append(Path(args.input_path))
    candidates.extend([
        AUDIT_SAMPLES_DIR / "player_stats_weekly_sample.parquet",
        AUDIT_SAMPLES_DIR / "player_stats_weekly_sample.csv",
        RAW_DATA_DIR / "player_stats_weekly.parquet",
        RAW_DATA_DIR / "player_stats_weekly.csv",
    ])
    for c in candidates:
        if c.exists():
            return _load_local(c), str(c)
    seasons = list(range(args.start_season, args.end_season + 1))
    result = load_player_stats_safe(seasons)
    if result.get("status") != "success" or result.get("data") is None:
        raise RuntimeError(f"Unable to load weekly player stats from local files or nflverse loader: {result.get('error')}")
    return result["data"], f"nflverse loader seasons={seasons}"


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    weekly_df, source = load_weekly_data(args)
    scored_df, scoring_meta = build_player_week_scored(weekly_df)
    season_df, target_meta = build_player_season_targets(scored_df, scoring_format=args.scoring_format, include_postseason=args.include_postseason)

    out_week = save_dataframe(scored_df, PROCESSED_DATA_DIR / "player_week_scored")
    out_season = save_dataframe(season_df, PROCESSED_DATA_DIR / "player_season_targets")

    report = build_scoring_validation_report(
        weekly_df,
        scored_df,
        season_df,
        {
            "input_source": source,
            "include_postseason": args.include_postseason,
            "duplicate_count": target_meta.get("duplicate_count", 0),
            "duplicate_strategy": target_meta.get("duplicate_strategy", "unknown"),
            "scoring_formats_generated": scoring_meta.scoring_formats_generated,
            "scoring_columns_found": scoring_meta.scoring_columns_found,
            "scoring_columns_missing": scoring_meta.scoring_columns_missing,
            "replacement_warnings": [],
        },
    )
    report_path = write_markdown(AUDIT_DIR / "scoring_validation_report.md", report)
    print(f"player_week_scored output: {out_week}")
    print(f"player_season_targets output: {out_season}")
    print(f"scoring_validation_report output: {report_path}")


if __name__ == "__main__":
    main()
