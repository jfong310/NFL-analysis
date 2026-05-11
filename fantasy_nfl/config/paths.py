"""Centralized filesystem paths for the project."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
AUDIT_DIR = DATA_DIR / "audit"
AUDIT_SAMPLES_DIR = AUDIT_DIR / "samples"
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"


def ensure_data_dirs() -> None:
    """Create expected data and notebook directories if they do not exist."""
    for path in [
        DATA_DIR,
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        SNAPSHOT_DIR,
        AUDIT_DIR,
        AUDIT_SAMPLES_DIR,
        NOTEBOOKS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
