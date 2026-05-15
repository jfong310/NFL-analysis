# Scoring Validation Report
- Audit timestamp (UTC): 2026-05-15T13:52:25.129460+00:00
- Seasons used: [2024]
- Input source: data/audit/samples/player_stats_weekly_sample.parquet
- Postseason excluded from season targets: True
- Input weekly rows: 1
- Scored weekly rows: 1
- Season target rows: 1
- Duplicate player-week rows found: 0
- Duplicate handling strategy: drop_duplicates_keep_first
- Target positions included: ['QB', 'RB', 'WR', 'TE']
- Scoring formats generated: ['standard', 'half_ppr', 'ppr']
- Scoring columns found: ['fumbles_lost', 'interceptions', 'passing_tds', 'passing_yards', 'receiving_tds', 'receiving_yards', 'receptions', 'rushing_tds', 'rushing_yards']
- Scoring columns missing treated as zero: ['offensive_fumble_recovery_tds', 'passing_2pt_conversions', 'receiving_2pt_conversions', 'return_tds', 'rushing_2pt_conversions', 'special_teams_tds']
- Games played logic: non-zero fantasy points OR offensive usage cols (attempts/carries/targets/receptions/snaps) > 0; row-count fallback.
- Replacement assumptions: {'QB': 12, 'RB': 24, 'WR': 36, 'TE': 12}
- Replacement warnings: []
- Primary team logic: most active weeks, latest-week tie-break.

## Basic sanity checks
- No negative games_played: True
- replacement_adjusted_points exists: True
- duplicate player-season rows: 0

## Top 10 players by total PPR points (each season)
### Season 2024

```
player_name position  total_fantasy_points_ppr
 Player One       RB                      14.2
```