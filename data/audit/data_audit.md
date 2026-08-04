# fantasy_nfl_model Data Audit

- Audit timestamp (UTC): 2026-08-04T19:02:06.863873+00:00
- Seasons requested: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

## Dataset Summary

| dataset_name | load_status | row_count | column_count | cache_status |
| --- | --- | --- | --- | --- |
| player_stats_weekly | success | 182252 | 145 | miss |
| rosters | success | 31005 | 36 | miss |
| players | success | 25035 | 39 | miss |
| schedules | success | 2761 | 46 | miss |
| snap_counts | success | 253106 | 16 | miss |
| injuries | success | 55556 | 17 | miss |
| fantasy_player_ids | success | 12470 | 35 | miss |
| ff_opportunity_weekly | success | 58304 | 159 | miss |

## Successful Loads

player_stats_weekly, rosters, players, schedules, snap_counts, injuries, fantasy_player_ids, ff_opportunity_weekly

## Failed Loads

None

## Potential Join Keys

- **player_stats_weekly**: player_id|player_name|team|season|week|game_id|season_type
- **rosters**: gsis_id|pfr_id|sleeper_id|espn_id|yahoo_id|football_name|full_name|team|season|week
- **players**: gsis_id|nfl_id|pfr_id|espn_id|display_name|football_name
- **schedules**: home_team|away_team|season|week|game_id
- **snap_counts**: team|season|week|game_id
- **injuries**: gsis_id|full_name|team|season|week|season_type
- **fantasy_player_ids**: gsis_id|nfl_id|pfr_id|fantasypros_id|sleeper_id|espn_id|yahoo_id|team
- **ff_opportunity_weekly**: player_id|full_name|posteam|season|week|game_id

## Player-Week Join Quality

| dataset | eligible_rows | matched_rows | match_rate | right_duplicate_key_rows |
| --- | --- | --- | --- | --- |
| player_stats_weekly | 56518 | 56518 | 1.0 | 0 |
| players | 56518 | 56518 | 1.0 | 0 |
| rosters | 56518 | 56518 | 1.0 | 2 |
| schedules | 56518 | 56518 | 1.0 | 0 |
| injuries | 56518 | 9653 | 0.17079514490958633 | 8 |
| ff_opportunity_weekly | 56518 | 51041 | 0.903092819986553 | 0 |
| snap_counts | 56518 | 56384 | 0.9976290739233519 | 0 |

## Initial Observations

- Raw pulls are cached as parquet files with JSON provenance records.
- The canonical sample contains regular-season QB/RB/WR/TE player-weeks.

## Chunk 1 Artifacts

- `data/audit/source_inventory.csv`
- `data/audit/sample_player_week.parquet`
- `data/audit/player_id_join_report.csv`
- Per-source samples in `data/audit/samples/`