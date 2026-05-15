import pandas as pd

from fantasy_nfl.transform.targets import build_player_season_targets


def test_targets_aggregation_and_filters():
    df = pd.DataFrame([
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 1, "season_type": "REG", "team": "X", "fantasy_points": 10, "fantasy_points_ppr": 10, "fantasy_points_half_ppr": 9, "fantasy_points_standard": 8, "carries": 1},
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 1, "season_type": "REG", "team": "X", "fantasy_points": 10, "fantasy_points_ppr": 10, "fantasy_points_half_ppr": 9, "fantasy_points_standard": 8, "carries": 1},
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 2, "season_type": "REG", "team": "Y", "fantasy_points": 0, "fantasy_points_ppr": 0, "fantasy_points_half_ppr": 0, "fantasy_points_standard": 0, "targets": 1},
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 3, "season_type": "POST", "team": "Y", "fantasy_points": 20, "fantasy_points_ppr": 20, "fantasy_points_half_ppr": 20, "fantasy_points_standard": 20, "carries": 4},
        {"player_id": "b", "player_name": "B", "position": "RB", "season": 2024, "week": 1, "season_type": "REG", "team": "Z", "fantasy_points": 5, "fantasy_points_ppr": 5, "fantasy_points_half_ppr": 4, "fantasy_points_standard": 3, "carries": 1},
    ])
    season, meta = build_player_season_targets(df)
    a = season[season["player_id"] == "a"].iloc[0]
    assert meta["duplicate_count"] == 1
    assert a["weeks_active"] == 2
    assert a["games_played"] == 2
    assert a["total_fantasy_points_ppr"] == 10
    assert a["points_per_game_ppr"] == 5
    assert a["primary_team"] == "Y"
    assert a["replacement_adjusted_points_ppr"] >= 0
    assert a["positional_finish_ppr"] == 1
