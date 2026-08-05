from __future__ import annotations

import pandas as pd

from fantasy_nfl.analysis.html_board import write_draft_board_html


def test_interactive_board_contains_sort_filters_and_shortlist(tmp_path):
    board = pd.DataFrame(
        [
            {
                "value_board_rank": 1,
                "player_name": "A.J. Test",
                "position": "WR",
                "team": "NYJ",
                "market_rank": 42.5,
                "market_metric": "adp",
                "model_rank": 20,
                "rank_value": 22.5,
                "projected_points_q50": 190,
                "projected_points_q10": 120,
                "projected_points_q90": 260,
                "beat_market_probability": 0.64,
                "bust_probability": 0.18,
                "risk_adjusted_value_score": 1.25,
                "recommendation": "Strong value",
            }
        ]
    )
    path = write_draft_board_html(board, tmp_path / "board.html")
    html = path.read_text(encoding="utf-8")
    assert 'data-column="market_rank"' in html
    assert 'data-type="number"' in html
    assert 'id="position"' in html
    assert 'id="recommendation"' in html
    assert 'id="max-rank"' in html
    assert 'id="reset"' in html
    assert 'id="show-shortlist"' in html
    assert 'class="rec-strong-value"' in html
    assert 'data-player="A.J. Test|WR"' in html
