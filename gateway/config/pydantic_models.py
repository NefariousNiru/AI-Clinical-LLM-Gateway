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
    identification: FeedbackSection = Field(default_factory=FeedbackSection)
    explanation: FeedbackSection = Field(default_factory=FeedbackSection)
    plan_recommendation: FeedbackSection = Field(default_factory=FeedbackSection)
    monitoring: FeedbackSection = Field(default_factory=FeedbackSection)


class FeedbackEnvelope(BaseModel):
    feedback: List[ProblemFeedback]
