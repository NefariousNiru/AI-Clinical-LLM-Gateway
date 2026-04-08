"""
file: gateway/config/models.py

Pydantic models used for typed LLM responses and envelopes.
"""

from dataclasses import dataclass
from typing import TypeVar, Generic

from pydantic import BaseModel, Field, constr
from gateway.util.enums import EmbeddingSectionType

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


class Envelope(BaseModel):
    """
    Envelope super class

    Attributes:
        error (bool): set true if any problem is encountered during generation. Defaults to False.
        errors (list[str]): human-readable reasons describing the error condition.
    """

    error: bool = Field(
        default=False,
        description="Flag to set true if any problem is encountered.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Human-readable reasons for error",
    )


class FeedbackEnvelope(Envelope):
    """
    FeedbackEnvelope payload.

    Attributes:
        feedback (ProblemFeedback): structured feedback object.
        error (bool): set true if any problem is encountered during generation. Defaults to False.
        errors (list[str]): human-readable reasons describing the error condition.
    """

    feedback: ProblemFeedback


class XYZEnvelope(Envelope):
    """
    Some Envelope payload.
    Placeholder
    Attributes:
        some_attribute (str): dummy placeholder
        error (bool): set true if any problem is encountered during generation. Defaults to False.
        errors (list[str]): human-readable reasons describing the error condition.
    """

    some_attribute: str


EnvelopeT = TypeVar("EnvelopeT", bound=Envelope)


class ChatServiceResponse(BaseModel, Generic[EnvelopeT]):
    """
    ChatServiceResponse payload.

    Attributes:
        envelope (EnvelopeT): top-level response container.
        input_tokens (int): number of tokens consumed for input.
        output_tokens (int): number of tokens produced in the output.
    """

    envelope: EnvelopeT
    input_tokens: int
    output_tokens: int


class EmbedRowRequest(BaseModel):
    """
    Extension (pydantic representation of embedding_pb2.EmbedRowRequest).

    Attributes:
        workup_id: Parent workup identifier.
        submission_id: Student submission identifier.
        disease_id: Disease / rubric identifier.
        section_type: Which answer/feedback section this row represents.
        student_answer_text: Plain student answer text for the section.
        feedback_text: Plain feedback text for the section.
    """

    workup_id: int
    submission_id: str
    disease_id: str
    section_type: EmbeddingSectionType
    student_answer_text: str
    feedback_text: str


@dataclass(slots=True)
class EmbedMiniBatch:
    """
    Minibatch container.

    Attributes:
        batch_index: Stable minibatch order index.
        rows: Proto rows belonging to this minibatch.
        total_tokens: Total estimated tokens across all texts in this minibatch.
    """

    batch_index: int
    rows: list[EmbedRowRequest]
    total_tokens: int
