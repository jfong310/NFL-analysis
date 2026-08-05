# Baseline Model Backtest Report

- Generated at (UTC): 2026-08-04T21:51:49.737544+00:00
- Walk-forward test seasons: 2019-2025
- Backtest prediction rows: 4156
- Models: prior-year baseline, random forest point estimates, gradient-boosted quantiles

## Average Walk-Forward Metrics

| target | model | mean_mae | mean_rmse | mean_r2 | mean_rank_correlation |
| --- | --- | --- | --- | --- | --- |
| target_games_played | prior_year_baseline | 4.3046 | 5.7134 | 0.1890 | 0.5769 |
| target_games_played | random_forest | 4.0967 | 4.9351 | 0.3940 | 0.6297 |
| target_points_per_game | prior_year_baseline | 3.0281 | 4.2573 | 0.4708 | 0.6697 |
| target_points_per_game | random_forest | 2.6377 | 3.5830 | 0.6255 | 0.7140 |
| target_total_fantasy_points | prior_year_baseline | 40.6170 | 62.2003 | 0.4944 | 0.7065 |
| target_total_fantasy_points | random_forest | 38.2176 | 56.1352 | 0.5879 | 0.7127 |

## Quantile Calibration

- Mean 80% interval coverage: 0.8885
- Mean 80% interval width: 129.42 points

## Leading Features

| target | feature | importance |
| --- | --- | --- |
| target_games_played | prior_year_replacement_adjusted_points | 0.2236 |
| target_games_played | age_x_prior_missed_rate | 0.1467 |
| target_games_played | prior_year_total_fantasy_points | 0.1083 |
| target_games_played | age | 0.0390 |
| target_games_played | prior_team_points_per_game | 0.0270 |
| target_games_played | career_games_missed_rate | 0.0247 |
| target_games_played | prior_year_fantasy_points_over_expected | 0.0227 |
| target_games_played | prior_team_offensive_plays_per_game | 0.0208 |
| target_games_played | prior_year_positional_finish | 0.0192 |
| target_games_played | career_points_per_game | 0.0186 |
| target_points_per_game | prior_year_total_fantasy_points | 0.2899 |
| target_points_per_game | prior_year_points_per_game | 0.2159 |
| target_points_per_game | multi_year_weighted_points_per_game | 0.1349 |
| target_points_per_game | prior_year_expected_fantasy_points | 0.0556 |
| target_points_per_game | age | 0.0299 |
| target_points_per_game | career_points_per_game | 0.0179 |
| target_points_per_game | prior_year_replacement_adjusted_points | 0.0165 |
| target_points_per_game | prior_year_expected_points_per_game | 0.0131 |
| target_points_per_game | prior_year_snap_share_std_dev | 0.0127 |
| target_points_per_game | prior_team_points_per_game | 0.0121 |
| target_total_fantasy_points | prior_year_total_fantasy_points | 0.4171 |
| target_total_fantasy_points | prior_year_expected_fantasy_points | 0.1289 |
| target_total_fantasy_points | multi_year_weighted_points_per_game | 0.0776 |
| target_total_fantasy_points | prior_year_points_per_game | 0.0470 |
| target_total_fantasy_points | age | 0.0330 |
| target_total_fantasy_points | prior_year_replacement_adjusted_points | 0.0236 |
| target_total_fantasy_points | career_points_per_game | 0.0181 |
| target_total_fantasy_points | recent_5_points_per_game | 0.0131 |
| target_total_fantasy_points | prior_team_points_per_game | 0.0130 |
| target_total_fantasy_points | recent_usage_trend | 0.0124 |

## Evaluation Design

Each test season is predicted using only earlier prediction seasons.
The first two seasons seed training; walk-forward evaluation begins with 2019.
Simple baselines reuse the immediately prior season's outcome.

## Interpretation

This is a baseline modeling milestone, not a claim of production-ready accuracy.
ADP is intentionally excluded until Chunk 5 so model skill and market value remain separable.