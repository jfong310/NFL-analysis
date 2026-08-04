from pathlib import Path

import pandas as pd

import fantasy_nfl.audit.data_audit as audit
from tests.test_player_week import datasets


def test_end_to_end_audit_outputs(monkeypatch, tmp_path):
    source = datasets()

    def result(name):
        return {"status": "success", "dataset_name": name, "data": source[name], "error": ""}

    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit, "AUDIT_SAMPLES_DIR", tmp_path / "samples")
    monkeypatch.setattr(audit, "load_or_fetch", lambda name, seasons, loader, refresh=False: loader())
    monkeypatch.setattr(audit, "load_player_stats_safe", lambda seasons: result("player_stats_weekly"))
    monkeypatch.setattr(audit, "load_rosters_safe", lambda seasons: result("rosters"))
    monkeypatch.setattr(audit, "load_players_safe", lambda: result("players"))
    monkeypatch.setattr(audit, "load_schedules_safe", lambda seasons: result("schedules"))
    monkeypatch.setattr(audit, "load_snap_counts_safe", lambda seasons: result("snap_counts"))
    monkeypatch.setattr(audit, "load_injuries_safe", lambda seasons: result("injuries"))
    monkeypatch.setattr(audit, "load_ff_playerids_safe", lambda: result("fantasy_player_ids"))
    monkeypatch.setattr(audit, "load_ff_opportunity_safe", lambda seasons: result("ff_opportunity_weekly"))

    inventory_path, markdown_path, inventory = audit.run_data_audit([2024])

    assert len(inventory) == 8
    assert Path(inventory_path).exists()
    assert Path(markdown_path).exists()
    assert (tmp_path / "sample_player_week.parquet").exists()
    assert (tmp_path / "player_id_join_report.csv").exists()
    text = Path(markdown_path).read_text(encoding="utf-8")
    assert "Player-Week Join Quality" in text
    assert "Chunk 1 Artifacts" in text
