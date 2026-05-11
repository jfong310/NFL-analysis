import importlib


def test_core_imports():
    modules = [
        "fantasy_nfl.config.paths",
        "fantasy_nfl.config.seasons",
        "fantasy_nfl.ingest.nflverse",
        "fantasy_nfl.audit.data_audit",
    ]
    for name in modules:
        importlib.import_module(name)
