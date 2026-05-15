from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fantasy_nfl.config.scoring import DEFAULT_SCORING_FORMAT, SCORING_FORMATS, get_scoring_config

ALIASES = {"player_display_name": "player_name", "recent_team": "team"}


@dataclass
class ScoringMetadata:
    scoring_columns_found: list[str]
    scoring_columns_missing: list[str]
    scoring_formats_generated: list[str]


def normalize_player_week_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for src, dst in ALIASES.items():
        if src in out.columns and dst not in out.columns:
            out[dst] = out[src]
    return out


def calculate_fantasy_points(df: pd.DataFrame, scoring_format: str = "ppr") -> tuple[pd.Series, dict[str, list[str]]]:
    config = get_scoring_config(scoring_format)
    total = pd.Series(0.0, index=df.index)
    found, missing = [], []
    for col, weight in config.items():
        if col in df.columns:
            total = total + pd.to_numeric(df[col], errors="coerce").fillna(0.0) * weight
            found.append(col)
        else:
            missing.append(col)
    return total, {"found": found, "missing": missing}


def score_player_weeks(df: pd.DataFrame, scoring_formats: list[str] | None = None) -> tuple[pd.DataFrame, ScoringMetadata]:
    out = normalize_player_week_columns(df)
    formats = scoring_formats or list(SCORING_FORMATS.keys())
    all_found, all_missing = set(), set()
    for fmt in formats:
        points, meta = calculate_fantasy_points(out, fmt)
        out[f"fantasy_points_{fmt}"] = points
        all_found.update(meta["found"])
        all_missing.update(meta["missing"])
    out["fantasy_points"] = out[f"fantasy_points_{DEFAULT_SCORING_FORMAT}"]
    return out, ScoringMetadata(sorted(all_found), sorted(all_missing), formats)
