"""Train and compare boosted point models without replacing production projections."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd
import sklearn

from fantasy_nfl.analysis.boosting_report import weighted_metric_summary, write_boosting_report
from fantasy_nfl.config.paths import AUDIT_DIR, MODEL_DIR, PROCESSED_DATA_DIR, ensure_data_dirs
from fantasy_nfl.models.baseline import TARGET_SPECS
from fantasy_nfl.models.boosting import (
    STANDALONE_MODELS,
    ENSEMBLE_COMPONENTS,
    candidate_feature_importance,
    predict_candidates,
    train_final_candidates,
    validation_weights,
    walk_forward_boosting_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the parallel boosted point-model benchmark.")
    parser.add_argument(
        "--input-path", type=Path,
        default=PROCESSED_DATA_DIR / "model_training_table.parquet",
    )
    parser.add_argument("--min-train-seasons", type=int, default=2)
    parser.add_argument("--rf-estimators", type=int, default=150)
    parser.add_argument("--boosting-estimators", type=int, default=100)
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

    season_eval, position_eval, backtest, weights = walk_forward_boosting_benchmark(
        table,
        min_train_seasons=args.min_train_seasons,
        rf_estimators=args.rf_estimators,
        boosting_estimators=args.boosting_estimators,
        random_state=args.random_state,
    )
    models = train_final_candidates(
        table,
        rf_estimators=args.rf_estimators,
        boosting_estimators=args.boosting_estimators,
        random_state=args.random_state,
    )
    importance = candidate_feature_importance(models)
    prediction_rows = table.loc[table["is_prediction_row"]].copy()
    final_weights = validation_weights(backtest)
    projections = predict_candidates(models, prediction_rows, final_weights)
    summary = weighted_metric_summary(season_eval)

    season_path = AUDIT_DIR / "boosting_model_eval_by_season.csv"
    position_path = AUDIT_DIR / "boosting_model_eval_by_position.csv"
    summary_path = AUDIT_DIR / "boosting_model_summary.csv"
    importance_path = AUDIT_DIR / "boosting_feature_importance.csv"
    weights_path = AUDIT_DIR / "boosting_ensemble_weights.csv"
    report_path = AUDIT_DIR / "boosting_benchmark_report.md"
    backtest_path = PROCESSED_DATA_DIR / "boosting_backtest_predictions.parquet"
    projections_path = PROCESSED_DATA_DIR / "boosting_2026_projections.parquet"
    projections_csv_path = PROCESSED_DATA_DIR / "boosting_2026_model_comparison.csv"
    model_path = MODEL_DIR / "boosting_candidate_models.pkl"

    season_eval.to_csv(season_path, index=False)
    position_eval.to_csv(position_path, index=False)
    summary.to_csv(summary_path, index=False)
    importance.to_csv(importance_path, index=False)
    weights.to_csv(weights_path, index=False)
    backtest.to_parquet(backtest_path, index=False)
    projections.to_parquet(projections_path, index=False)
    projections.to_csv(projections_csv_path, index=False)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "models": models,
        "final_weights": final_weights.to_dict(),
        "standalone_models": list(STANDALONE_MODELS),
        "ensemble_components": list(ENSEMBLE_COMPONENTS),
        "metadata": {
            "sklearn_version": sklearn.__version__,
            "feature_table": args.input_path.name,
            "rf_estimators": args.rf_estimators,
            "boosting_estimators": args.boosting_estimators,
            "random_state": args.random_state,
            "production_promoted": False,
        },
    }
    joblib.dump(bundle, model_path)
    write_boosting_report(
        season_eval, position_eval, importance, weights, projections, report_path
    )

    print(f"Overall model summary saved to: {summary_path}")
    print(f"Season comparison saved to: {season_path}")
    print(f"Position comparison saved to: {position_path}")
    print(f"Candidate importance saved to: {importance_path}")
    print(f"Ensemble weights saved to: {weights_path}")
    print(f"Benchmark report saved to: {report_path}")
    print(f"Backtest predictions saved to: {backtest_path}")
    print(f"Readable 2026 model comparison saved to: {projections_csv_path}")
    print(f"Parallel 2026 projections saved to: {projections_path}")
    print(f"Candidate model bundle saved to: {model_path}")
    print("Production baseline and draft board were not changed.")


if __name__ == "__main__":
    main()
