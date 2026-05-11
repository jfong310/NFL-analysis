"""Input/output helpers for data artifacts."""

from pathlib import Path

from typing import Any

try:
    import pandas as pd
except Exception:  # noqa: BLE001
    pd = None

from fantasy_nfl.utils.logging import get_logger

logger = get_logger(__name__)


def save_dataframe(df: Any, path: Path) -> Path:
    """Save a dataframe, preferring parquet and falling back to CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    parquet_path = path.with_suffix(".parquet")
    try:
        df.to_parquet(parquet_path, index=False)
        return parquet_path
    except Exception as exc:  # noqa: BLE001
        logger.warning("Parquet save failed for %s (%s). Falling back to CSV.", parquet_path, exc)
        csv_path = path.with_suffix(".csv")
        df.to_csv(csv_path, index=False)
        return csv_path


def save_sample(df: Any, path: Path, n: int = 1000) -> Path:
    """Save a row-limited sample dataframe."""
    sample = df.head(n).copy()
    return save_dataframe(sample, path)


def write_markdown(path: Path, content: str) -> Path:
    """Write markdown content to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
