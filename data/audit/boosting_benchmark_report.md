# Boosted Point-Model Benchmark

- Generated at (UTC): 2026-08-05T05:40:06.579895+00:00
- Walk-forward test seasons: 2019-2025
- Parallel 2026 projection rows: 608
- Production status: unchanged; these are comparison candidates.

## Overall Walk-Forward Comparison

| model | mae | rmse | r2 | rank_correlation |
| --- | --- | --- | --- | --- |
| boosting_absolute | 35.5415 | 56.5627 | 0.5817 | 0.7211 |
| boosting_q50 | 35.5415 | 56.5627 | 0.5817 | 0.7211 |
| ensemble_validation_weighted | 36.9306 | 55.4528 | 0.5978 | 0.7213 |
| ensemble_equal | 37.0037 | 55.4481 | 0.5978 | 0.7211 |
| boosting_huber | 37.4787 | 55.8151 | 0.5924 | 0.7178 |
| random_forest | 38.1803 | 56.0979 | 0.5882 | 0.7126 |
| boosting_squared | 38.5837 | 56.0022 | 0.5896 | 0.7143 |

## Promotion Gate

- Eligible: no
- The ensemble does not clearly beat the best standalone model (boosting_absolute); retain parallel comparison outputs and do not promote it.

## Final 2026 Validation Weights

| model | weight |
| --- | --- |
| random_forest | 0.2398 |
| boosting_squared | 0.2348 |
| boosting_huber | 0.2488 |
| boosting_q50 | 0.2767 |

Weights are inverse-squared-MAE weights learned from 2019-2025 out-of-fold predictions.
During the backtest, each season's weighted ensemble uses only earlier out-of-fold seasons.

## Position Comparison

| position | model | mae | rmse | rank_correlation |
| --- | --- | --- | --- | --- |
| QB | boosting_absolute | 54.7236 | 83.5888 | 0.7050 |
| QB | boosting_q50 | 54.7236 | 83.5888 | 0.7050 |
| QB | boosting_huber | 56.3805 | 82.2330 | 0.7072 |
| QB | ensemble_validation_weighted | 56.4577 | 81.9138 | 0.7088 |
| QB | ensemble_equal | 56.5454 | 81.9064 | 0.7095 |
| QB | random_forest | 58.2516 | 82.5443 | 0.7092 |
| QB | boosting_squared | 59.4713 | 83.5865 | 0.7029 |
| RB | boosting_absolute | 37.6786 | 59.5541 | 0.7100 |
| RB | boosting_q50 | 37.6786 | 59.5541 | 0.7100 |
| RB | ensemble_validation_weighted | 39.2758 | 58.2255 | 0.7103 |
| RB | ensemble_equal | 39.3638 | 58.2190 | 0.7100 |
| RB | boosting_huber | 39.7823 | 58.5240 | 0.7048 |
| RB | random_forest | 40.7908 | 58.7133 | 0.6990 |
| RB | boosting_squared | 40.8410 | 58.4423 | 0.7055 |
| TE | boosting_absolute | 25.2231 | 39.8523 | 0.7139 |
| TE | boosting_q50 | 25.2231 | 39.8523 | 0.7139 |
| TE | ensemble_validation_weighted | 26.0197 | 38.6419 | 0.7163 |
| TE | ensemble_equal | 26.0688 | 38.6211 | 0.7162 |
| TE | random_forest | 26.5590 | 38.8405 | 0.7060 |
| TE | boosting_huber | 26.7405 | 38.9654 | 0.7106 |
| TE | boosting_squared | 27.3154 | 38.7998 | 0.7092 |
| WR | boosting_absolute | 33.3551 | 50.6173 | 0.7430 |
| WR | boosting_q50 | 33.3551 | 50.6173 | 0.7430 |
| WR | ensemble_validation_weighted | 34.8150 | 49.9680 | 0.7444 |
| WR | ensemble_equal | 34.8865 | 49.9743 | 0.7441 |
| WR | boosting_huber | 35.5050 | 50.4540 | 0.7412 |
| WR | random_forest | 36.0961 | 50.9392 | 0.7352 |
| WR | boosting_squared | 36.2658 | 50.3817 | 0.7395 |

## Leading Features by Candidate

| model | feature | importance |
| --- | --- | --- |
| boosting_absolute | prior_year_total_fantasy_points | 0.6165 |
| boosting_absolute | age_x_prior_missed_rate | 0.1311 |
| boosting_absolute | prior_year_expected_fantasy_points | 0.0648 |
| boosting_absolute | multi_year_weighted_points_per_game | 0.0471 |
| boosting_absolute | age | 0.0436 |
| boosting_absolute | prior_year_replacement_adjusted_points | 0.0277 |
| boosting_absolute | prior_team_points_per_game | 0.0159 |
| boosting_absolute | career_games_missed_rate | 0.0086 |
| boosting_huber | prior_year_total_fantasy_points | 0.7310 |
| boosting_huber | recent_5_points_per_game | 0.0434 |
| boosting_huber | multi_year_weighted_points_per_game | 0.0427 |
| boosting_huber | age | 0.0423 |
| boosting_huber | prior_year_replacement_adjusted_points | 0.0414 |
| boosting_huber | career_points_per_game | 0.0145 |
| boosting_huber | career_games_missed_rate | 0.0141 |
| boosting_huber | prior_year_expected_fantasy_points | 0.0129 |
| boosting_q50 | prior_year_total_fantasy_points | 0.6165 |
| boosting_q50 | age_x_prior_missed_rate | 0.1311 |
| boosting_q50 | prior_year_expected_fantasy_points | 0.0648 |
| boosting_q50 | multi_year_weighted_points_per_game | 0.0471 |
| boosting_q50 | age | 0.0436 |
| boosting_q50 | prior_year_replacement_adjusted_points | 0.0277 |
| boosting_q50 | prior_team_points_per_game | 0.0159 |
| boosting_q50 | career_games_missed_rate | 0.0086 |
| boosting_squared | prior_year_total_fantasy_points | 0.6678 |
| boosting_squared | multi_year_weighted_points_per_game | 0.0835 |
| boosting_squared | recent_5_points_per_game | 0.0566 |
| boosting_squared | age | 0.0412 |
| boosting_squared | prior_year_points_per_game | 0.0312 |
| boosting_squared | prior_year_expected_fantasy_points | 0.0240 |
| boosting_squared | career_points_per_game | 0.0192 |
| boosting_squared | career_games_missed_rate | 0.0124 |
| random_forest | prior_year_total_fantasy_points | 0.4171 |
| random_forest | prior_year_expected_fantasy_points | 0.1289 |
| random_forest | multi_year_weighted_points_per_game | 0.0776 |
| random_forest | prior_year_points_per_game | 0.0470 |
| random_forest | age | 0.0330 |
| random_forest | prior_year_replacement_adjusted_points | 0.0236 |
| random_forest | career_points_per_game | 0.0181 |
| random_forest | recent_5_points_per_game | 0.0131 |

## Interpretation

Squared-error boosting emphasizes large misses. Huber reduces the influence of extreme misses.
Absolute-error and Q50 boosting target the conditional median and are naturally aligned with MAE.
Model importance is reported separately; it is not averaged across incompatible importance scales.
Absolute-error and Q50 are identical under the current hyperparameters, so only Q50 participates in ensembles.
The existing draft board is intentionally not overwritten by this benchmark.