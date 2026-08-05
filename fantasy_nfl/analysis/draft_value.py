"""Model-versus-market value, uncertainty, and recommendation scoring."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPLACEMENT_RANKS = {"QB": 13, "RB": 37, "WR": 49, "TE": 13}


def _piecewise_cdf(threshold: pd.Series, q10: pd.Series, q50: pd.Series, q90: pd.Series) -> pd.Series:
    """Approximate a CDF from the model's 10th, 50th, and 90th percentiles."""
    x = threshold.to_numpy(float)
    a = q10.to_numpy(float)
    b = np.maximum(q50.to_numpy(float), a + 1e-6)
    c = np.maximum(q90.to_numpy(float), b + 1e-6)
    result = np.empty(len(x), dtype=float)
    low = x <= a
    mid1 = (x > a) & (x <= b)
    mid2 = (x > b) & (x <= c)
    high = x > c
    result[low] = 0.10 * np.clip(x[low] / np.maximum(a[low], 1e-6), 0, 1)
    result[mid1] = 0.10 + 0.40 * (x[mid1] - a[mid1]) / (b[mid1] - a[mid1])
    result[mid2] = 0.50 + 0.40 * (x[mid2] - b[mid2]) / (c[mid2] - b[mid2])
    result[high] = 0.90 + 0.10 * np.clip((x[high] - c[high]) / np.maximum(c[high], 1), 0, 1)
    return pd.Series(np.clip(result, 0, 1), index=threshold.index)


def _market_curve(group: pd.DataFrame) -> pd.Series:
    """Estimate the point level implied by positional market rank without look-ahead."""
    ordered = group.sort_values("positional_rank", kind="stable")
    smoothed = ordered["projected_points_q50"].rolling(9, center=True, min_periods=3).median()
    smoothed = smoothed.fillna(ordered["projected_points_q50"].expanding().median())
    # A later positional pick should never imply more points than an earlier pick.
    smoothed = smoothed.cummin()
    return smoothed.reindex(group.index)


def build_draft_value_board(matched_market: pd.DataFrame, projections: pd.DataFrame) -> pd.DataFrame:
    """Join projections to market price and calculate practical draft value metrics."""
    market = matched_market.loc[
        (matched_market["join_status"] == "matched") & matched_market["player_id"].notna()
    ].copy()
    market = market.sort_values("market_rank").drop_duplicates("player_id", keep="first")
    projection_columns = [
        "player_id",
        "projected_total_fantasy_points",
        "projected_points_per_game",
        "projected_games_played",
        "projected_points_q10",
        "projected_points_q50",
        "projected_points_q90",
        "projected_positional_finish",
    ]
    board = market.merge(projections[projection_columns], on="player_id", how="inner", validate="one_to_one")
    if board.empty:
        raise ValueError("No market players matched the projection table")

    replacement = {}
    for position, group in board.groupby("position"):
        rank = REPLACEMENT_RANKS.get(position, max(1, len(group)))
        ordered = group["projected_points_q50"].sort_values(ascending=False)
        replacement[position] = float(ordered.iloc[min(rank, len(ordered)) - 1])
    board["replacement_points"] = board["position"].map(replacement)
    board["projected_points_above_replacement"] = (
        board["projected_points_q50"] - board["replacement_points"]
    )
    board["model_rank"] = board["projected_points_above_replacement"].rank(
        ascending=False, method="min"
    )
    board["model_positional_rank"] = board.groupby("position")[
        "projected_points_q50"
    ].rank(ascending=False, method="min")
    board["rank_value"] = board["market_rank"] - board["model_rank"]
    board["rank_value_rate"] = board["rank_value"] / board["market_rank"].clip(lower=12)
    board["positional_rank_value"] = board["positional_rank"] - board["model_positional_rank"]

    board["market_expected_points"] = np.nan
    for indices in board.groupby("position").groups.values():
        group = board.loc[indices]
        board.loc[indices, "market_expected_points"] = _market_curve(group)
    board["expected_value_points"] = (
        board["projected_points_q50"] - board["market_expected_points"]
    )
    board["beat_market_probability"] = 1 - _piecewise_cdf(
        board["market_expected_points"],
        board["projected_points_q10"],
        board["projected_points_q50"],
        board["projected_points_q90"],
    )
    bust_threshold = 0.75 * board["market_expected_points"]
    board["bust_probability"] = _piecewise_cdf(
        bust_threshold,
        board["projected_points_q10"],
        board["projected_points_q50"],
        board["projected_points_q90"],
    )
    board["upside_points"] = (board["projected_points_q90"] - board["market_expected_points"]).clip(lower=0)
    board["downside_points"] = (board["market_expected_points"] - board["projected_points_q10"]).clip(lower=0)
    board["uncertainty_width"] = board["projected_points_q90"] - board["projected_points_q10"]
    raw = (
        board["expected_value_points"]
        + 0.20 * board["upside_points"]
        - 0.20 * board["downside_points"]
        + 25.0 * board["rank_value_rate"]
        - 8.0 * board["bust_probability"]
    )
    scale = raw.std(ddof=0)
    board["risk_adjusted_value_score"] = (raw - raw.mean()) / (scale if scale else 1.0)

    score = board["risk_adjusted_value_score"]
    delta = board["rank_value"]
    conditions = [
        (score >= 1.0) & (delta >= 12),
        (score >= 0.35) & (delta >= 5),
        (board["beat_market_probability"] >= 0.55) & (board["uncertainty_width"] >= board["uncertainty_width"].quantile(0.75)),
        (score <= -1.0) & (delta <= -12),
        (score <= -0.35) & (delta <= -5),
    ]
    labels = ["Strong value", "Value", "High-risk upside", "Avoid", "Overpriced"]
    board["recommendation"] = np.select(conditions, labels, default="Fair price")
    board["value_board_rank"] = board["risk_adjusted_value_score"].rank(
        ascending=False, method="min"
    ).astype(int)
    return board.sort_values(["value_board_rank", "market_rank"], kind="stable").reset_index(drop=True)


def write_draft_board_html(board: pd.DataFrame, path: Path) -> Path:
    """Write a standalone, searchable HTML draft board."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    display_columns = [
        "value_board_rank", "player_name", "position", "team", "market_rank", "market_metric",
        "model_rank", "rank_value", "projected_points_q50", "projected_points_q10",
        "projected_points_q90", "beat_market_probability", "bust_probability",
        "risk_adjusted_value_score", "recommendation",
    ]
    display = board[display_columns].copy()
    display = display.round(
        {"market_rank": 1, "model_rank": 0, "rank_value": 1, "projected_points_q50": 1,
         "projected_points_q10": 1, "projected_points_q90": 1,
         "beat_market_probability": 3, "bust_probability": 3,
         "risk_adjusted_value_score": 2}
    )
    table = display.to_html(index=False, classes="draft-board", table_id="draft-board")
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fantasy NFL Draft Value Board</title><style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#17212b}} h1{{margin-bottom:.25rem}}
.note{{color:#536270;margin-bottom:1rem}} input{{padding:.55rem;width:min(28rem,90%);margin-bottom:1rem}}
table{{border-collapse:collapse;width:100%;font-size:.86rem}} th,td{{padding:.45rem;border-bottom:1px solid #dce2e8;text-align:right}}
th:nth-child(2),td:nth-child(2),th:last-child,td:last-child{{text-align:left}} th{{position:sticky;top:0;background:#15324b;color:white}}
tr:hover{{background:#eef6fb}}
</style></head><body><h1>Fantasy NFL Draft Value Board</h1>
<p class="note">Positive rank value means the model values a player earlier than the market. Search by player, position, team, or recommendation.</p>
<input id="filter" placeholder="Filter draft board…" onkeyup="filterRows()">{table}
<script>function filterRows(){{const q=document.getElementById('filter').value.toLowerCase();document.querySelectorAll('#draft-board tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none');}}</script>
</body></html>"""
    path.write_text(html, encoding="utf-8")
    return path
