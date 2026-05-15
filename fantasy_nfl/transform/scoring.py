from __future__ import annotations

from dataclasses import dataclass

from fantasy_nfl.config.scoring import DEFAULT_SCORING_FORMAT, SCORING_FORMATS, get_scoring_config


@dataclass
class ScoringMetadata:
    scoring_columns_found: list[str]
    scoring_columns_missing: list[str]
    scoring_formats_generated: list[str]


def normalize_player_week_columns(df):
    rename_map = {"player_position": "position", "posteam": "team", "recent_team": "team"}
    out = df.copy()
    for src, dst in rename_map.items():
        if src in out.columns and dst not in out.columns:
            out = out.rename(columns={src: dst})
    return out


def _series_or_zero(df, col):
    if col in df.columns:
        return df[col].fillna(0)
    return 0


def calculate_fantasy_points(df, scoring_format="ppr"):
    cfg = get_scoring_config(scoring_format)
    points = 0
    found, missing = [], []
    for col, mult in cfg.items():
        if col in df.columns:
            found.append(col)
        else:
            missing.append(col)
        points = points + (_series_or_zero(df, col) * mult)
    return points, found, missing


def score_player_weeks(df, scoring_formats=None):
    out = normalize_player_week_columns(df)
    formats = scoring_formats or list(SCORING_FORMATS.keys())
    all_found, all_missing = set(), set()
    for fmt in formats:
        points, found, missing = calculate_fantasy_points(out, fmt)
        out[f"fantasy_points_{fmt}"] = points
        all_found.update(found)
        all_missing.update(missing)
    out["fantasy_points"] = out[f"fantasy_points_{DEFAULT_SCORING_FORMAT}"]
    return out, ScoringMetadata(sorted(all_found), sorted(all_missing - all_found), formats)
