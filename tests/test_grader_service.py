# tests/test_grader_service.py

import pytest
from gateway.service.grader_service import GraderService
from tests.conftest import FakeServicerContext
from gateway.grader.v1 import grader_pb2


def make_submission(name="Hypertension", priority=True):
    return f"""
    student_submission:
    {{
      "name": "{name}",
      "isPriority": {str(priority).lower()}
    }}
    """


@pytest.mark.asyncio
async def test_success_path_with_dummy_provider():
    svc = GraderService()
    ctx = FakeServicerContext()

    req = grader_pb2.GradeRequest(
        system_prompt="system",
        user_prompt=make_submission("Hypertension", True),
        model_provider="dummy",
        model_name="n/a",
        trace_id="t-1",
        job_id="j-1",
    )

    resp = await svc.Grade(req, ctx)

    assert resp.feedback.name == "Hypertension"
    assert resp.feedback.is_priority is True

    assert resp.feedback.identification.score == "1.0"
    assert resp.feedback.explanation.score == "1.0"
    assert resp.feedback.plan_recommendation.score == "1.0"
    assert resp.feedback.monitoring.score == "1.0"


@pytest.mark.asyncio
async def test_non_priority_problem():
    svc = GraderService()
    ctx = FakeServicerContext()

    req = grader_pb2.GradeRequest(
        system_prompt="system",
        user_prompt=make_submission("Diabetes", False),
        model_provider="dummy",
        model_name="n/a",
        trace_id="t-2",
        job_id="j-2",
    )

    resp = await svc.Grade(req, ctx)

    assert resp.feedback.name == "Diabetes"
    assert resp.feedback.is_priority is False


@pytest.mark.asyncio
async def test_missing_name_causes_abort():
    svc = GraderService()
    ctx = FakeServicerContext()

    req = grader_pb2.GradeRequest(
        system_prompt="system",
        user_prompt="""
        student_submission:
        {
          "isPriority": true
        }
        """,
        model_provider="dummy",
        model_name="n/a",
        trace_id="t-3",
        job_id="j-3",
    )

    with pytest.raises(RuntimeError) as exc:
        await svc.Grade(req, ctx)

    assert "Missing 'name'" in str(exc.value)


@pytest.mark.asyncio
async def test_missing_submission_section():
    svc = GraderService()
    ctx = FakeServicerContext()

    req = grader_pb2.GradeRequest(
        system_prompt="system",
        user_prompt="random prompt",
        model_provider="dummy",
        model_name="n/a",
        trace_id="t-4",
        job_id="j-4",
    )

    with pytest.raises(RuntimeError):
        await svc.Grade(req, ctx)
