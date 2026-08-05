import numpy as np
import pandas as pd

from fantasy_nfl.models.baseline import (
    MODEL_INPUT_COLUMNS,
    TARGET_SPECS,
    extract_feature_importance,
    make_quantile_model,
    predict_rows,
    train_final_models,
)
from fantasy_nfl.models.evaluate import regression_metrics, walk_forward_backtest
from fantasy_nfl.transform.features import MODEL_FEATURE_COLUMNS


def model_table():
    rows = []
    rng = np.random.default_rng(42)
    positions = ["QB", "RB", "WR", "TE"]
    for season in range(2017, 2022):
        for index in range(12):
            prior_points = 20.0 + index * 8 + (season - 2017) * 2
            row = {
                "player_id": f"P{index}",
                "player_name": f"Player {index}",
                "position": positions[index % len(positions)],
                "prediction_season": season,
                "prior_year_team": "A",
                "is_training_row": True,
                "is_prediction_row": False,
                "target_total_fantasy_points": prior_points * 0.9 + rng.normal(0, 3),
                "target_points_per_game": prior_points / 12 + rng.normal(0, 0.2),
                "target_games_played": float(8 + index % 9),
            }
            for feature_index, feature in enumerate(MODEL_FEATURE_COLUMNS):
                row[feature] = prior_points / (feature_index + 2)
            row["prior_year_total_fantasy_points"] = prior_points
            row["prior_year_points_per_game"] = prior_points / 12
            row["prior_year_games_played"] = float(9 + index % 8)
            rows.append(row)

    prediction = rows[-1].copy()
    prediction.update(
        {
            "player_id": "P2022",
            "player_name": "Prediction Player",
            "prediction_season": 2022,
            "is_training_row": False,
            "is_prediction_row": True,
            "target_total_fantasy_points": np.nan,
            "target_points_per_game": np.nan,
            "target_games_played": np.nan,
        }
    )
    rows.append(prediction)
    return pd.DataFrame(rows)


def test_regression_metrics_are_exact_for_perfect_prediction():
    actual = pd.Series([1.0, 2.0, 3.0])
    metrics = regression_metrics(actual, actual.to_numpy())
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["r2"] == 1.0
    assert metrics["rank_correlation"] == 1.0


def test_walk_forward_splits_never_train_on_test_or_future():
    season_eval, position_eval, predictions = walk_forward_backtest(
        model_table(),
        min_train_seasons=2,
        n_estimators=10,
        quantile_estimators=10,
    )

    assert set(season_eval.test_season) == {2019, 2020, 2021}
    assert (predictions.train_max_season < predictions.prediction_season).all()
    assert {"prior_year_baseline", "random_forest"}.issubset(set(season_eval.model))
    assert set(position_eval.position) == {"QB", "RB", "WR", "TE"}
    assert (
        predictions["quantile_10"]
        <= predictions["quantile_50"]
    ).all()
    assert (
        predictions["quantile_50"]
        <= predictions["quantile_90"]
    ).all()


def test_final_models_produce_bounded_predictions_and_importance():
    table = model_table()
    bundle = train_final_models(
        table, n_estimators=10, quantile_estimators=10
    )
    prediction_rows = table[table.is_prediction_row]
    projections = predict_rows(bundle, prediction_rows)

    assert len(projections) == 1
    assert projections.projected_total_fantasy_points.iloc[0] >= 0
    assert 0 <= projections.projected_games_played.iloc[0] <= 18
    assert projections.projected_points_q10.iloc[0] <= projections.projected_points_q50.iloc[0]
    assert projections.projected_points_q50.iloc[0] <= projections.projected_points_q90.iloc[0]

    for target, model in bundle["point_models"].items():
        importance = extract_feature_importance(model, target)
        assert not importance.empty
        assert np.isclose(importance.importance.sum(), 1.0)


def test_model_contract_contains_all_inputs_and_targets():
    table = model_table()
    assert set(MODEL_INPUT_COLUMNS).issubset(table.columns)
    assert set(TARGET_SPECS).issubset(table.columns)
    assert make_quantile_model(0.5, n_estimators=5)
