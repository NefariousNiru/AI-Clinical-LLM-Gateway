# tests/test_pydantic_proto_roundtrip.py

from gateway.service.grader_service import GraderService
from gateway.grader.v1 import grader_pb2
from gateway.config.models import (
    FeedbackSection as PydFeedbackSection,
    ProblemFeedback as PydProblemFeedback,
)


def _mk_pyd_feedback():
    sec = PydFeedbackSection(score="3", evaluation="good", feedback="keep going")
    return PydProblemFeedback(
        name="Hypertension Management",
        is_priority=True,
        identification=sec,
        explanation=PydFeedbackSection(score="2", evaluation="avg", feedback="improve depth"),
        plan_recommendation=PydFeedbackSection(
            score="4", evaluation="strong", feedback="clear plan"
        ),
        monitoring=PydFeedbackSection(score="1", evaluation="weak", feedback="needs schedule"),
    )


def _assert_section_equal(proto: grader_pb2.FeedbackSection, pyd: PydFeedbackSection):
    assert proto.score == pyd.score
    assert proto.evaluation == pyd.evaluation
    assert proto.feedback == pyd.feedback


def test_pydantic_to_proto_roundtrip_field_equality():
    # Arrange: start from a Pydantic ProblemFeedback
    pyd = _mk_pyd_feedback()

    # Act: use the service’s mapper to convert Pydantic -> Proto
    svc = GraderService()
    proto: grader_pb2.ProblemFeedback = svc._pydantic_to_proto_problem_feedback(pyd)

    # Assert: every field matches exactly
    assert proto.name == pyd.name
    assert proto.is_priority == pyd.is_priority

    _assert_section_equal(proto.identification, pyd.identification)
    _assert_section_equal(proto.explanation, pyd.explanation)
    _assert_section_equal(proto.plan_recommendation, pyd.plan_recommendation)
    _assert_section_equal(proto.monitoring, pyd.monitoring)
