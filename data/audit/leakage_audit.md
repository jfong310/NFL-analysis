# Future-Leakage Audit

- Generated at (UTC): 2026-08-04T20:00:29.369773+00:00
- Rows: 5874
- Training rows: 5266
- Prediction rows: 608
- Prediction seasons: 2017-2026
- Feature count: 40

## Guardrail Results

| check | passed | details |
| --- | --- | --- |
| feature_source_is_prior_season | True | violations=0 |
| unique_player_prediction_rows | True | duplicates=0 |
| prediction_targets_are_blank | True | non_null_cells=0 |
| historical_outcomes_are_observed | True | training_rows=5266 |
| feature_values_are_finite | True | infinite_values=0 |
| declared_feature_schema | True | declared_features=40 |

## Feature Missingness

| feature | missing_rate |
| --- | --- |
| prior_year_fantasy_points_over_expected | 0.0449 |
| prior_year_expected_fantasy_points | 0.0449 |
| prior_year_expected_points_per_game | 0.0449 |
| prior_year_snap_share | 0.0049 |
| prior_year_snap_share_std_dev | 0.0049 |
| multi_year_weighted_snap_share | 0.0048 |
| age | 0.0000 |
| years_experience | 0.0000 |
| prior_year_injury_report_weeks | 0.0000 |
| career_games_missed_rate | 0.0000 |
| prior_year_games_missed_rate | 0.0000 |
| prior_year_games_missed | 0.0000 |
| prior_year_games_played | 0.0000 |
| career_seasons | 0.0000 |
| age_x_prior_missed_rate | 0.0000 |
| prior_year_total_fantasy_points | 0.0000 |
| recent_production_trend | 0.0000 |
| prior_year_targets_per_game | 0.0000 |
| prior_year_points_per_game | 0.0000 |
| prior_year_positional_finish | 0.0000 |
| prior_year_replacement_adjusted_points | 0.0000 |
| career_points_per_game | 0.0000 |
| multi_year_weighted_points_per_game | 0.0000 |
| recent_5_points_per_game | 0.0000 |
| recent_usage_trend | 0.0000 |
| recent_5_opportunities_per_game | 0.0000 |
| prior_year_opportunities_per_game | 0.0000 |
| prior_year_passing_attempts_per_game | 0.0000 |
| prior_year_receptions_per_game | 0.0000 |
| prior_year_carries_per_game | 0.0000 |
| prior_year_weekly_std_dev | 0.0000 |
| multi_year_weighted_opportunities_per_game | 0.0000 |
| prior_year_bust_week_rate | 0.0000 |
| prior_year_boom_week_rate | 0.0000 |
| prior_year_coefficient_of_variation | 0.0000 |
| prior_year_usage_std_dev | 0.0000 |
| prior_team_pass_rate | 0.0000 |
| prior_team_rush_rate | 0.0000 |
| prior_team_offensive_plays_per_game | 0.0000 |
| prior_team_points_per_game | 0.0000 |

## Known Scope Limitation

Rows require a prior NFL season, so true rookies and players returning after a full
season away are not represented in this v1 table. Rookie-specific data is deferred.