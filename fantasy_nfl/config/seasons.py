"""Season range defaults for data pulls and audits."""

DEFAULT_START_SEASON = 2016
DEFAULT_END_SEASON = 2025
DEFAULT_SEASONS = list(range(DEFAULT_START_SEASON, DEFAULT_END_SEASON + 1))


def get_season_range(start_season: int | None = None, end_season: int | None = None) -> list[int]:
    start = DEFAULT_START_SEASON if start_season is None else start_season
    end = DEFAULT_END_SEASON if end_season is None else end_season
    if end < start:
        raise ValueError(f"end-season ({end}) must be >= start-season ({start})")
    return list(range(start, end + 1))
