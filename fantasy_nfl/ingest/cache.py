"""Local parquet cache and provenance records for nflverse datasets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable

import pandas as pd

from fantasy_nfl.config.paths import RAW_DATA_DIR
from fantasy_nfl.utils.logging import get_logger

logger = get_logger(__name__)


def cache_stem(dataset_name: str, seasons: list[int] | None) -> str:
    season_token = "all" if seasons is None else f"{min(seasons)}-{max(seasons)}"
    return f"{dataset_name}_{season_token}"


def cache_paths(
    dataset_name: str, seasons: list[int] | None, cache_dir: Path = RAW_DATA_DIR
) -> tuple[Path, Path]:
    stem = cache_stem(dataset_name, seasons)
    return cache_dir / f"{stem}.parquet", cache_dir / f"{stem}.provenance.json"


def read_cached(
    dataset_name: str, seasons: list[int] | None, cache_dir: Path = RAW_DATA_DIR
) -> dict[str, Any] | None:
    data_path, _ = cache_paths(dataset_name, seasons, cache_dir)
    if not data_path.exists():
        return None
    try:
        return {
            "status": "success",
            "dataset_name": dataset_name,
            "data": pd.read_parquet(data_path),
            "error": "",
            "cache_status": "hit",
            "cache_path": str(data_path),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ignoring unreadable cache %s: %s", data_path, exc)
        return None


def write_cached(
    dataset_name: str,
    seasons: list[int] | None,
    frame: pd.DataFrame,
    cache_dir: Path = RAW_DATA_DIR,
) -> Path:
    data_path, provenance_path = cache_paths(dataset_name, seasons, cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(data_path, index=False)
    try:
        nflreadpy_version = version("nflreadpy")
    except PackageNotFoundError:
        nflreadpy_version = "unknown"
    provenance = {
        "dataset_name": dataset_name,
        "seasons": seasons,
        "source": "nflverse via nflreadpy",
        "nflreadpy_version": nflreadpy_version,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": list(frame.columns),
        "data_path": str(data_path),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, default=str), encoding="utf-8")
    return data_path


def load_or_fetch(
    dataset_name: str,
    seasons: list[int] | None,
    loader: Callable[[], dict[str, Any]],
    *,
    refresh: bool = False,
    cache_dir: Path = RAW_DATA_DIR,
) -> dict[str, Any]:
    if not refresh:
        cached = read_cached(dataset_name, seasons, cache_dir)
        if cached is not None:
            return cached
    result = loader()
    if result.get("status") == "success" and result.get("data") is not None:
        path = write_cached(dataset_name, seasons, result["data"], cache_dir)
        result.update({"cache_status": "miss", "cache_path": str(path)})
    return result
