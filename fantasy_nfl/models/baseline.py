"""Deterministic tabular baseline models for fantasy outcomes."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from fantasy_nfl.transform.features import MODEL_FEATURE_COLUMNS

MODEL_INPUT_COLUMNS = ["position", *MODEL_FEATURE_COLUMNS]

TARGET_SPECS = {
    "target_total_fantasy_points": {
        "baseline_feature": "prior_year_total_fantasy_points",
        "prediction_name": "projected_total_fantasy_points",
        "lower": 0.0,
        "upper": None,
    },
    "target_points_per_game": {
        "baseline_feature": "prior_year_points_per_game",
        "prediction_name": "projected_points_per_game",
        "lower": 0.0,
        "upper": None,
    },
    "target_games_played": {
        "baseline_feature": "prior_year_games_played",
        "prediction_name": "projected_games_played",
        "lower": 0.0,
        "upper": 18.0,
    },
}

QUANTILES = (0.1, 0.5, 0.9)


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "numeric",
                SimpleImputer(strategy="median", add_indicator=True),
                MODEL_FEATURE_COLUMNS,
            ),
            (
                "position",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ["position"],
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def make_point_model(
    *,
    n_estimators: int = 150,
    random_state: int = 42,
) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", make_preprocessor()),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=n_estimators,
                    max_depth=14,
                    min_samples_leaf=4,
                    max_features=0.7,
                    n_jobs=-1,
                    random_state=random_state,
                ),
            ),
        ]
    )


def make_quantile_model(
    quantile: float,
    *,
    n_estimators: int = 100,
    random_state: int = 42,
) -> Pipeline:
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile must be strictly between zero and one")
    return Pipeline(
        [
            ("preprocess", make_preprocessor()),
            (
                "model",
                GradientBoostingRegressor(
                    loss="quantile",
                    alpha=quantile,
                    n_estimators=n_estimators,
                    learning_rate=0.04,
                    max_depth=3,
                    min_samples_leaf=8,
                    random_state=random_state,
                ),
            ),
        ]
    )


def clip_predictions(values: Any, target: str) -> np.ndarray:
    spec = TARGET_SPECS[target]
    return np.clip(
        np.asarray(values, dtype=float),
        spec["lower"],
        spec["upper"] if spec["upper"] is not None else np.inf,
    )


def extract_feature_importance(model: Pipeline, target: str) -> pd.DataFrame:
    names = model.named_steps["preprocess"].get_feature_names_out()
    importance = model.named_steps["model"].feature_importances_
    return (
        pd.DataFrame(
            {
                "target": target,
                "feature": names,
                "importance": importance,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def train_final_models(
    table: pd.DataFrame,
    *,
    n_estimators: int = 150,
    quantile_estimators: int = 100,
    random_state: int = 42,
) -> dict[str, Any]:
    train = table[table["is_training_row"]].copy()
    point_models = {}
    for target in TARGET_SPECS:
        model = make_point_model(
            n_estimators=n_estimators, random_state=random_state
        )
        model.fit(train[MODEL_INPUT_COLUMNS], train[target])
        point_models[target] = model

    quantile_models = {}
    for quantile in QUANTILES:
        model = make_quantile_model(
            quantile,
            n_estimators=quantile_estimators,
            random_state=random_state,
        )
        model.fit(
            train[MODEL_INPUT_COLUMNS], train["target_total_fantasy_points"]
        )
        quantile_models[quantile] = model

    return {
        "point_models": point_models,
        "quantile_models": quantile_models,
        "model_input_columns": MODEL_INPUT_COLUMNS,
        "training_seasons": sorted(train["prediction_season"].unique().tolist()),
        "random_state": random_state,
    }


def predict_rows(bundle: dict[str, Any], rows: pd.DataFrame) -> pd.DataFrame:
    output = rows[
        [
            "player_id",
            "player_name",
            "position",
            "prediction_season",
            "prior_year_team",
        ]
    ].copy()
    inputs = rows[MODEL_INPUT_COLUMNS]
    for target, model in bundle["point_models"].items():
        output[TARGET_SPECS[target]["prediction_name"]] = clip_predictions(
            model.predict(inputs), target
        )

    quantile_values = np.column_stack(
        [
            bundle["quantile_models"][quantile].predict(inputs)
            for quantile in QUANTILES
        ]
    )
    quantile_values = np.maximum.accumulate(
        np.sort(np.clip(quantile_values, 0.0, np.inf), axis=1), axis=1
    )
    for index, quantile in enumerate(QUANTILES):
        output[f"projected_points_q{int(quantile * 100):02d}"] = quantile_values[
            :, index
        ]
    output["projected_positional_finish"] = (
        output.groupby("position")["projected_total_fantasy_points"]
        .rank(method="first", ascending=False)
        .astype("int64")
    )
    return output.sort_values(
        ["position", "projected_positional_finish"]
    ).reset_index(drop=True)
