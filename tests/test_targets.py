import pandas as pd

from fantasy_nfl.transform.targets import build_player_season_targets


def test_targets_aggregation_filtering_duplicates_and_replacement():
    df = pd.DataFrame([
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 1, "season_type": "REG", "team": "X", "fantasy_points": 0, "fantasy_points_ppr": 10, "fantasy_points_half_ppr": 9, "fantasy_points_standard": 8, "carries": 5, "targets": 0, "attempts": 0, "receptions": 0},
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 2, "season_type": "REG", "team": "Y", "fantasy_points": 20, "fantasy_points_ppr": 20, "fantasy_points_half_ppr": 19, "fantasy_points_standard": 18, "carries": 0, "targets": 3, "attempts": 0, "receptions": 2},
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 2, "season_type": "REG", "team": "Y", "fantasy_points": 20, "fantasy_points_ppr": 20, "fantasy_points_half_ppr": 19, "fantasy_points_standard": 18, "carries": 0, "targets": 3, "attempts": 0, "receptions": 2},
        {"player_id": "a", "player_name": "A", "position": "RB", "season": 2024, "week": 3, "season_type": "POST", "team": "Y", "fantasy_points": 10, "fantasy_points_ppr": 10, "fantasy_points_half_ppr": 9, "fantasy_points_standard": 8, "carries": 2, "targets": 0, "attempts": 0, "receptions": 0},
        {"player_id": "b", "player_name": "B", "position": "RB", "season": 2024, "week": 1, "season_type": "REG", "team": "Z", "fantasy_points": 5, "fantasy_points_ppr": 5, "fantasy_points_half_ppr": 5, "fantasy_points_standard": 5, "carries": 1, "targets": 0, "attempts": 0, "receptions": 0},
    ])
    season_df, meta = build_player_season_targets(df)
    a = season_df[season_df.player_id == "a"].iloc[0]
    assert meta["duplicate_count"] == 1
    assert a["weeks_active"] == 2
    assert a["games_played"] == 2  # week1 usage with zero points still counts
    assert a["total_fantasy_points_ppr"] == 30
    assert a["points_per_game_ppr"] == 15
    assert a["primary_team"] == "Y"
    assert a["positional_finish_ppr"] == 1
    assert "replacement_adjusted_points_ppr" in season_df.columns
