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
        "fantasy_nfl.models.baseline",
        "fantasy_nfl.models.evaluate",
        "fantasy_nfl.models.boosting",
        "fantasy_nfl.analysis.backtest_report",
        "fantasy_nfl.ingest.market",
        "fantasy_nfl.transform.market",
        "fantasy_nfl.analysis.draft_value",
        "fantasy_nfl.analysis.html_board",
        "fantasy_nfl.analysis.boosting_report",
        "fantasy_nfl.audit.scoring_validation",
    ]
    for name in modules:
        importlib.import_module(name)
