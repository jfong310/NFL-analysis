"""Parallel boosted point-model benchmark and leakage-safe ensemble utilities."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline

from fantasy_nfl.models.baseline import (
    MODEL_INPUT_COLUMNS,
    extract_feature_importance,
    make_point_model,
    make_preprocessor,
    make_quantile_model,
)
from fantasy_nfl.models.evaluate import regression_metrics

POINTS_TARGET = "target_total_fantasy_points"
STANDALONE_MODELS = (
    "random_forest",
    "boosting_squared",
    "boosting_huber",
    "boosting_absolute",
    "boosting_q50",
)
ENSEMBLE_COMPONENTS = (
    "random_forest",
    "boosting_squared",
    "boosting_huber",
    "boosting_q50",
)
ENSEMBLE_MODELS = ("ensemble_equal", "ensemble_validation_weighted")
REPLACEMENT_RANKS = {"QB": 13, "RB": 37, "WR": 49, "TE": 13}


def make_boosted_point_model(
    loss: str,
    *,
    n_estimators: int = 100,
    random_state: int = 42,
) -> Pipeline:
    """Build a conservatively regularized gradient-boosted point estimator."""
    allowed = {"squared_error", "huber", "absolute_error"}
    if loss not in allowed:
        raise ValueError(f"Unsupported boosted point loss: {loss}")
    return Pipeline(
        [
            ("preprocess", make_preprocessor()),
            (
                "model",
                GradientBoostingRegressor(
                    loss=loss,
                    n_estimators=n_estimators,
                    learning_rate=0.04,
                    max_depth=3,
                    min_samples_leaf=8,
                    random_state=random_state,
                ),
            ),
        ]
    )


def make_candidate_models(
    *,
    rf_estimators: int = 150,
    boosting_estimators: int = 100,
    random_state: int = 42,
) -> dict[str, Pipeline]:
    """Return all standalone candidates with consistent preprocessing."""
    return {
        "random_forest": make_point_model(
            n_estimators=rf_estimators, random_state=random_state
        ),
        "boosting_squared": make_boosted_point_model(
            "squared_error", n_estimators=boosting_estimators, random_state=random_state
        ),
        "boosting_huber": make_boosted_point_model(
            "huber", n_estimators=boosting_estimators, random_state=random_state
        ),
        "boosting_absolute": make_boosted_point_model(
            "absolute_error", n_estimators=boosting_estimators, random_state=random_state
        ),
        "boosting_q50": make_quantile_model(
            0.5, n_estimators=boosting_estimators, random_state=random_state
        ),
    }


def validation_weights(predictions: pd.DataFrame) -> pd.Series:
    """Calculate transparent inverse-squared-MAE weights from prior OOF predictions."""
    if predictions.empty:
        return pd.Series(1 / len(ENSEMBLE_COMPONENTS), index=ENSEMBLE_COMPONENTS)
    actual = predictions["actual_total_fantasy_points"].to_numpy(float)
    errors = {}
    for model in ENSEMBLE_COMPONENTS:
        predicted = predictions[f"prediction_{model}"].to_numpy(float)
        errors[model] = max(float(np.mean(np.abs(actual - predicted))), 1e-6)
    inverse = pd.Series({model: 1 / error**2 for model, error in errors.items()})
    return inverse / inverse.sum()


def _metric_row(
    frame: pd.DataFrame, model: str, *, season: int, position: str = "ALL"
) -> dict[str, Any]:
    metrics = regression_metrics(
        frame["actual_total_fantasy_points"], frame[f"prediction_{model}"].to_numpy()
    )
    return {
        "test_season": season,
        "position": position,
        "target": POINTS_TARGET,
        "model": model,
        "n_train": int(frame["n_train"].iloc[0]),
        "n_test": len(frame),
        **metrics,
    }


def walk_forward_boosting_benchmark(
    table: pd.DataFrame,
    *,
    min_train_seasons: int = 2,
    rf_estimators: int = 150,
    boosting_estimators: int = 100,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Backtest candidates and ensembles using training seasons strictly before each test."""
    historical = table.loc[table["is_training_row"]].copy()
    seasons = sorted(historical["prediction_season"].unique().tolist())
    if len(seasons) <= min_train_seasons:
        raise ValueError("Not enough historical seasons for walk-forward backtesting")
    frames: list[pd.DataFrame] = []
    for test_season in seasons[min_train_seasons:]:
        train = historical.loc[historical["prediction_season"] < test_season]
        test = historical.loc[historical["prediction_season"] == test_season]
        fold = test[["player_id", "player_name", "position", "prediction_season"]].copy()
        fold["train_max_season"] = int(train["prediction_season"].max())
        fold["n_train"] = len(train)
        fold["actual_total_fantasy_points"] = test[POINTS_TARGET].to_numpy()
        models = make_candidate_models(
            rf_estimators=rf_estimators,
            boosting_estimators=boosting_estimators,
            random_state=random_state,
        )
        for name, model in models.items():
            model.fit(train[MODEL_INPUT_COLUMNS], train[POINTS_TARGET])
            fold[f"prediction_{name}"] = np.clip(
                model.predict(test[MODEL_INPUT_COLUMNS]), 0.0, np.inf
            )
        frames.append(fold)
    predictions = pd.concat(frames, ignore_index=True)
    predictions["prediction_ensemble_equal"] = predictions[
        [f"prediction_{name}" for name in ENSEMBLE_COMPONENTS]
    ].mean(axis=1)

    weight_rows: list[dict[str, Any]] = []
    weighted_values = pd.Series(index=predictions.index, dtype=float)
    for season in sorted(predictions["prediction_season"].unique()):
        history = predictions.loc[predictions["prediction_season"] < season]
        weights = validation_weights(history)
        indexes = predictions.index[predictions["prediction_season"] == season]
        matrix = predictions.loc[
            indexes, [f"prediction_{name}" for name in ENSEMBLE_COMPONENTS]
        ]
        weighted_values.loc[indexes] = matrix.to_numpy() @ weights.loc[list(ENSEMBLE_COMPONENTS)].to_numpy()
        for model, weight in weights.items():
            weight_rows.append(
                {
                    "application_season": int(season),
                    "weight_training_through": (
                        int(history["prediction_season"].max()) if not history.empty else pd.NA
                    ),
                    "model": model,
                    "weight": float(weight),
                    "scope": "walk_forward",
                }
            )
    predictions["prediction_ensemble_validation_weighted"] = weighted_values

    season_rows: list[dict[str, Any]] = []
    position_rows: list[dict[str, Any]] = []
    for season, fold in predictions.groupby("prediction_season"):
        for model in (*STANDALONE_MODELS, *ENSEMBLE_MODELS):
            season_rows.append(_metric_row(fold, model, season=int(season)))
            for position, group in fold.groupby("position"):
                position_rows.append(
                    _metric_row(group, model, season=int(season), position=str(position))
                )
    final_weights = validation_weights(predictions)
    for model, weight in final_weights.items():
        weight_rows.append(
            {
                "application_season": int(table.loc[table["is_prediction_row"], "prediction_season"].max()),
                "weight_training_through": int(predictions["prediction_season"].max()),
                "model": model,
                "weight": float(weight),
                "scope": "final_2026",
            }
        )
    return (
        pd.DataFrame(season_rows),
        pd.DataFrame(position_rows),
        predictions,
        pd.DataFrame(weight_rows),
    )


def train_final_candidates(
    table: pd.DataFrame,
    *,
    rf_estimators: int = 150,
    boosting_estimators: int = 100,
    random_state: int = 42,
) -> dict[str, Pipeline]:
    """Fit every standalone candidate on all historical training rows."""
    train = table.loc[table["is_training_row"]]
    models = make_candidate_models(
        rf_estimators=rf_estimators,
        boosting_estimators=boosting_estimators,
        random_state=random_state,
    )
    for model in models.values():
        model.fit(train[MODEL_INPUT_COLUMNS], train[POINTS_TARGET])
    return models


def candidate_feature_importance(models: dict[str, Pipeline]) -> pd.DataFrame:
    """Return comparable, separately labeled tree importance for every candidate."""
    frames = []
    for name, model in models.items():
        frame = extract_feature_importance(model, POINTS_TARGET)
        frame.insert(0, "model", name)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def predict_candidates(
    models: dict[str, Pipeline],
    rows: pd.DataFrame,
    final_weights: pd.Series,
) -> pd.DataFrame:
    """Generate parallel 2026 projections and ranks without choosing a winner."""
    output = rows[
        ["player_id", "player_name", "position", "prediction_season", "prior_year_team"]
    ].copy()
    for name, model in models.items():
        output[f"projected_points_{name}"] = np.clip(
            model.predict(rows[MODEL_INPUT_COLUMNS]), 0.0, np.inf
        )
    standalone_columns = [f"projected_points_{name}" for name in STANDALONE_MODELS]
    ensemble_columns = [f"projected_points_{name}" for name in ENSEMBLE_COMPONENTS]
    output["projected_points_ensemble_equal"] = output[ensemble_columns].mean(axis=1)
    output["projected_points_ensemble_validation_weighted"] = (
        output[ensemble_columns].to_numpy()
        @ final_weights.loc[list(ENSEMBLE_COMPONENTS)].to_numpy()
    )
    all_models = (*STANDALONE_MODELS, *ENSEMBLE_MODELS)
    for name in all_models:
        points_column = f"projected_points_{name}"
        output[f"positional_rank_{name}"] = output.groupby("position")[points_column].rank(
            ascending=False, method="first"
        )
        replacement = {}
        for position, group in output.groupby("position"):
            ordered = group[points_column].sort_values(ascending=False)
            rank = min(REPLACEMENT_RANKS.get(position, len(ordered)), len(ordered))
            replacement[position] = float(ordered.iloc[rank - 1])
        vorp = output[points_column] - output["position"].map(replacement)
        output[f"overall_rank_{name}"] = vorp.rank(ascending=False, method="first")
    output["projection_spread"] = output[standalone_columns].max(axis=1) - output[
        standalone_columns
    ].min(axis=1)
    rank_columns = [f"overall_rank_{name}" for name in STANDALONE_MODELS]
    output["rank_spread"] = output[rank_columns].max(axis=1) - output[rank_columns].min(axis=1)
    return output.sort_values(
        "overall_rank_ensemble_validation_weighted", kind="stable"
    ).reset_index(drop=True)
