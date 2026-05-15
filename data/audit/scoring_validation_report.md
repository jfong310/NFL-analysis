# Scoring Validation Report
- Audit timestamp (UTC): 2026-05-15T13:39:45.745660+00:00
- Input source: data/audit/samples/player_stats_weekly_sample.parquet
- Seasons used: [2024]
- Postseason excluded from season targets: True
- Input weekly rows: 1
- Scored weekly rows: 1
- Season target rows: 1
- Duplicate player-week count: 0
- Duplicate handling strategy: keep_first using key ['player_id', 'season', 'week', 'season_type']
- Target positions included: ['QB', 'RB', 'WR', 'TE']
- Non-target positions are excluded from season target output.
- Scoring formats generated: ['standard', 'half_ppr', 'ppr']
- Scoring columns found: ['fumbles_lost', 'interceptions', 'passing_tds', 'passing_yards', 'receiving_tds', 'receiving_yards', 'receptions', 'rushing_tds', 'rushing_yards']
- Scoring columns missing (treated as zero): ['offensive_fumble_recovery_tds', 'passing_2pt_conversions', 'receiving_2pt_conversions', 'return_tds', 'rushing_2pt_conversions', 'special_teams_tds']
- Games played logic: fantasy_points != 0 OR usage columns > 0 OR snap columns > 0; fallback row count via weeks_active.
- Replacement-level assumptions: {'QB': 12, 'RB': 24, 'WR': 36, 'TE': 12}
- Primary team logic: most active weeks, latest-week tie-break.
## Sanity Checks
- No negative games_played: True
- points_per_game consistency: True
- positional finish positive integers: True
- replacement_adjusted_points columns present: True
- duplicate player-season rows: 0
## Replacement baseline warnings
- 2024 RB: only 1 players for baseline 24; using lowest available
- 2024 RB: only 1 players for baseline 24; using lowest available
- 2024 RB: only 1 players for baseline 24; using lowest available
## Leaderboards
### Top 10 PPR Total - 2024
- A (RB): 12.50
### Top 10 by Position - 2024
#### QB
#### RB
- A: 12.50
#### WR
#### TE
## Limitations
- Chunk 2 output only; ADP ingestion and ML modeling are intentionally not included yet.
