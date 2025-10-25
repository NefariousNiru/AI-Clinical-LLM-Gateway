# tests/test_grader_service.py
import pytest
from gateway.service.grader_service import GraderService
from gateway.grader.v1 import grader_pb2
from tests.conftest import FakeServicerContext


@pytest.mark.asyncio
async def test_validate_prompts_empty_system_aborts():
    svc = GraderService()
    ctx = FakeServicerContext()
    req = grader_pb2.GradeRequest(
        system_prompt=" ", user_prompt="ok", model_provider="dummy", model_name="n/a"
    )
    with pytest.raises(RuntimeError) as ei:
        await svc._validate_prompts(req, ctx)
    assert "INVALID_ARGUMENT" in str(ei.value)


@pytest.mark.asyncio
async def test_validate_prompts_empty_user_aborts():
    svc = GraderService()
    ctx = FakeServicerContext()
    req = grader_pb2.GradeRequest(
        system_prompt="ok", user_prompt=" ", model_provider="dummy", model_name="n/a"
    )
    with pytest.raises(RuntimeError):
        await svc._validate_prompts(req, ctx)


@pytest.mark.asyncio
async def test_success_path_with_dummy_provider():
    svc = GraderService()
    ctx = FakeServicerContext()
    req = grader_pb2.GradeRequest(
        system_prompt="s",
        user_prompt="u",
        model_provider="dummy",
        model_name="n/a",
        trace_id="t-1",
        job_id="j-1",
    )
    resp = await svc.Grade(req, ctx)
    assert isinstance(resp, grader_pb2.GradeResponse)
    assert resp.feedback.name != ""


@pytest.mark.asyncio
async def test_unsupported_provider_aborts(monkeypatch):
    svc = GraderService()
    ctx = FakeServicerContext()
    req = grader_pb2.GradeRequest(
        system_prompt="s", user_prompt="u", model_provider="nope", model_name="x"
    )
    with pytest.raises(RuntimeError) as ei:
        await svc._get_chat_service(req, ctx)
    # message should be INVALID_ARGUMENT with unsupported provider text embedded by GraderService
    assert "INVALID_ARGUMENT" in str(ei.value)
