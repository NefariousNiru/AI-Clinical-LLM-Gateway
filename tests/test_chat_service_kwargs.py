# tests/test_chat_service_kwargs.py
import pytest
import instructor
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from gateway.service import chat_service as chat_service_mod
from gateway.service.chat_service import ChatService
from gateway.config.settings import settings
from gateway.config.models import FeedbackEnvelope


class CapturingInstructor:
    def __init__(self):
        self.last_kwargs = None

        class Chat:
            class Completions:
                def __init__(self, outer):
                    self.outer = outer

                async def create_with_completion(self, **kwargs):
                    self.outer.last_kwargs = kwargs
                    # minimal valid envelope + fake usage
                    env = FeedbackEnvelope.model_validate(
                        {
                            "feedback": {
                                "name": "P",
                                "is_priority": False,
                                "identification": {
                                    "score": "1",
                                    "evaluation": "ok",
                                    "feedback": "ok",
                                },
                                "explanation": {"score": "1", "evaluation": "ok", "feedback": "ok"},
                                "plan_recommendation": {
                                    "score": "1",
                                    "evaluation": "ok",
                                    "feedback": "ok",
                                },
                                "monitoring": {"score": "1", "evaluation": "ok", "feedback": "ok"},
                            },
                            "error": False,
                            "errors": [],
                        }
                    )

                    class Usage:
                        prompt_tokens = 1
                        completion_tokens = 1

                    completion = type("C", (), {"usage": Usage})()
                    return env, completion

            def __init__(self, outer):
                self.completions = Chat.Completions(outer)

        self.chat = Chat(self)


@pytest.mark.asyncio
async def test_openai_non_gpt5_includes_temperature(monkeypatch):
    raw = AsyncOpenAI(api_key="test", base_url="http://localhost")
    fake = CapturingInstructor()
    monkeypatch.setattr(instructor, "from_openai", lambda *_a, **_k: fake)
    monkeypatch.setattr(chat_service_mod, "AsyncInstructor", CapturingInstructor)

    svc = ChatService(raw)
    _ = await svc.grade(
        system_prompt="s", user_prompt="u", model_name="gpt-4o-mini", trace_id="t", job_id="j"
    )
    kw = fake.last_kwargs
    assert kw["model"] == "gpt-4o-mini"
    assert kw["temperature"] == settings.model_temperature
    assert kw["max_retries"] == settings.instructor_max_retry
    assert kw["strict"] is True


@pytest.mark.asyncio
async def test_openai_gpt5_omits_temperature(monkeypatch):
    raw = AsyncOpenAI(api_key="test", base_url="http://localhost")
    fake = CapturingInstructor()
    monkeypatch.setattr(instructor, "from_openai", lambda *_a, **_k: fake)
    monkeypatch.setattr(chat_service_mod, "AsyncInstructor", CapturingInstructor)

    svc = ChatService(raw)
    _ = await svc.grade(
        system_prompt="s", user_prompt="u", model_name="gpt-5-turbo", trace_id="t", job_id="j"
    )
    kw = fake.last_kwargs
    assert "temperature" not in kw  # omitted for gpt-5*


@pytest.mark.asyncio
async def test_anthropic_includes_max_tokens(monkeypatch):
    raw = AsyncAnthropic(api_key="test")
    fake = CapturingInstructor()
    monkeypatch.setattr(instructor, "from_anthropic", lambda *_a, **_k: fake)
    monkeypatch.setattr(chat_service_mod, "AsyncInstructor", CapturingInstructor)

    svc = ChatService(raw)
    _ = await svc.grade(
        system_prompt="s", user_prompt="u", model_name="claude-3-haiku", trace_id="t", job_id="j"
    )
    kw = fake.last_kwargs
    assert kw["max_tokens"] == settings.anthropic_max_tokens
