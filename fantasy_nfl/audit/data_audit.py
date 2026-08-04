"""Dataset audit routines for nflverse/nflreadpy availability checks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

try:
    import pandas as pd
except Exception:  # noqa: BLE001
    pd = None

from fantasy_nfl.config.paths import AUDIT_DIR, AUDIT_SAMPLES_DIR, ensure_data_dirs
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
from fantasy_nfl.transform.player_week import build_player_week
from fantasy_nfl.utils.io import save_sample, write_markdown
from fantasy_nfl.utils.logging import get_logger

logger = get_logger(__name__)

PLAYER_KEYS = ["player_id", "gsis_id", "nfl_id", "pfr_id", "fantasypros_id", "sleeper_id", "espn_id", "yahoo_id", "player_name", "display_name", "football_name", "full_name"]
TEAM_KEYS = ["team", "recent_team", "posteam", "home_team", "away_team"]
TIME_KEYS = ["season", "week", "game_id", "season_type"]


def _first_present(columns: list[str], choices: list[str]) -> str | None:
    for c in choices:
        if c in columns:
            return c
    return None


def _summarize_dataset(name: str, result: dict, seasons: list[int]) -> dict:
    row = {
        "dataset_name": name,
        "load_status": result.get("status", "failed"),
        "row_count": 0,
        "column_count": 0,
        "columns": "",
        "sample_columns": "",
        "seasons_requested": str(seasons),
        "min_season": None,
        "max_season": None,
        "unique_players": None,
        "unique_teams": None,
        "cache_status": result.get("cache_status", ""),
        "cache_path": result.get("cache_path", ""),
        "missingness_summary": "",
        "sample_output_path": "",
        "error_message": result.get("error", ""),
        "join_keys_found": "",
    }
    if result.get("status") != "success" or result.get("data") is None:
        return row

    df = result["data"]
    cols = list(df.columns)
    row["row_count"] = int(len(df))
    row["column_count"] = int(len(cols))
    row["columns"] = "|".join(cols)
    row["sample_columns"] = "|".join(cols[:20])

    if "season" in df.columns:
        row["min_season"] = pd.to_numeric(df["season"], errors="coerce").min()
        row["max_season"] = pd.to_numeric(df["season"], errors="coerce").max()

    player_col = _first_present(cols, PLAYER_KEYS)
    if player_col:
        row["unique_players"] = int(df[player_col].nunique(dropna=True))

    team_col = _first_present(cols, TEAM_KEYS)
    if team_col:
        row["unique_teams"] = int(df[team_col].nunique(dropna=True))

    key_cols = [c for c in PLAYER_KEYS + TEAM_KEYS + TIME_KEYS if c in df.columns]
    row["join_keys_found"] = "|".join(key_cols)
    if key_cols:
        miss = {c: float(df[c].isna().mean()) for c in key_cols[:12]}
        row["missingness_summary"] = "; ".join(f"{k}={v:.3f}" for k, v in miss.items())

    sample_path = save_sample(df, AUDIT_SAMPLES_DIR / f"{name}_sample")
    row["sample_output_path"] = str(sample_path)
    return row


def _markdown_table(frame: pd.DataFrame) -> str:
    """Render Markdown without pandas' optional tabulate dependency."""
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        values = [str(value).replace("|", "\\|") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _build_markdown(
    report_df: pd.DataFrame, seasons: list[int], join_report: pd.DataFrame | None = None
) -> str:
    now = datetime.now(timezone.utc).isoformat()
    success = report_df[report_df["load_status"] == "success"]["dataset_name"].tolist()
    failed = report_df[report_df["load_status"] == "failed"]["dataset_name"].tolist()

    lines = [
        "# fantasy_nfl_model Data Audit",
        "",
        f"- Audit timestamp (UTC): {now}",
        f"- Seasons requested: {seasons}",
        "",
        "## Dataset Summary",
        "",
        _markdown_table(
            report_df[["dataset_name", "load_status", "row_count", "column_count", "cache_status"]]
        ),
        "",
        "## Successful Loads",
        "",
        ", ".join(success) if success else "None",
        "",
        "## Failed Loads",
        "",
        ", ".join(failed) if failed else "None",
        "",
        "## Potential Join Keys",
        "",
    ]

    for _, rec in report_df.iterrows():
        keys = rec.get("join_keys_found", "") or "None detected"
        lines.append(f"- **{rec['dataset_name']}**: {keys}")

    if join_report is not None and not join_report.empty:
        lines.extend(
            [
                "",
                "## Player-Week Join Quality",
                "",
                _markdown_table(join_report[["dataset", "eligible_rows", "matched_rows", "match_rate", "right_duplicate_key_rows"]]),
            ]
        )


    lines.extend(
        [
            "",
            "## Initial Observations",
            "",
            "- Raw pulls are cached as parquet files with JSON provenance records.",
            "- The canonical sample contains regular-season QB/RB/WR/TE player-weeks.",
            "",
            "## Chunk 1 Artifacts",
            "",
            "- `data/audit/source_inventory.csv`",
            "- `data/audit/sample_player_week.parquet`",
            "- `data/audit/player_id_join_report.csv`",
            "- Per-source samples in `data/audit/samples/`",
        ]
    )
    return "\n".join(lines)


def run_data_audit(seasons: list[int], *, refresh: bool = False):
    """Run data-source audit and persist inventory artifacts."""
    if pd is None:
        raise ImportError("pandas is required to run data audit.")
    ensure_data_dirs()
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

    rows = []
    datasets = {}
    for name, cache_seasons, loader in loaders:
        logger.info("Auditing dataset: %s", name)
        result = load_or_fetch(name, cache_seasons, loader, refresh=refresh)
        rows.append(_summarize_dataset(name, result, seasons))
        if result.get("status") == "success" and result.get("data") is not None:
            datasets[name] = result["data"]

    inventory_df = pd.DataFrame(rows)
    inventory_path = AUDIT_DIR / "source_inventory.csv"
    inventory_df.to_csv(inventory_path, index=False)

    player_week, join_report = build_player_week(datasets)
    player_week_path = AUDIT_DIR / "sample_player_week.parquet"
    sample_player_week = player_week.groupby("season", group_keys=False).head(500).reset_index(drop=True)
    sample_player_week.to_parquet(player_week_path, index=False)
    join_report_path = AUDIT_DIR / "player_id_join_report.csv"
    join_report.to_csv(join_report_path, index=False)

    markdown_path = AUDIT_DIR / "data_audit.md"
    write_markdown(markdown_path, _build_markdown(inventory_df, seasons, join_report))

    return inventory_path, markdown_path, inventory_df
