"""Run Chunk 4 walk-forward backtesting and train final baseline models."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd
import sklearn

from fantasy_nfl.analysis.backtest_report import write_backtest_report
from fantasy_nfl.config.paths import AUDIT_DIR, MODEL_DIR, PROCESSED_DATA_DIR, ensure_data_dirs
from fantasy_nfl.models.baseline import (
    TARGET_SPECS,
    extract_feature_importance,
    predict_rows,
    train_final_models,
)
from fantasy_nfl.models.evaluate import walk_forward_backtest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and backtest baseline fantasy models.")
    parser.add_argument(
        "--input-path",
        type=Path,
        default=PROCESSED_DATA_DIR / "model_training_table.parquet",
    )
    parser.add_argument("--min-train-seasons", type=int, default=2)
    parser.add_argument("--n-estimators", type=int, default=150)
    parser.add_argument("--quantile-estimators", type=int, default=100)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_data_dirs()
    if not args.input_path.exists():
        raise FileNotFoundError(
            f"Feature table not found: {args.input_path}. Run scripts/run_feature_pipeline.py first."
        )
    table = pd.read_parquet(args.input_path)
    required = {"is_training_row", "is_prediction_row", *TARGET_SPECS}
    missing = sorted(required - set(table.columns))
    if missing:
        raise ValueError(f"Feature table missing required model columns: {missing}")

    season_eval, position_eval, backtest_predictions = walk_forward_backtest(
        table,
        min_train_seasons=args.min_train_seasons,
        n_estimators=args.n_estimators,
        quantile_estimators=args.quantile_estimators,
        random_state=args.random_state,
    )
    bundle = train_final_models(
        table,
        n_estimators=args.n_estimators,
        quantile_estimators=args.quantile_estimators,
        random_state=args.random_state,
    )
    importance = pd.concat(
        [
            extract_feature_importance(model, target)
            for target, model in bundle["point_models"].items()
        ],
        ignore_index=True,
    )
    prediction_rows = table[table["is_prediction_row"]].copy()
    projections = predict_rows(bundle, prediction_rows)

    season_path = AUDIT_DIR / "model_eval_by_season.csv"
    position_path = AUDIT_DIR / "model_eval_by_position.csv"
    importance_path = AUDIT_DIR / "feature_importance.csv"
    report_path = AUDIT_DIR / "backtest_report.md"
    backtest_path = PROCESSED_DATA_DIR / "backtest_predictions.parquet"
    projections_path = PROCESSED_DATA_DIR / "baseline_2026_projections.parquet"
    model_path = MODEL_DIR / "baseline_model.pkl"

    season_eval.to_csv(season_path, index=False)
    position_eval.to_csv(position_path, index=False)
    importance.to_csv(importance_path, index=False)
    backtest_predictions.to_parquet(backtest_path, index=False)
    projections.to_parquet(projections_path, index=False)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle["metadata"] = {
        "sklearn_version": sklearn.__version__,
        "feature_table": args.input_path.name,
        "n_estimators": args.n_estimators,
        "quantile_estimators": args.quantile_estimators,
        "targets": list(TARGET_SPECS),
    }
    joblib.dump(bundle, model_path)
    write_backtest_report(
        season_eval,
        position_eval,
        backtest_predictions,
        importance,
        report_path,
    )

    print(f"model_eval_by_season.csv saved to: {season_path}")
    print(f"model_eval_by_position.csv saved to: {position_path}")
    print(f"feature_importance.csv saved to: {importance_path}")
    print(f"backtest_report.md saved to: {report_path}")
    print(f"baseline_model.pkl saved to: {model_path}")
    print(f"baseline_2026_projections.parquet saved to: {projections_path}")


if __name__ == "__main__":
    main()
