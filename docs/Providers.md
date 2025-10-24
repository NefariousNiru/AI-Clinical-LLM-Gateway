# Providers

The registry supports these names (case-insensitive):

- `openai` → `AsyncOpenAI(api_key=OPENAI_API_KEY)`
- `anthropic` → `AsyncAnthropic(api_key=ANTHROPIC_API_KEY)`
- `ollama` → `AsyncOpenAI(base_url=OLLAMA_HOST, api_key='ollama')`
- `dummy` → `DummyProvider()` (local testing, no network)

`ChatService` adapts calls:
- OpenAI: uses Instructor JSON mode.
- Anthropic: uses Anthropic JSON via Instructor, sets `max_tokens` from settings.
- Dummy: returns a canned `ChatServiceResponse` with deterministic payload.

#### To add more Providers: 
- Register them in `provider_registry.py` and add it in class `ChatService`
```python
    def __init__(self, raw_client: Provider):
        self.raw_client = raw_client
        if isinstance(raw_client, AsyncOpenAI):
            self.client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
        elif isinstance(raw_client, AsyncAnthropic):
            self.client = instructor.from_anthropic(raw_client, mode=instructor.Mode.ANTHROPIC_JSON)
        elif isinstance(raw_client, DummyProvider):
            self.client = raw_client
        # Add more here and return appropriate instructor wrapper in client. 
```