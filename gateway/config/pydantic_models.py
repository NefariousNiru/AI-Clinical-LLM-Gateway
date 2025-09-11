from pydantic import BaseModel, Field
from typing import List


class FeedbackSection(BaseModel):
    score: str = ""
    evaluation: str = ""
    feedback: str = ""


class ProblemFeedback(BaseModel):
    name: str
    is_priority: bool = False
    identification: FeedbackSection = Field(default_factory=FeedbackSection)
    explanation: FeedbackSection = Field(default_factory=FeedbackSection)
    plan_recommendation: FeedbackSection = Field(default_factory=FeedbackSection)
    monitoring: FeedbackSection = Field(default_factory=FeedbackSection)


class FeedbackEnvelope(BaseModel):
    feedback: List[ProblemFeedback]
