import pandas as pd
import json

from fantasy_nfl.ingest.cache import load_or_fetch, read_cached


def test_cache_round_trip_and_hit(tmp_path):
    calls = {"count": 0}

    def loader():
        calls["count"] += 1
        return {"status": "success", "dataset_name": "weekly", "data": pd.DataFrame({"season": [2024]}), "error": ""}

    first = load_or_fetch("weekly", [2024], loader, cache_dir=tmp_path)
    second = load_or_fetch("weekly", [2024], loader, cache_dir=tmp_path)

    assert first["cache_status"] == "miss"
    assert second["cache_status"] == "hit"
    assert calls["count"] == 1
    assert read_cached("weekly", [2024], tmp_path)["data"].equals(pd.DataFrame({"season": [2024]}))
    provenance_path = tmp_path / "weekly_2024-2024.provenance.json"
    assert provenance_path.exists()
    assert json.loads(provenance_path.read_text())["nflreadpy_version"]
