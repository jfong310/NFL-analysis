import pandas as pd

from fantasy_nfl.audit.feature_audit import build_leakage_checks
from fantasy_nfl.transform.features import (
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMNS,
    build_model_feature_table,
)
from fantasy_nfl.transform.targets import build_player_season_targets


def feature_weeks():
    rows = []
    values = {
        ("A", 2023): [10.0, 20.0],
        ("A", 2024): [30.0],
        ("B", 2023): [5.0],
    }
    for (player, season), scores in values.items():
        for week, score in enumerate(scores, start=1):
            rows.append(
                {
                    "player_id": player,
                    "player_name": f"Player {player}",
                    "season": season,
                    "week": week,
                    "position": "WR",
                    "team": player,
                    "fantasy_points_standard": score,
                    "fantasy_points_half_ppr": score,
                    "fantasy_points_ppr": score,
                    "targets": 5.0 + week,
                    "carries": 1.0,
                    "passing_attempts": 0.0,
                    "receptions": 4.0,
                    "opportunities": 6.0 + week,
                    "snap_share": 0.75,
                    "total_fantasy_points_exp": score - 2.0,
                    "injury_status": "Questionable" if player == "B" else None,
                    "birth_date": "2000-01-01",
                    "years_exp": float(season - 2021),
                }
            )
    return pd.DataFrame(rows)


def schedules():
    return pd.DataFrame(
        [
            {
                "season": 2023,
                "game_type": "REG",
                "game_id": "2023_01_A_B",
                "home_team": "A",
                "away_team": "B",
                "home_score": 24,
                "away_score": 17,
            },
            {
                "season": 2024,
                "game_type": "REG",
                "game_id": "2024_01_A_B",
                "home_team": "A",
                "away_team": "B",
                "home_score": 28,
                "away_score": 20,
            },
        ]
    )


def players():
    return pd.DataFrame(
        {
            "gsis_id": ["A", "B"],
            "rookie_season": [2022, 2023],
        }
    )


def build_table(weeks=None):
    weeks = feature_weeks() if weeks is None else weeks
    targets = build_player_season_targets(
        weeks, replacement_ranks={"WR": 2}
    )
    return build_model_feature_table(weeks, targets, schedules(), players())


def test_feature_rows_use_prior_season_and_create_prediction_row():
    table = build_table()
    a_2024 = table[(table.player_id == "A") & (table.prediction_season == 2024)].iloc[0]
    a_2025 = table[(table.player_id == "A") & (table.prediction_season == 2025)].iloc[0]

    assert a_2024.feature_source_season == 2023
    assert a_2024.prior_year_points_per_game == 15.0
    assert a_2024.recent_5_points_per_game == 15.0
    assert a_2024.target_total_fantasy_points == 30.0
    assert a_2024.prior_team_points_per_game == 24.0
    assert a_2024.years_experience == 2.0
    assert a_2025.is_prediction_row
    assert a_2025[TARGET_COLUMNS].isna().all()


def test_known_zero_outcome_is_filled_for_absent_player():
    table = build_table()
    b_2024 = table[(table.player_id == "B") & (table.prediction_season == 2024)].iloc[0]
    assert b_2024.target_observed
    assert b_2024.target_games_played == 0.0
    assert b_2024.target_total_fantasy_points == 0.0


def test_future_season_does_not_change_earlier_features():
    all_weeks = feature_weeks()
    earlier = all_weeks[all_weeks.season == 2023].copy()
    early_table = build_table(earlier)
    full_table = build_table(all_weeks)
    early_row = early_table[
        (early_table.player_id == "A") & (early_table.prediction_season == 2024)
    ][MODEL_FEATURE_COLUMNS].reset_index(drop=True)
    full_row = full_table[
        (full_table.player_id == "A") & (full_table.prediction_season == 2024)
    ][MODEL_FEATURE_COLUMNS].reset_index(drop=True)
    pd.testing.assert_frame_equal(early_row, full_row)


def test_leakage_checks_pass_and_keys_are_unique():
    table = build_table()
    checks = build_leakage_checks(table)
    assert checks["passed"].all()
    assert not table.duplicated(["player_id", "prediction_season"]).any()
