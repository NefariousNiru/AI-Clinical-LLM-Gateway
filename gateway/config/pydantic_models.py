from pydantic import BaseModel, Field, constr
from typing import List

NonEmptyStr = constr(strip_whitespace=True, min_length=1)

class FeedbackSection(BaseModel):
    score: NonEmptyStr
    evaluation: NonEmptyStr
    feedback: NonEmptyStr


class ProblemFeedback(BaseModel):
    name: NonEmptyStr
    is_priority: bool = False
    identification: FeedbackSection
    explanation: FeedbackSection
    plan_recommendation: FeedbackSection
    monitoring: FeedbackSection


class FeedbackEnvelope(BaseModel):
    feedback: List[ProblemFeedback]
    # When error == True, 'feedback' may be empty and 'errors' should explain why.
    error: bool = False
    errors: List[str] = Field(default_factory=list, description="Human-readable reasons")
