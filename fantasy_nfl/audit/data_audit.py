"""Dataset audit routines for nflverse/nflreadpy availability checks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

try:
    import pandas as pd
except Exception:  # noqa: BLE001
    pd = None

from fantasy_nfl.config.paths import AUDIT_DIR, AUDIT_SAMPLES_DIR, ensure_data_dirs
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


def _build_markdown(report_df: pd.DataFrame, seasons: list[int]) -> str:
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
        report_df[["dataset_name", "load_status", "row_count", "column_count", "sample_output_path"]].to_markdown(index=False),
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

    lines.extend(
        [
            "",
            "## Initial Observations",
            "",
            "- This report focuses on loading viability and key-schema discovery only.",
            "- No modeling, fantasy scoring, ADP ingestion, or feature engineering is implemented in this chunk.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Stabilize final nflreadpy loader names based on your installed version.",
            "2. Add a light ID crosswalk strategy (player/team key normalization).",
            "3. Add incremental caching strategy in `data/raw/` for repeatable pulls.",
        ]
    )
    return "\n".join(lines)


def run_data_audit(seasons: list[int]):
    """Run data-source audit and persist inventory artifacts."""
    if pd is None:
        raise ImportError("pandas is required to run data audit.")
    ensure_data_dirs()
    loaders = [
        ("player_stats_weekly", lambda: load_player_stats_safe(seasons)),
        ("rosters", lambda: load_rosters_safe(seasons)),
        ("players", load_players_safe),
        ("schedules", lambda: load_schedules_safe(seasons)),
        ("snap_counts", lambda: load_snap_counts_safe(seasons)),
        ("injuries", lambda: load_injuries_safe(seasons)),
        ("fantasy_player_ids", load_ff_playerids_safe),
        ("ff_opportunity_weekly", lambda: load_ff_opportunity_safe(seasons)),
    ]

    rows = []
    for name, loader in loaders:
        logger.info("Auditing dataset: %s", name)
        result = loader()
        rows.append(_summarize_dataset(name, result, seasons))

    inventory_df = pd.DataFrame(rows)
    inventory_path = AUDIT_DIR / "source_inventory.csv"
    inventory_df.to_csv(inventory_path, index=False)

    markdown_path = AUDIT_DIR / "data_audit.md"
    write_markdown(markdown_path, _build_markdown(inventory_df, seasons))

    return inventory_path, markdown_path, inventory_df
