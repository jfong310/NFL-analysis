"""Run Chunk 5 market ingestion, player matching, and draft-value scoring."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from fantasy_nfl.analysis.draft_value import build_draft_value_board
from fantasy_nfl.analysis.html_board import write_draft_board_html
from fantasy_nfl.config.paths import AUDIT_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR, SNAPSHOT_DIR, ensure_data_dirs
from fantasy_nfl.ingest.market import append_snapshot, fetch_fantasypros_adp, load_fantasypros_ppr_ecr, load_market_file
from fantasy_nfl.transform.market import match_market_players


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a model-versus-market fantasy draft board.")
    parser.add_argument("--market-file", type=Path, help="Optional full FantasyPros CSV/parquet export.")
    parser.add_argument("--snapshot-date", help="Override imported snapshot date (YYYY-MM-DD).")
    parser.add_argument("--refresh", action="store_true", help="Fetch current official market data.")
    parser.add_argument("--minimum-adp-rows", type=int, default=100)
    parser.add_argument("--projections-path", type=Path, default=PROCESSED_DATA_DIR / "baseline_2026_projections.parquet")
    parser.add_argument("--player-ids-path", type=Path, default=RAW_DATA_DIR / "fantasy_player_ids_all.parquet")
    return parser.parse_args()


def _select_market(args: argparse.Namespace, snapshot_path: Path) -> pd.DataFrame:
    if args.market_file:
        return load_market_file(args.market_file, snapshot_date=args.snapshot_date)
    if snapshot_path.exists() and not args.refresh:
        snapshots = pd.read_parquet(snapshot_path)
        latest = snapshots["snapshot_date"].astype(str).max()
        current = snapshots.loc[snapshots["snapshot_date"].astype(str) == latest].copy()
        preferred = current.loc[current["market_metric"] == "adp"]
        return preferred if len(preferred) >= args.minimum_adp_rows else current
    try:
        adp = fetch_fantasypros_adp(snapshot_date=args.snapshot_date)
        if len(adp) >= args.minimum_adp_rows:
            return adp
        print(f"FantasyPros returned only {len(adp)} visible ADP rows; using public PPR ECR fallback.")
    except Exception as exc:  # noqa: BLE001
        print(f"FantasyPros ADP fetch failed ({exc}); using public PPR ECR fallback.")
    return load_fantasypros_ppr_ecr()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    for path, instruction in [
        (args.projections_path, "Run scripts/run_model_training.py first."),
        (args.player_ids_path, "Run scripts/run_data_audit.py first."),
    ]:
        if not path.exists():
            raise FileNotFoundError(f"Required input not found: {path}. {instruction}")
    snapshot_path = SNAPSHOT_DIR / "adp_snapshots.parquet"
    market = _select_market(args, snapshot_path)
    append_snapshot(market, snapshot_path)
    crosswalk = pd.read_parquet(args.player_ids_path)
    projections = pd.read_parquet(args.projections_path)
    matched, join_report = match_market_players(market, crosswalk)
    join_report["has_projection"] = join_report["player_id"].isin(set(projections["player_id"].dropna()))
    join_report_path = AUDIT_DIR / "adp_join_report.csv"
    join_report.to_csv(join_report_path, index=False)
    board = build_draft_value_board(matched, projections)
    csv_path = PROCESSED_DATA_DIR / "draft_value_board.csv"
    html_path = PROCESSED_DATA_DIR / "draft_value_board.html"
    board.to_csv(csv_path, index=False)
    write_draft_board_html(board, html_path)
    matched_count = int(join_report["join_status"].eq("matched").sum())
    projected_count = int(join_report["has_projection"].sum())
    metric = ", ".join(sorted(market["market_metric"].dropna().unique()))
    print(f"Market snapshot: {len(market)} rows ({metric}) -> {snapshot_path}")
    print(f"Player-ID matches: {matched_count}/{len(join_report)}; with projections: {projected_count}")
    print(f"ADP join report saved to: {join_report_path}")
    print(f"Draft value board ({len(board)} rows) saved to: {csv_path}")
    print(f"HTML draft board saved to: {html_path}")


if __name__ == "__main__":
    main()
