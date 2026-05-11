"""Defensive wrappers around nflreadpy dataset loaders."""

from __future__ import annotations

from typing import Any

try:
    import pandas as pd
except Exception:  # noqa: BLE001
    pd = None

from fantasy_nfl.utils.logging import get_logger

logger = get_logger(__name__)


def _import_nflreadpy():
    try:
        import nflreadpy  # type: ignore

        return nflreadpy, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _to_pandas(obj: Any) -> pd.DataFrame:
    if pd is not None and isinstance(obj, pd.DataFrame):
        return obj
    if hasattr(obj, "to_pandas"):
        return obj.to_pandas()
    raise TypeError(f"Unsupported dataframe type: {type(obj)}")


def _try_load(dataset_name: str, candidate_functions: list[str], seasons: list[int] | None = None) -> dict[str, Any]:
    nflreadpy, import_error = _import_nflreadpy()
    if nflreadpy is None:
        msg = f"nflreadpy unavailable: {import_error}"
        logger.warning(msg)
        return {"status": "failed", "dataset_name": dataset_name, "data": None, "error": msg}

    for fn_name in candidate_functions:
        fn = getattr(nflreadpy, fn_name, None)
        if fn is None:
            continue
        try:
            data = fn(seasons=seasons) if seasons is not None else fn()
            return {"status": "success", "dataset_name": dataset_name, "data": _to_pandas(data), "error": ""}
        except TypeError:
            try:
                data = fn(seasons) if seasons is not None else fn()
                return {"status": "success", "dataset_name": dataset_name, "data": _to_pandas(data), "error": ""}
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s failed via %s: %s", dataset_name, fn_name, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("%s failed via %s: %s", dataset_name, fn_name, exc)

    msg = f"No working nflreadpy loader found for {dataset_name}. Checked: {candidate_functions}"
    return {"status": "failed", "dataset_name": dataset_name, "data": None, "error": msg}


def load_player_stats_safe(seasons: list[int]) -> dict[str, Any]:
    return _try_load("player_stats_weekly", ["load_player_stats", "load_weekly_player_stats", "import_weekly_data"], seasons)


def load_rosters_safe(seasons: list[int]) -> dict[str, Any]:
    return _try_load("rosters", ["load_rosters", "import_seasonal_rosters"], seasons)


def load_players_safe() -> dict[str, Any]:
    return _try_load("players", ["load_players", "import_players"])


def load_schedules_safe(seasons: list[int]) -> dict[str, Any]:
    return _try_load("schedules", ["load_schedules", "import_schedules"], seasons)


def load_snap_counts_safe(seasons: list[int]) -> dict[str, Any]:
    return _try_load("snap_counts", ["load_snap_counts", "import_snap_counts"], seasons)


def load_injuries_safe(seasons: list[int]) -> dict[str, Any]:
    return _try_load("injuries", ["load_injuries", "import_injuries"], seasons)


def load_ff_playerids_safe() -> dict[str, Any]:
    return _try_load("fantasy_player_ids", ["load_ff_playerids", "load_fantasy_player_ids", "import_ids"])


def load_ff_opportunity_safe(seasons: list[int]) -> dict[str, Any]:
    return _try_load(
        "ff_opportunity_weekly",
        ["load_ff_opportunity", "load_weekly_fantasy_stats", "import_weekly_fantasy_stats"],
        seasons,
    )
