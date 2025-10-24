"""
file: gateway/providers/provider_registry.py

Provider registry for constructing typed SDK clients (OpenAI, Anthropic, Ollama) or DummyProvider.

Supported names (case-insensitive): {"openai","anthropic","ollama","dummy"}.
Returns concrete async SDK clients (AsyncOpenAI, AsyncAnthropic) or DummyProvider.
Raises:
    ValueError: if the provider name is not registered.
"""

from typing import Union
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from gateway.config.settings import settings
from gateway.providers.dummy_provider import DummyProvider

# --- registry dict instead of a class or decorators ---
PROVIDER_REGISTER = {
    "openai": lambda: AsyncOpenAI(api_key=settings.openai_api_key),
    "ollama": lambda: AsyncOpenAI(base_url=settings.ollama_host, api_key="ollama"),
    "anthropic": lambda: AsyncAnthropic(api_key=settings.anthropic_api_key),
    "dummy": lambda: DummyProvider(),
}

Provider = Union[AsyncOpenAI, AsyncAnthropic, DummyProvider]


def get_provider(name: str) -> Provider:
    """
    Return a concrete provider client for the given name.
    Args:
        name: One of {"openai","anthropic","ollama","dummy"} (case-insensitive).
    Returns:
        Provider: AsyncOpenAI, AsyncAnthropic, or DummyProvider.
    Raises:
        ValueError: If `name` is not registered.
    """
    try:
        return PROVIDER_REGISTER[name.lower()]()
    except KeyError:
        raise ValueError(f"{name}")
