from pathlib import Path

from fantasy_nfl.config.paths import (
    AUDIT_SAMPLES_DIR,
    DATA_DIR,
    MODEL_DIR,
    NOTEBOOKS_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    REPO_ROOT,
    SNAPSHOT_DIR,
    ensure_data_dirs,
)


def test_repo_root_exists():
    assert REPO_ROOT.exists()


def test_path_objects():
    for p in [DATA_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR, SNAPSHOT_DIR, MODEL_DIR, AUDIT_SAMPLES_DIR, NOTEBOOKS_DIR]:
        assert isinstance(p, Path)


def test_ensure_data_dirs_creates_expected_dirs():
    ensure_data_dirs()
    assert DATA_DIR.exists()
    assert RAW_DATA_DIR.exists()
    assert PROCESSED_DATA_DIR.exists()
    assert SNAPSHOT_DIR.exists()
    assert MODEL_DIR.exists()
    assert AUDIT_SAMPLES_DIR.exists()
