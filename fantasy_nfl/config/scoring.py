"""Fantasy scoring rules and replacement-level defaults."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

SCORING_FORMATS = ("standard", "half_ppr", "ppr")

_BASE_WEIGHTS = {
    "passing_yards": 0.04,
    "passing_tds": 4.0,
    "passing_interceptions": -2.0,
    "rushing_yards": 0.1,
    "rushing_tds": 6.0,
    "receiving_yards": 0.1,
    "receiving_tds": 6.0,
    "special_teams_tds": 6.0,
    "passing_2pt_conversions": 2.0,
    "rushing_2pt_conversions": 2.0,
    "receiving_2pt_conversions": 2.0,
    "sack_fumbles_lost": -2.0,
    "rushing_fumbles_lost": -2.0,
    "receiving_fumbles_lost": -2.0,
}

SCORING_WEIGHTS: Mapping[str, Mapping[str, float]] = MappingProxyType(
    {
        "standard": MappingProxyType({**_BASE_WEIGHTS, "receptions": 0.0}),
        "half_ppr": MappingProxyType({**_BASE_WEIGHTS, "receptions": 0.5}),
        "ppr": MappingProxyType({**_BASE_WEIGHTS, "receptions": 1.0}),
    }
)

REPLACEMENT_RANKS: Mapping[str, int] = MappingProxyType(
    {"QB": 13, "RB": 37, "WR": 49, "TE": 13}
)


def get_scoring_weights(scoring_format: str) -> Mapping[str, float]:
    try:
        return SCORING_WEIGHTS[scoring_format]
    except KeyError as exc:
        supported = ", ".join(SCORING_FORMATS)
        raise ValueError(f"Unknown scoring format {scoring_format!r}; expected one of: {supported}") from exc
