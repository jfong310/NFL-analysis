import pandas as pd

from fantasy_nfl.transform.scoring import score_player_weeks


def test_scoring_math_and_mutation():
    df = pd.DataFrame([
        {
            "passing_yards": 250,
            "passing_tds": 2,
            "interceptions": 1,
            "rushing_yards": 30,
            "rushing_tds": 1,
            "receptions": 5,
            "receiving_yards": 70,
            "receiving_tds": 1,
            "fumbles_lost": 1,
        }
    ])
    original = df.copy(deep=True)
    scored, _ = score_player_weeks(df)
    assert scored.loc[0, "fantasy_points_ppr"] == 41
    assert scored.loc[0, "fantasy_points_half_ppr"] == 38.5
    assert scored.loc[0, "fantasy_points_standard"] == 36
    pd.testing.assert_frame_equal(df, original)


def test_missing_optional_and_bonus_columns():
    df = pd.DataFrame([
        {"passing_tds": 1, "special_teams_tds": 1, "return_tds": 1, "offensive_fumble_recovery_tds": 1, "passing_2pt_conversions": 1}
    ])
    scored, meta = score_player_weeks(df)
    assert scored.loc[0, "fantasy_points_ppr"] == 4 + 6 + 6 + 6 + 2
    assert "rushing_yards" in meta.scoring_columns_missing
