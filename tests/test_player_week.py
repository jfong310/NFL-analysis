import pandas as pd
import pytest

from fantasy_nfl.transform.player_week import build_player_week


def datasets():
    return {
        "player_stats_weekly": pd.DataFrame({
            "player_id": ["00-1"], "player_display_name": ["Example Player"], "season": [2024],
            "week": [1], "season_type": ["REG"], "game_id": ["2024_01_A_B"], "position": ["WR"],
            "team": ["JAC"], "opponent_team": ["A"], "fantasy_points": [10.0],
            "fantasy_points_ppr": [15.0], "targets": [6], "receptions": [5],
        }),
        "players": pd.DataFrame({"gsis_id": ["00-1"], "birth_date": ["2000-01-01"], "pfr_id": ["ExamPl00"]}),
        "rosters": pd.DataFrame({"gsis_id": ["00-1"], "season": [2024], "week": [1], "years_exp": [2]}),
        "schedules": pd.DataFrame({"game_id": ["2024_01_A_B"], "gameday": ["2024-09-01"], "home_team": ["B"], "away_team": ["A"]}),
        "injuries": pd.DataFrame({"gsis_id": ["00-1"], "season": [2024], "week": [1], "report_status": ["Questionable"]}),
        "ff_opportunity_weekly": pd.DataFrame({"player_id": ["00-1"], "season": [2024], "week": [1], "total_fantasy_points_exp": [12.5]}),
        "fantasy_player_ids": pd.DataFrame({"gsis_id": ["00-1"], "pfr_id": ["ExamPl00"]}),
        "snap_counts": pd.DataFrame({"pfr_player_id": ["ExamPl00"], "game_id": ["2024_01_A_B"], "offense_snaps": [52], "offense_pct": [0.8]}),
    }


def test_build_player_week_schema_and_joins():
    player_week, report = build_player_week(datasets())

    assert len(player_week) == 1
    assert player_week.loc[0, "team"] == "JAX"
    assert player_week.loc[0, "fantasy_points"] == 15.0
    assert player_week.loc[0, "snap_count"] == 52
    assert player_week.loc[0, "injury_status"] == "Questionable"
    assert not player_week.duplicated(["player_id", "season", "week"]).any()
    assert set(report["dataset"]) >= {"players", "rosters", "schedules", "injuries", "snap_counts"}
    assert report.loc[report["dataset"] == "snap_counts", "match_rate"].iloc[0] == 1.0


def test_duplicate_player_week_is_rejected():
    source = datasets()
    source["player_stats_weekly"] = pd.concat(
        [source["player_stats_weekly"], source["player_stats_weekly"]], ignore_index=True
    )
    with pytest.raises(ValueError, match="duplicate player-week"):
        build_player_week(source)
