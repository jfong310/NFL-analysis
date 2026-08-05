"""Walk-forward model evaluation by season and position."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_pinball_loss,
    mean_squared_error,
    r2_score,
)

from fantasy_nfl.models.baseline import (
    MODEL_INPUT_COLUMNS,
    QUANTILES,
    TARGET_SPECS,
    clip_predictions,
    make_point_model,
    make_quantile_model,
)


def regression_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    rank_correlation = pd.Series(actual_values).corr(
        pd.Series(predicted_values), method="spearman"
    )
    return {
        "mae": float(mean_absolute_error(actual_values, predicted_values)),
        "rmse": float(np.sqrt(mean_squared_error(actual_values, predicted_values))),
        "r2": float(r2_score(actual_values, predicted_values)),
        "rank_correlation": float(rank_correlation)
        if pd.notna(rank_correlation)
        else np.nan,
    }


def _evaluation_row(
    *,
    season: int,
    target: str,
    model: str,
    n_train: int,
    actual: pd.Series,
    predicted: np.ndarray,
    position: str | None = None,
) -> dict[str, Any]:
    return {
        "test_season": season,
        "position": position or "ALL",
        "target": target,
        "model": model,
        "n_train": n_train,
        "n_test": len(actual),
        **regression_metrics(actual, predicted),
        "pinball_loss": np.nan,
        "interval_coverage": np.nan,
        "interval_width": np.nan,
    }


def walk_forward_backtest(
    table: pd.DataFrame,
    *,
    min_train_seasons: int = 2,
    n_estimators: int = 150,
    quantile_estimators: int = 100,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    historical = table[table["is_training_row"]].copy()
    seasons = sorted(historical["prediction_season"].unique().tolist())
    if len(seasons) <= min_train_seasons:
        raise ValueError("Not enough historical seasons for walk-forward backtesting")

    season_rows: list[dict[str, Any]] = []
    position_rows: list[dict[str, Any]] = []
    prediction_frames = []

    for test_season in seasons[min_train_seasons:]:
        train = historical[historical["prediction_season"] < test_season]
        test = historical[historical["prediction_season"] == test_season].copy()
        fold_predictions = test[
            ["player_id", "player_name", "position", "prediction_season"]
        ].copy()
        fold_predictions["train_max_season"] = int(
            train["prediction_season"].max()
        )

        for target, spec in TARGET_SPECS.items():
            actual = test[target]
            baseline_prediction = clip_predictions(
                test[spec["baseline_feature"]], target
            )
            model = make_point_model(
                n_estimators=n_estimators, random_state=random_state
            )
            model.fit(train[MODEL_INPUT_COLUMNS], train[target])
            ml_prediction = clip_predictions(
                model.predict(test[MODEL_INPUT_COLUMNS]), target
            )
            fold_predictions[f"actual_{target}"] = actual.to_numpy()
            fold_predictions[f"baseline_{target}"] = baseline_prediction
            fold_predictions[f"ml_{target}"] = ml_prediction

            season_rows.append(
                _evaluation_row(
                    season=test_season,
                    target=target,
                    model="prior_year_baseline",
                    n_train=len(train),
                    actual=actual,
                    predicted=baseline_prediction,
                )
            )
            season_rows.append(
                _evaluation_row(
                    season=test_season,
                    target=target,
                    model="random_forest",
                    n_train=len(train),
                    actual=actual,
                    predicted=ml_prediction,
                )
            )

            for position, group in test.groupby("position"):
                indexes = group.index
                position_rows.append(
                    _evaluation_row(
                        season=test_season,
                        target=target,
                        model="prior_year_baseline",
                        n_train=len(train),
                        actual=group[target],
                        predicted=baseline_prediction[
                            test.index.get_indexer(indexes)
                        ],
                        position=position,
                    )
                )
                position_rows.append(
                    _evaluation_row(
                        season=test_season,
                        target=target,
                        model="random_forest",
                        n_train=len(train),
                        actual=group[target],
                        predicted=ml_prediction[test.index.get_indexer(indexes)],
                        position=position,
                    )
                )

        quantile_predictions = []
        actual_points = test["target_total_fantasy_points"]
        for quantile in QUANTILES:
            model = make_quantile_model(
                quantile,
                n_estimators=quantile_estimators,
                random_state=random_state,
            )
            model.fit(
                train[MODEL_INPUT_COLUMNS],
                train["target_total_fantasy_points"],
            )
            values = np.clip(
                model.predict(test[MODEL_INPUT_COLUMNS]), 0.0, np.inf
            )
            quantile_predictions.append(values)
        quantile_matrix = np.sort(np.column_stack(quantile_predictions), axis=1)
        for index, quantile in enumerate(QUANTILES):
            name = f"quantile_{int(quantile * 100):02d}"
            values = quantile_matrix[:, index]
            fold_predictions[name] = values
            season_rows.append(
                {
                    "test_season": test_season,
                    "position": "ALL",
                    "target": "target_total_fantasy_points",
                    "model": name,
                    "n_train": len(train),
                    "n_test": len(test),
                    "mae": np.nan,
                    "rmse": np.nan,
                    "r2": np.nan,
                    "rank_correlation": np.nan,
                    "pinball_loss": float(
                        mean_pinball_loss(actual_points, values, alpha=quantile)
                    ),
                    "interval_coverage": np.nan,
                    "interval_width": np.nan,
                }
            )
        lower, _, upper = quantile_matrix.T
        season_rows.append(
            {
                "test_season": test_season,
                "position": "ALL",
                "target": "target_total_fantasy_points",
                "model": "quantile_interval_80",
                "n_train": len(train),
                "n_test": len(test),
                "mae": np.nan,
                "rmse": np.nan,
                "r2": np.nan,
                "rank_correlation": np.nan,
                "pinball_loss": np.nan,
                "interval_coverage": float(
                    ((actual_points >= lower) & (actual_points <= upper)).mean()
                ),
                "interval_width": float(np.mean(upper - lower)),
            }
        )
        prediction_frames.append(fold_predictions)

    return (
        pd.DataFrame(season_rows),
        pd.DataFrame(position_rows),
        pd.concat(prediction_frames, ignore_index=True),
    )
