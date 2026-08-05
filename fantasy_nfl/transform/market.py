"""Normalize and match market player records to nflverse player identifiers."""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalize_player_name(value: object) -> str:
    """Create a conservative comparison key for football player names."""
    if value is None or pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    parts = text.split()
    while parts and parts[-1] in {"jr", "sr", "ii", "iii", "iv", "v"}:
        parts.pop()
    return "".join(parts)


def _latest_crosswalk(crosswalk: pd.DataFrame) -> pd.DataFrame:
    required = {"fantasypros_id", "gsis_id", "name", "position"}
    missing = required - set(crosswalk.columns)
    if missing:
        raise ValueError(f"Player ID crosswalk missing columns: {sorted(missing)}")
    result = crosswalk.copy()
    result["fantasypros_id"] = pd.to_numeric(result["fantasypros_id"], errors="coerce")
    result["normalized_name"] = result["name"].map(normalize_player_name)
    result["position"] = result["position"].astype(str).str.upper()
    if "db_season" in result:
        result = result.sort_values("db_season", ascending=False, na_position="last")
    return result.drop_duplicates(
        ["fantasypros_id", "gsis_id", "normalized_name", "position"], keep="first"
    )


def match_market_players(
    market: pd.DataFrame, crosswalk: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Match by FantasyPros ID first and exact normalized name/position second."""
    required = {"fantasypros_id", "player_name", "position"}
    missing = required - set(market.columns)
    if missing:
        raise ValueError(f"Market data missing columns: {sorted(missing)}")
    result = market.copy().reset_index(drop=True)
    result["fantasypros_id"] = pd.to_numeric(result["fantasypros_id"], errors="coerce")
    result["position"] = result["position"].astype(str).str.upper()
    result["normalized_name"] = result["player_name"].map(normalize_player_name)
    ids = _latest_crosswalk(crosswalk)
    by_id = (
        ids.dropna(subset=["fantasypros_id", "gsis_id"])
        .drop_duplicates("fantasypros_id", keep="first")
        .set_index("fantasypros_id")
    )
    result["player_id"] = result["fantasypros_id"].map(by_id["gsis_id"])
    result["match_method"] = result["player_id"].notna().map(
        {True: "fantasypros_id", False: "unmatched"}
    )
    name_map = (
        ids.dropna(subset=["gsis_id"])
        .loc[lambda x: x["normalized_name"].ne("")]
        .drop_duplicates(["normalized_name", "position"], keep=False)
        .set_index(["normalized_name", "position"])["gsis_id"]
    )
    for index in result.index[result["player_id"].isna()]:
        key = (result.at[index, "normalized_name"], result.at[index, "position"])
        if key in name_map.index:
            result.at[index, "player_id"] = name_map.loc[key]
            result.at[index, "match_method"] = "normalized_name_position"
    duplicate_match = result["player_id"].notna() & result["player_id"].duplicated(keep=False)
    result["join_status"] = "matched"
    result.loc[result["player_id"].isna(), "join_status"] = "unmatched"
    result.loc[duplicate_match, "join_status"] = "duplicate_player_id"
    report_columns = [
        "snapshot_date", "fantasypros_id", "player_name", "normalized_name", "position",
        "team", "market_rank", "market_metric", "player_id", "match_method", "join_status",
    ]
    return result, result[report_columns].copy()
