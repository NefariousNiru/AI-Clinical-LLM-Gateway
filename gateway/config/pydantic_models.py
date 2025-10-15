# gateway/config/pydantic_models.py
"""Pydantic models used for typed LLM responses and envelopes."""
from pydantic import BaseModel, Field, constr
from typing import List

NonEmptyStr = constr(strip_whitespace=True, min_length=1)


class FeedbackSection(BaseModel):
    """Atomic rubric-aligned chunk of feedback."""

    score: NonEmptyStr
    evaluation: NonEmptyStr
    feedback: NonEmptyStr


class ProblemFeedback(BaseModel):
    """Feedback for a single clinical problem."""

    name: NonEmptyStr
    is_priority: bool = False
    identification: FeedbackSection
    explanation: FeedbackSection
    plan_recommendation: FeedbackSection
    monitoring: FeedbackSection


class FeedbackEnvelope(BaseModel):
    """Wrapper produced by Instructor when Chatting with LLM"""

    feedback: ProblemFeedback
    # When error == True, 'feedback' may be empty and 'errors' should explain why.
    error: bool = Field(
        default=False,
        description="Flag to set true if any problem is encountered.",
    )
    errors: List[str] = Field(
        default_factory=list, description="Human-readable reasons for error"
    )


class ChatServiceResponse(BaseModel):
    """Top Level Chat Service response"""

    envelope: FeedbackEnvelope
    input_tokens: int
    output_tokens: int
