import pandas as pd

from fantasy_nfl.transform.scoring import score_player_weeks


def _row():
    return pd.DataFrame([
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
            "passing_2pt_conversions": 1,
            "special_teams_tds": 1,
        }
    ])


def test_scoring_math_all_formats():
    scored, _ = score_player_weeks(_row())
    assert scored.loc[0, "fantasy_points_ppr"] == 49
    assert scored.loc[0, "fantasy_points_half_ppr"] == 46.5
    assert scored.loc[0, "fantasy_points_standard"] == 44


def test_missing_optional_columns_as_zero_and_no_mutation():
    df = _row().drop(columns=["passing_2pt_conversions", "special_teams_tds"]) 
    before_cols = set(df.columns)
    scored, meta = score_player_weeks(df)
    assert set(df.columns) == before_cols
    assert "passing_2pt_conversions" in meta.scoring_columns_missing
    assert scored.loc[0, "fantasy_points_ppr"] == 41
