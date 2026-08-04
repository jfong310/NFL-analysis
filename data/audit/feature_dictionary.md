# Feature Dictionary

All features are calculated using information available no later than feature_source_season,
which must equal prediction_season minus one for the current pipeline.

| feature | family | definition |
| --- | --- | --- |
| age | profile | Age on September 1 of the prediction season. |
| years_experience | profile | Prediction season minus rookie season; roster/career fallback. |
| career_seasons | profile | Number of NFL seasons observed through the feature cutoff. |
| prior_year_games_played | availability | Weekly-stat games in the immediately prior season. |
| prior_year_games_missed | availability | Scheduled season limit minus prior games played. |
| prior_year_games_missed_rate | availability | Prior games missed divided by season limit. |
| career_games_missed_rate | availability | Career missed games divided by career scheduled games. |
| prior_year_injury_report_weeks | availability | Prior weeks with an injury-report status. |
| age_x_prior_missed_rate | availability | Age multiplied by prior games-missed rate. |
| prior_year_total_fantasy_points | production | Prior-season PPR fantasy-point total. |
| prior_year_points_per_game | production | Prior-season PPR points per game. |
| prior_year_positional_finish | production | Prior-season PPR positional finish. |
| prior_year_replacement_adjusted_points | production | Prior PPR points above positional replacement. |
| career_points_per_game | production | Career PPR points divided by career games through cutoff. |
| multi_year_weighted_points_per_game | production | Recency-weighted PPG over up to three seasons (0.6/0.3/0.1). |
| recent_5_points_per_game | production | Average PPR points over the last five prior-season games. |
| recent_production_trend | production | Last-five PPG minus full prior-season PPG. |
| prior_year_targets_per_game | usage | Prior targets per player-week. |
| prior_year_carries_per_game | usage | Prior carries per player-week. |
| prior_year_receptions_per_game | usage | Prior receptions per player-week. |
| prior_year_passing_attempts_per_game | usage | Prior passing attempts per player-week. |
| prior_year_opportunities_per_game | usage | Targets plus carries plus passing attempts per week. |
| recent_5_opportunities_per_game | usage | Average opportunities over the last five prior games. |
| recent_usage_trend | usage | Last-five opportunities minus full prior-season opportunities. |
| multi_year_weighted_opportunities_per_game | usage | Recency-weighted opportunities over up to three seasons. |
| prior_year_expected_fantasy_points | usage | Prior nflverse expected fantasy-point total. |
| prior_year_expected_points_per_game | usage | Prior expected fantasy points per player-week. |
| prior_year_fantasy_points_over_expected | efficiency | Prior actual PPR points minus expected points. |
| prior_year_weekly_std_dev | volatility | Population standard deviation of prior weekly PPR points. |
| prior_year_coefficient_of_variation | volatility | Prior weekly PPR standard deviation divided by mean. |
| prior_year_boom_week_rate | volatility | Share of prior weeks scoring at least 20 PPR points. |
| prior_year_bust_week_rate | volatility | Share of prior weeks scoring fewer than 5 PPR points. |
| prior_year_usage_std_dev | volatility | Population standard deviation of weekly opportunities. |
| prior_year_snap_share | usage | Mean offensive snap share in the prior season. |
| prior_year_snap_share_std_dev | volatility | Population standard deviation of offensive snap share. |
| multi_year_weighted_snap_share | usage | Recency-weighted snap share over up to three seasons. |
| prior_team_pass_rate | team_context | Prior team pass attempts divided by pass attempts plus carries. |
| prior_team_rush_rate | team_context | One minus prior team pass rate. |
| prior_team_offensive_plays_per_game | team_context | Prior team pass attempts plus carries per scheduled game. |
| prior_team_points_per_game | team_context | Prior team NFL points per scheduled game. |

## Target Columns

Target columns are outcomes from prediction_season. They are populated only for
historical training rows and are blank for 2026 prediction rows.

- target_games_played
- target_total_fantasy_points
- target_points_per_game
- target_weekly_std_dev
- target_positional_finish
- target_top_12_finish
- target_top_24_finish
- target_top_36_finish
- target_replacement_adjusted_points