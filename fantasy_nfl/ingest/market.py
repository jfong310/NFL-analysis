"""FantasyPros market-data ingestion and dated snapshot persistence."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

FANTASYPROS_PPR_ADP_URL = "https://www.fantasypros.com/nfl/adp/ppr-overall.php"
MARKET_COLUMNS = [
    "snapshot_date",
    "season",
    "fantasypros_id",
    "player_name",
    "position",
    "team",
    "market_rank",
    "positional_rank",
    "market_metric",
    "scoring_format",
    "source",
    "source_url",
    "retrieved_at_utc",
]


def _report_config(html: str) -> dict[str, Any]:
    marker = "window.FP.reportConfig = "
    start = html.find(marker)
    if start < 0:
        raise ValueError("FantasyPros reportConfig was not found in the response")
    value, _ = json.JSONDecoder().raw_decode(html[start + len(marker) :].lstrip())
    return value


def parse_fantasypros_adp_html(
    html: str,
    *,
    snapshot_date: date | str | None = None,
    source_url: str = FANTASYPROS_PPR_ADP_URL,
) -> pd.DataFrame:
    """Parse the JSON report embedded in a FantasyPros PPR ADP page."""
    config = _report_config(html)
    rows = config.get("table", {}).get("rows", [])
    if not rows:
        raise ValueError("FantasyPros report contained no ADP rows")
    season_match = re.search(r"(20\d{2})", str(config.get("subtitle", "")))
    season = int(season_match.group(1)) if season_match else datetime.now().year
    snap = pd.Timestamp(snapshot_date or date.today()).date().isoformat()
    retrieved = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []
    for row in rows:
        player = row.get("player") or {}
        position_text = str(row.get("pos") or "")
        position_match = re.match(r"([A-Za-z]+)(\d+)?", position_text)
        team_text = str(player.get("team") or "")
        records.append(
            {
                "snapshot_date": snap,
                "season": season,
                "fantasypros_id": pd.to_numeric(row.get("id") or player.get("id"), errors="coerce"),
                "player_name": player.get("name"),
                "position": position_match.group(1).upper() if position_match else None,
                "team": team_text.split(" (")[0] or None,
                "market_rank": pd.to_numeric(row.get("avg", row.get("rank")), errors="coerce"),
                "positional_rank": (
                    float(position_match.group(2))
                    if position_match and position_match.group(2)
                    else None
                ),
                "market_metric": "adp",
                "scoring_format": "ppr",
                "source": "FantasyPros consensus ADP",
                "source_url": source_url,
                "retrieved_at_utc": retrieved,
            }
        )
    frame = pd.DataFrame(records, columns=MARKET_COLUMNS)
    return frame.sort_values("market_rank", kind="stable").reset_index(drop=True)


def fetch_fantasypros_adp(
    *, snapshot_date: date | str | None = None, timeout: int = 30
) -> pd.DataFrame:
    """Fetch the official FantasyPros page and parse its visible consensus ADP rows."""
    import requests

    response = requests.get(
        FANTASYPROS_PPR_ADP_URL,
        timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 (compatible; fantasy-nfl-research/1.0)"},
    )
    response.raise_for_status()
    return parse_fantasypros_adp_html(response.text, snapshot_date=snapshot_date)


def load_fantasypros_ppr_ecr() -> pd.DataFrame:
    """Load the public nflverse copy of FantasyPros PPR expert consensus rankings."""
    import nflreadpy

    raw = nflreadpy.load_ff_rankings("draft")
    if hasattr(raw, "to_pandas"):
        raw = raw.to_pandas()
    selected = raw.loc[
        (raw["page_type"] == "redraft-overall")
        & raw["fp_page"].astype(str).str.endswith("/ppr-cheatsheets.php")
    ].copy()
    if selected.empty:
        raise ValueError("Public FantasyPros PPR ECR feed returned no rows")
    selected["scrape_date"] = pd.to_datetime(selected["scrape_date"])
    selected = selected.loc[selected["scrape_date"] == selected["scrape_date"].max()].copy()
    selected["position"] = selected["pos"].astype(str).str.upper()
    selected["market_rank"] = pd.to_numeric(selected["ecr"], errors="coerce")
    selected["positional_rank"] = selected.groupby("position")["market_rank"].rank(
        method="first"
    )
    retrieved = datetime.now(timezone.utc).isoformat()
    result = pd.DataFrame(
        {
            "snapshot_date": selected["scrape_date"].dt.date.astype(str),
            "season": selected["scrape_date"].dt.year,
            "fantasypros_id": pd.to_numeric(selected["id"], errors="coerce"),
            "player_name": selected["player"],
            "position": selected["position"],
            "team": selected["team"],
            "market_rank": selected["market_rank"],
            "positional_rank": selected["positional_rank"],
            "market_metric": "ecr",
            "scoring_format": "ppr",
            "source": "FantasyPros PPR expert consensus via nflverse",
            "source_url": "https://www.fantasypros.com/nfl/rankings/ppr-cheatsheets.php",
            "retrieved_at_utc": retrieved,
        }
    )
    return result[MARKET_COLUMNS].sort_values("market_rank", kind="stable").reset_index(drop=True)


def load_market_file(path: Path, *, snapshot_date: date | str | None = None) -> pd.DataFrame:
    """Load a full FantasyPros export or a previously standardized snapshot."""
    path = Path(path)
    frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    if set(MARKET_COLUMNS).issubset(frame.columns):
        result = frame[MARKET_COLUMNS].copy()
        if snapshot_date is not None:
            result["snapshot_date"] = pd.Timestamp(snapshot_date).date().isoformat()
        return result
    aliases = {
        "Player": "player_name",
        "PLAYER NAME": "player_name",
        "POS": "position_text",
        "Team": "team",
        "AVG": "market_rank",
        "Rank": "market_rank",
        "FantasyPros ID": "fantasypros_id",
    }
    frame = frame.rename(columns={key: value for key, value in aliases.items() if key in frame})
    required = {"player_name", "market_rank"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Market file missing columns: {sorted(missing)}")
    position_text = frame.get("position", frame.get("position_text", "")).astype(str)
    position = position_text.str.extract(r"([A-Za-z]+)", expand=False).str.upper()
    positional_rank = pd.to_numeric(
        position_text.str.extract(r"(\d+)", expand=False), errors="coerce"
    )
    snap = pd.Timestamp(snapshot_date or date.today()).date().isoformat()
    result = pd.DataFrame(
        {
            "snapshot_date": snap,
            "season": pd.Timestamp(snap).year,
            "fantasypros_id": pd.to_numeric(frame.get("fantasypros_id"), errors="coerce"),
            "player_name": frame["player_name"],
            "position": position,
            "team": frame.get("team"),
            "market_rank": pd.to_numeric(frame["market_rank"], errors="coerce"),
            "positional_rank": positional_rank,
            "market_metric": "adp",
            "scoring_format": "ppr",
            "source": "FantasyPros imported export",
            "source_url": str(path),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    result["positional_rank"] = result["positional_rank"].fillna(
        result.groupby("position")["market_rank"].rank(method="first")
    )
    return result[MARKET_COLUMNS]


def append_snapshot(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Append a dated market snapshot while making repeat runs idempotent."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=MARKET_COLUMNS)
    combined = pd.concat([prior, frame[MARKET_COLUMNS]], ignore_index=True)
    key = ["snapshot_date", "fantasypros_id", "player_name", "market_metric", "scoring_format"]
    combined = combined.drop_duplicates(key, keep="last").sort_values(
        ["snapshot_date", "market_rank"], kind="stable"
    )
    combined.to_parquet(path, index=False)
    return combined.reset_index(drop=True)
