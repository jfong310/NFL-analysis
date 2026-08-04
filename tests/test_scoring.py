import pandas as pd
import pytest

from fantasy_nfl.transform.scoring import (
    IDENTITY_COLUMNS,
    SCORING_STAT_COLUMNS,
    build_player_week_scored,
    calculate_fantasy_points,
)


def stat_frame(**values):
    row = {column: 0 for column in SCORING_STAT_COLUMNS}
    row.update(values)
    return pd.DataFrame([row])


def weekly_row(**values):
    row = {
        "player_id": "00-1",
        "player_display_name": "Example Player",
        "season": 2024,
        "week": 1,
        "season_type": "REG",
        "game_id": "2024_01_A_B",
        "team": "JAC",
        "opponent_team": "B",
        "position": "WR",
        "fantasy_points": 16.0,
        "fantasy_points_ppr": 21.0,
    }
    row.update({column: 0 for column in SCORING_STAT_COLUMNS})
    row.update(values)
    return row


def test_standard_half_ppr_and_ppr_known_example():
    frame = stat_frame(receiving_yards=100, receiving_tds=1, receptions=5)
    assert calculate_fantasy_points(frame, "standard").iloc[0] == 16.0
    assert calculate_fantasy_points(frame, "half_ppr").iloc[0] == 18.5
    assert calculate_fantasy_points(frame, "ppr").iloc[0] == 21.0


def test_passing_two_point_special_teams_and_fumble_scoring():
    frame = stat_frame(
        passing_yards=250,
        passing_tds=2,
        passing_interceptions=1,
        rushing_yards=20,
        passing_2pt_conversions=1,
        special_teams_tds=1,
        sack_fumbles_lost=1,
    )
    assert calculate_fantasy_points(frame, "standard").iloc[0] == 24.0


def test_unknown_format_and_missing_columns_are_rejected():
    with pytest.raises(ValueError, match="Unknown scoring format"):
        calculate_fantasy_points(stat_frame(), "bonus")
    with pytest.raises(ValueError, match="Missing scoring columns"):
        calculate_fantasy_points(pd.DataFrame({"receptions": [1]}), "ppr")


def test_scored_table_filters_scope_normalizes_and_matches_reference():
    regular = weekly_row(receiving_yards=100, receiving_tds=1, receptions=5)
    postseason = weekly_row(week=19, season_type="POST")
    defender = weekly_row(player_id="00-2", position="LB")
    source = pd.DataFrame([regular, postseason, defender])

    scored = build_player_week_scored(source)

    assert len(scored) == 1
    assert scored.loc[0, "team"] == "JAX"
    assert scored.loc[0, "fantasy_points_standard"] == 16.0
    assert scored.loc[0, "fantasy_points_ppr"] == 21.0
    assert scored.loc[0, "fantasy_points"] == 21.0
    assert scored.loc[0, "nflverse_fantasy_points_standard"] == 16.0
    assert scored.loc[0, "nflverse_fantasy_points_ppr"] == 21.0


def test_duplicate_player_week_is_rejected():
    source = pd.DataFrame([weekly_row(), weekly_row()])
    with pytest.raises(ValueError, match="duplicate player-week"):
        build_player_week_scored(source)
