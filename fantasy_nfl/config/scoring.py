"""Scoring and target-construction configuration."""

from __future__ import annotations

SCORING_FORMATS = {
    "standard": {
        "passing_yards": 0.04,
        "passing_tds": 4.0,
        "interceptions": -2.0,
        "passing_2pt_conversions": 2.0,
        "rushing_yards": 0.1,
        "rushing_tds": 6.0,
        "rushing_2pt_conversions": 2.0,
        "receptions": 0.0,
        "receiving_yards": 0.1,
        "receiving_tds": 6.0,
        "receiving_2pt_conversions": 2.0,
        "fumbles_lost": -2.0,
        "special_teams_tds": 6.0,
        "return_tds": 6.0,
        "offensive_fumble_recovery_tds": 6.0,
    },
    "half_ppr": {
        "passing_yards": 0.04,
        "passing_tds": 4.0,
        "interceptions": -2.0,
        "passing_2pt_conversions": 2.0,
        "rushing_yards": 0.1,
        "rushing_tds": 6.0,
        "rushing_2pt_conversions": 2.0,
        "receptions": 0.5,
        "receiving_yards": 0.1,
        "receiving_tds": 6.0,
        "receiving_2pt_conversions": 2.0,
        "fumbles_lost": -2.0,
        "special_teams_tds": 6.0,
        "return_tds": 6.0,
        "offensive_fumble_recovery_tds": 6.0,
    },
    "ppr": {
        "passing_yards": 0.04,
        "passing_tds": 4.0,
        "interceptions": -2.0,
        "passing_2pt_conversions": 2.0,
        "rushing_yards": 0.1,
        "rushing_tds": 6.0,
        "rushing_2pt_conversions": 2.0,
        "receptions": 1.0,
        "receiving_yards": 0.1,
        "receiving_tds": 6.0,
        "receiving_2pt_conversions": 2.0,
        "fumbles_lost": -2.0,
        "special_teams_tds": 6.0,
        "return_tds": 6.0,
        "offensive_fumble_recovery_tds": 6.0,
    },
}

DEFAULT_SCORING_FORMAT = "ppr"
REPLACEMENT_BASELINES = {"QB": 12, "RB": 24, "WR": 36, "TE": 12}
TARGET_POSITIONS = ["QB", "RB", "WR", "TE"]


def get_scoring_config(format_name: str) -> dict[str, float]:
    if format_name not in SCORING_FORMATS:
        raise ValueError(f"Unknown scoring format '{format_name}'. Available: {sorted(SCORING_FORMATS)}")
    return SCORING_FORMATS[format_name]
