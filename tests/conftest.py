# tests/conftest.py
import types
import pytest

from gateway.config.pydantic_models import (
    FeedbackSection as PydFeedbackSection,
    ProblemFeedback,
    FeedbackEnvelope,
    ChatServiceResponse,
)


class FakeServicerContext:
    """Minimal async replacement for grpc.aio.ServicerContext for unit tests."""

    def __init__(self):
        self._trailers = ()
        self._aborted = False
        self._abort_status = None
        self._abort_details = None
        self._invocation_metadata = {}

    # gRPC interceptor code calls this
    def invocation_metadata(self):
        return tuple(self._invocation_metadata.items())

    def set_test_metadata(self, **headers):
        self._invocation_metadata.update(headers)

    def set_trailing_metadata(self, md):
        self._trailers = tuple(md)

    @property
    def trailing_metadata(self):
        return self._trailers

    async def abort(self, status, details):
        # emulate grpc behavior: mark aborted and raise to stop flow
        self._aborted = True
        self._abort_status = status
        self._abort_details = details
        raise RuntimeError(f"aborted: {status.name} {details}")


@pytest.fixture
def fake_context():
    return FakeServicerContext()


@pytest.fixture
def sample_envelope():
    sec = PydFeedbackSection(
        score="1",
        evaluation="ok",
        feedback="ok",
    )
    fb = ProblemFeedback(
        name="Hypertension Management",
        is_priority=True,
        identification=sec,
        explanation=sec,
        plan_recommendation=sec,
        monitoring=sec,
    )
    env = FeedbackEnvelope(feedback=fb, error=False, errors=[])
    return env


@pytest.fixture
def sample_chat_response(sample_envelope):
    return ChatServiceResponse(envelope=sample_envelope, input_tokens=10, output_tokens=5)


@pytest.fixture
def fake_completion_with_usage():
    class U:
        prompt_tokens = 10
        completion_tokens = 5

    c = types.SimpleNamespace(usage=U())
    return c
