# Fantasy Scoring Validation Report

- Generated at (UTC): 2026-08-04T19:14:31.958440+00:00
- Scored player-week rows: 56518
- Player-season target rows: 5874
- Seasons: 2016-2025
- Duplicate player-week rows: 0
- Duplicate player-season rows: 0

## Reference Reconciliation

| scoring_format | rows_compared | exact_match_rate | mean_absolute_error | max_absolute_error | rows_over_tolerance |
| --- | --- | --- | --- | --- | --- |
| standard | 56518 | 1.0 | 6.402964471348825e-17 | 7.105427357601002e-15 | 0 |
| ppr | 56518 | 1.0 | 6.548818994825272e-17 | 7.105427357601002e-15 | 0 |

Standard and PPR calculations are independently reconstructed from component statistics.
Half-PPR is calculated from the same rules with 0.5 points per reception; nflverse has no half-PPR reference column.

## Replacement-Level Assumption

The replacement player is selected at the configured total-points positional rank in each season.
Replacement-adjusted points equal player season points minus that replacement player's season points.

Default ranks: QB13, RB37, WR49, TE13.