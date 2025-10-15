# gateway/providers/dummy_provider.py
from gateway.config.pydantic_models import (
    ChatServiceResponse,
    FeedbackEnvelope,
    FeedbackSection,
    ProblemFeedback,
)


class DummyProvider:
    """No-LLM provider: Dummy to test"""

    @staticmethod
    def get_dummy_response():
        """Return a mock ChatServiceResponse for testing ChatService without a real provider."""
        dummy_section = FeedbackSection(
            score="1",
            evaluation="Clear explanation of pathophysiology and risk factors.",
            feedback="Continue using structured reasoning and evidence-backed arguments.",
        )

        dummy_feedback = ProblemFeedback(
            name="Hypertension Management",
            is_priority=True,
            identification=dummy_section,
            explanation=dummy_section,
            plan_recommendation=dummy_section,
            monitoring=dummy_section,
        )

        dummy_envelope = FeedbackEnvelope(
            feedback=dummy_feedback,
            error=False,
            errors=[],
        )

        return ChatServiceResponse(
            envelope=dummy_envelope,
            input_tokens=1050,
            output_tokens=320,
        )
