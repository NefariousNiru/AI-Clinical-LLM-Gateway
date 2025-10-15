# tests/test_chat_service_dummy.py
import pytest
from gateway.providers.dummy_provider import DummyProvider
from gateway.service.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_service_with_dummy_provider_returns_structured_envelope():
    svc = ChatService(DummyProvider())
    resp = await svc.grade(
        system_prompt="s",
        user_prompt="u",
        model_name="n/a",
        trace_id="t-1",
        job_id="j-1",
    )
    assert resp.envelope.feedback.name == "Hypertension Management"
    assert isinstance(resp.input_tokens, int)
    assert isinstance(resp.output_tokens, int)
