# tests/test_chat_service_instructor_mock.py
import types
import pytest
import instructor
from openai import AsyncOpenAI

# Import both the class and the module so we can patch the type that ChatService checks
from gateway.service import chat_service as chat_service_mod
from gateway.service.chat_service import ChatService
from gateway.config.pydantic_models import FeedbackEnvelope, ChatServiceResponse


class FakeAsyncInstructor:
    """
    Test double that mimics the surface of instructor.AsyncInstructor enough for ChatService:
    - Provides .chat.completions.create_with_completion(...)
    - Returns (FeedbackEnvelope, completion_like_with_usage)
    """

    def __init__(self):
        class Chat:
            class Completions:
                async def create_with_completion(self, **kwargs):
                    # Build a minimal valid FeedbackEnvelope and a fake completion with usage
                    env = FeedbackEnvelope.model_validate(
                        {
                            "feedback": {
                                "name": "Problem",
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
                        prompt_tokens = 11
                        completion_tokens = 7

                    completion = types.SimpleNamespace(usage=Usage())
                    return env, completion

            completions = Completions()

        self.chat = Chat()


@pytest.mark.asyncio
async def test_chat_service_openai_instructor(monkeypatch):
    # Construct a harmless OpenAI client. We won't make network calls because we patch Instructor.
    raw = AsyncOpenAI(api_key="test", base_url="http://localhost")

    # 1) Patch instructor.from_openai to return our fake wrapper
    monkeypatch.setattr(instructor, "from_openai", lambda *_args, **_kw: FakeAsyncInstructor())

    # 2) Make ChatService's isinstance(self.client, AsyncInstructor) check pass
    #    by replacing the AsyncInstructor symbol that ChatService imports with our fake class.
    monkeypatch.setattr(chat_service_mod, "AsyncInstructor", FakeAsyncInstructor)

    svc = ChatService(raw)
    resp: ChatServiceResponse = await svc.grade(
        system_prompt="s",
        user_prompt="u",
        model_name="gpt-4o-mini",  # any non gpt-5 to exercise temperature injection path
        trace_id="t-1",
        job_id="j-1",
    )

    assert resp.envelope.feedback.name == "Problem"
    assert resp.input_tokens == 11
    assert resp.output_tokens == 7
