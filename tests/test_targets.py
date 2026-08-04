import pandas as pd
import pytest

from fantasy_nfl.audit.scoring_validation import scoring_validation_metrics
from fantasy_nfl.transform.targets import build_player_season_targets


def scored_rows():
    rows = []
    weekly = {
        ("A", 2024): [10.0, 30.0],
        ("B", 2024): [10.0, 10.0],
        ("C", 2024): [5.0, 5.0],
        ("A", 2025): [15.0],
    }
    for (player, season), scores in weekly.items():
        for week, score in enumerate(scores, start=1):
            rows.append(
                {
                    "player_id": player,
                    "player_name": f"Player {player}",
                    "season": season,
                    "week": week,
                    "position": "QB",
                    "team": "A",
                    "fantasy_points_standard": score,
                    "fantasy_points_half_ppr": score,
                    "fantasy_points_ppr": score,
                }
            )
    return pd.DataFrame(rows)


def test_season_targets_aggregation_ranks_and_replacement_value():
    targets = build_player_season_targets(scored_rows(), replacement_ranks={"QB": 2})
    a_2024 = targets[(targets.player_id == "A") & (targets.season == 2024)].iloc[0]
    b_2024 = targets[(targets.player_id == "B") & (targets.season == 2024)].iloc[0]
    c_2024 = targets[(targets.player_id == "C") & (targets.season == 2024)].iloc[0]

    assert len(targets) == 4
    assert a_2024.games_played == 2
    assert a_2024.total_fantasy_points == 40.0
    assert a_2024.points_per_game == 20.0
    assert a_2024.weekly_std_dev == 10.0
    assert a_2024.positional_finish == 1
    assert b_2024.positional_finish == 2
    assert c_2024.positional_finish == 3
    assert a_2024.replacement_points_per_game == 10.0
    assert a_2024.replacement_adjusted_points == 20.0
    assert b_2024.replacement_adjusted_points == 0.0
    assert a_2024.replacement_total_fantasy_points == 20.0
    assert c_2024.replacement_adjusted_points == -10.0


def test_seasons_are_kept_separate_and_outputs_are_unique():
    targets = build_player_season_targets(scored_rows(), replacement_ranks={"QB": 2})
    assert set(targets.season) == {2024, 2025}
    assert not targets.duplicated(["player_id", "season"]).any()
    assert targets.loc[targets.season == 2025, "replacement_rank"].iloc[0] == 1


def test_duplicate_week_is_rejected():
    source = scored_rows()
    source = pd.concat([source, source.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate player-week"):
        build_player_season_targets(source, replacement_ranks={"QB": 2})


def test_reference_validation_metrics():
    scored = pd.DataFrame(
        {
            "fantasy_points_standard": [10.0, 12.0],
            "nflverse_fantasy_points_standard": [10.0, 12.0],
            "fantasy_points_ppr": [15.0, 20.0],
            "nflverse_fantasy_points_ppr": [15.0, 20.0],
        }
    )
    metrics = scoring_validation_metrics(scored)
    assert (metrics["exact_match_rate"] == 1.0).all()
    assert (metrics["rows_over_tolerance"] == 0).all()
