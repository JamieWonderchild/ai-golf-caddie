import os
import importlib
import sys
import pytest


def test_load_config_requires_api_key(monkeypatch):
    monkeypatch.delenv("SPEECHMATICS_API_KEY", raising=False)
    # Ensure no .env leaks in test env
    monkeypatch.setenv("SPEECHMATICS_API_KEY", "", prepend=False)
    # reload module to clear cache
    if "golfcaddie.config" in sys.modules:
        importlib.reload(sys.modules["golfcaddie.config"])
    from golfcaddie import config

    with pytest.raises(RuntimeError):
        config.reload_config()


def test_load_config_success(monkeypatch):
    monkeypatch.setenv("SPEECHMATICS_API_KEY", "testkey")
    from golfcaddie.config import reload_config

    cfg = reload_config()
    assert cfg.speechmatics_api_key == "testkey"
    assert cfg.db_path.endswith("app.db")

