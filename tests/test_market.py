from __future__ import annotations

import pandas as pd

from fantasy_nfl.analysis.draft_value import build_draft_value_board
from fantasy_nfl.ingest.market import append_snapshot, parse_fantasypros_adp_html
from fantasy_nfl.transform.market import match_market_players, normalize_player_name


def test_normalize_player_name_handles_punctuation_accents_and_suffixes():
    assert normalize_player_name("Amon-Ra St. Brown Jr.") == "amonrastbrown"
    assert normalize_player_name("José Núñez III") == "josenunez"


def test_parse_fantasypros_embedded_report():
    html = '''<script>window.FP.reportConfig = {"subtitle":"2026 Rankings: Consensus of 2 Sources","table":{"rows":[{"id":123,"rank":1,"player":{"name":"Test Runner","team":"NYJ (9)"},"pos":"RB1","avg":1.5}]}};</script>'''
    frame = parse_fantasypros_adp_html(html, snapshot_date="2026-08-05")
    row = frame.iloc[0]
    assert row["fantasypros_id"] == 123
    assert row["position"] == "RB"
    assert row["positional_rank"] == 1
    assert row["market_rank"] == 1.5
    assert row["snapshot_date"] == "2026-08-05"


def test_append_snapshot_is_idempotent(tmp_path):
    html = '''<script>window.FP.reportConfig = {"subtitle":"2026 Rankings","table":{"rows":[{"id":1,"rank":1,"player":{"name":"One","team":"A"},"pos":"WR1","avg":2}]}};</script>'''
    frame = parse_fantasypros_adp_html(html, snapshot_date="2026-08-05")
    path = tmp_path / "snapshots.parquet"
    append_snapshot(frame, path)
    assert len(append_snapshot(frame, path)) == 1


def test_player_matching_prefers_id_then_name_position():
    market = pd.DataFrame({
        "snapshot_date": ["2026-08-05"] * 3, "fantasypros_id": [100, None, 999],
        "player_name": ["ID Winner", "A.J. Brown", "Nobody"], "position": ["WR", "WR", "RB"],
        "team": ["A", "B", "C"], "market_rank": [1, 2, 3], "market_metric": ["adp"] * 3,
    })
    ids = pd.DataFrame({
        "fantasypros_id": [100, 200], "gsis_id": ["p1", "p2"],
        "name": ["Different Name", "AJ Brown"], "position": ["WR", "WR"], "db_season": [2026, 2026],
    })
    matched, report = match_market_players(market, ids)
    assert matched.loc[0, "player_id"] == "p1"
    assert matched.loc[1, "player_id"] == "p2"
    assert report["join_status"].tolist() == ["matched", "matched", "unmatched"]


def test_value_board_rewards_players_ranked_ahead_of_market():
    rows, projections = [], []
    for i in range(12):
        player_id = f"p{i}"
        rows.append({
            "snapshot_date": "2026-08-05", "fantasypros_id": i, "player_name": f"Player {i}",
            "position": "RB", "team": "T", "market_rank": i + 1, "positional_rank": i + 1,
            "market_metric": "adp", "player_id": player_id, "join_status": "matched",
        })
        median = 180 - i * 5 + (35 if i == 8 else 0)
        projections.append({
            "player_id": player_id, "projected_total_fantasy_points": median,
            "projected_points_per_game": median / 16, "projected_games_played": 16,
            "projected_points_q10": median - 35, "projected_points_q50": median,
            "projected_points_q90": median + 35, "projected_positional_finish": i + 1,
        })
    board = build_draft_value_board(pd.DataFrame(rows), pd.DataFrame(projections))
    sleeper = board.loc[board["player_id"] == "p8"].iloc[0]
    assert sleeper["rank_value"] > 0
    assert sleeper["risk_adjusted_value_score"] > 0
    assert board["beat_market_probability"].between(0, 1).all()
    assert board["bust_probability"].between(0, 1).all()
