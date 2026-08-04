import importlib


def test_core_imports():
    modules = [
        "fantasy_nfl.config.paths",
        "fantasy_nfl.config.seasons",
        "fantasy_nfl.ingest.nflverse",
        "fantasy_nfl.audit.data_audit",
        "fantasy_nfl.config.scoring",
        "fantasy_nfl.transform.scoring",
        "fantasy_nfl.transform.targets",
        "fantasy_nfl.transform.features",
        "fantasy_nfl.audit.feature_audit",
        "fantasy_nfl.audit.scoring_validation",
    ]
    for name in modules:
        importlib.import_module(name)
