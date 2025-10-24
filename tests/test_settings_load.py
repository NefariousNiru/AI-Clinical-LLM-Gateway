# tests/test_settings_load.py
from importlib import reload
from gateway.config import settings as settings_mod


def test_settings_defaults_present(monkeypatch):
    # ensure no crash on import; validate a few key defaults
    s = settings_mod.settings
    assert isinstance(s.port, int)
    assert s.host
    assert s.log_level


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "60000")
    monkeypatch.setenv("MODEL_TEMPERATURE", "0.7")
    # re-import module to rebuild Settings
    reload(settings_mod)
    s = settings_mod.settings
    assert s.host == "127.0.0.1"
    assert s.port == 60000
    assert s.model_temperature == 0.7
