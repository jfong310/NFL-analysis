from __future__ import annotations

import numpy as np
import pandas as pd

from fantasy_nfl.models.baseline import MODEL_INPUT_COLUMNS
from fantasy_nfl.models.boosting import (
    ENSEMBLE_MODELS,
    STANDALONE_MODELS,
    candidate_feature_importance,
    make_boosted_point_model,
    predict_candidates,
    train_final_candidates,
    validation_weights,
    walk_forward_boosting_benchmark,
)
from fantasy_nfl.transform.features import MODEL_FEATURE_COLUMNS


def benchmark_table() -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(7)
    positions = ["QB", "RB", "WR", "TE"]
    for season in range(2017, 2022):
        for index in range(12):
            prior = 35.0 + index * 7 + (season - 2017) * 3
            row = {
                "player_id": f"P{index}", "player_name": f"Player {index}",
                "position": positions[index % 4], "prediction_season": season,
                "prior_year_team": "T", "is_training_row": True, "is_prediction_row": False,
                "target_total_fantasy_points": prior * 0.92 + rng.normal(0, 2),
                "target_points_per_game": prior / 12, "target_games_played": 14.0,
            }
            for feature_index, feature in enumerate(MODEL_FEATURE_COLUMNS):
                row[feature] = prior / (feature_index + 2)
            rows.append(row)
    prediction = rows[-1].copy()
    prediction.update({
        "player_id": "P2022", "player_name": "Prediction", "prediction_season": 2022,
        "is_training_row": False, "is_prediction_row": True,
        "target_total_fantasy_points": np.nan,
    })
    rows.append(prediction)
    return pd.DataFrame(rows)


def test_boosted_point_factory_validates_loss():
    assert make_boosted_point_model("squared_error", n_estimators=5)
    try:
        make_boosted_point_model("not-a-loss", n_estimators=5)
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("Unsupported loss should fail")


def test_parallel_walk_forward_and_weights_are_leakage_safe():
    season_eval, position_eval, predictions, weights = walk_forward_boosting_benchmark(
        benchmark_table(), min_train_seasons=2, rf_estimators=5, boosting_estimators=5
    )
    assert set(season_eval.model) == set((*STANDALONE_MODELS, *ENSEMBLE_MODELS))
    assert (predictions.train_max_season < predictions.prediction_season).all()
    assert set(position_eval.position) == {"QB", "RB", "WR", "TE"}
    prediction_columns = {f"prediction_{name}" for name in (*STANDALONE_MODELS, *ENSEMBLE_MODELS)}
    assert prediction_columns.issubset(predictions.columns)
    walk_weights = weights.loc[weights.scope == "walk_forward"]
    assert np.allclose(walk_weights.groupby("application_season").weight.sum(), 1.0)
    trained = walk_weights.dropna(subset=["weight_training_through"])
    assert (trained.weight_training_through < trained.application_season).all()


def test_final_candidates_preserve_parallel_projections_and_ranks():
    table = benchmark_table()
    _, _, backtest, _ = walk_forward_boosting_benchmark(
        table, min_train_seasons=2, rf_estimators=5, boosting_estimators=5
    )
    models = train_final_candidates(table, rf_estimators=5, boosting_estimators=5)
    weights = validation_weights(backtest)
    projections = predict_candidates(models, table.loc[table.is_prediction_row], weights)
    importance = candidate_feature_importance(models)
    assert set(MODEL_INPUT_COLUMNS).issubset(table.columns)
    assert np.isclose(weights.sum(), 1.0)
    assert len(projections) == 1
    for name in (*STANDALONE_MODELS, *ENSEMBLE_MODELS):
        assert f"projected_points_{name}" in projections
        assert f"positional_rank_{name}" in projections
        assert f"overall_rank_{name}" in projections
    assert set(importance.model) == set(STANDALONE_MODELS)
    assert importance.groupby("model").importance.sum().round(6).eq(1.0).all()
