# gateway/providers/provider_registry.py
from typing import Union
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from gateway.providers.dummy_provider import DummyProvider
from gateway.config.settings import settings

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
    :raises ValueError
    :param name: Provider name
    :return: Provider instance
    """
    try:
        return PROVIDER_REGISTER[name.lower()]()
    except KeyError:
        raise ValueError(f"{name}")
