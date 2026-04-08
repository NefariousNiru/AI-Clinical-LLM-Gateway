"""
file: gateway/config/models.py

Pydantic models used for typed LLM responses and envelopes.
"""

from pydantic import BaseModel, Field, constr

NonEmptyStr = constr(strip_whitespace=True, min_length=1)


class FeedbackSection(BaseModel):
    """
    FeedbackSection payload.

    Attributes:
        score (NonEmptyStr): rubric score or rating for this section.
        evaluation (NonEmptyStr): brief assessment or rationale.
        feedback (NonEmptyStr): actionable comments or guidance.
    """

    score: NonEmptyStr
    evaluation: NonEmptyStr
    feedback: NonEmptyStr


class ProblemFeedback(BaseModel):
    """
    ProblemFeedback payload.

    Attributes:
        name (NonEmptyStr): identifier or title of the clinical problem.
        is_priority (bool): whether this problem is flagged as priority. Defaults to False.
        identification (FeedbackSection): scoring and comments for identification.
        explanation (FeedbackSection): scoring and comments for explanation.
        plan_recommendation (FeedbackSection): scoring and comments for plan/recommendation.
        monitoring (FeedbackSection): scoring and comments for monitoring and follow-up.
    """

    name: NonEmptyStr
    is_priority: bool = False
    identification: FeedbackSection
    explanation: FeedbackSection
    plan_recommendation: FeedbackSection
    monitoring: FeedbackSection


class FeedbackEnvelope(BaseModel):
    """
    FeedbackEnvelope payload.

    Attributes:
        feedback (ProblemFeedback): structured feedback object.
        error (bool): set true if any problem is encountered during generation. Defaults to False.
        errors (list[str]): human-readable reasons describing the error condition.
    """

    feedback: ProblemFeedback
    error: bool = Field(
        default=False,
        description="Flag to set true if any problem is encountered.",
    )  # When error == True, 'feedback' may be empty and 'errors' should explain why.
    errors: list[str] = Field(default_factory=list, description="Human-readable reasons for error")


class ChatServiceResponse(BaseModel):
    """
    ChatServiceResponse payload.

    Attributes:
        envelope (FeedbackEnvelope): top-level response container.
        input_tokens (int): number of tokens consumed for input.
        output_tokens (int): number of tokens produced in the output.
    """

    envelope: FeedbackEnvelope
    input_tokens: int
    output_tokens: int
