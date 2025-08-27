# gateway/config/provider_factory.py
from gateway.interface.provider_interface import Provider
from gateway.providers.dummy_provider import DummyProvider


def get_provider(provider: str) -> Provider:
    provider_name = provider.lower()

    if provider_name == "dummy":
        return DummyProvider()
    elif provider_name == "openai":
        from gateway.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()
    elif provider_name == "ollama":
        from gateway.providers.ollama_provider import OllamaProvider

        return OllamaProvider()
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")
