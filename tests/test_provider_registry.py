# tests/test_provider_registry.py
import pytest
from gateway.providers.provider_registry import get_provider


@pytest.mark.parametrize("name", ["openai", "anthropic", "ollama", "dummy"])
def test_get_provider_known(name, monkeypatch):
    # Prevent accidental live SDK calls during construction where possible
    if name in {"openai", "ollama"}:
        monkeypatch.setenv("OPENAI_API_KEY", "test")  # AsyncOpenAI requires a key
    if name == "anthropic":
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    p = get_provider(name)
    assert p is not None


def test_get_provider_unknown():
    with pytest.raises(ValueError):
        get_provider("not-a-provider")
