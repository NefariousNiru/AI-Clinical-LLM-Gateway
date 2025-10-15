from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor

class FeedbackSection(_message.Message):
    __slots__ = ("evaluation", "feedback", "score")
    SCORE_FIELD_NUMBER: _ClassVar[int]
    EVALUATION_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_FIELD_NUMBER: _ClassVar[int]
    score: str
    evaluation: str
    feedback: str
    def __init__(
        self,
        score: str | None = ...,
        evaluation: str | None = ...,
        feedback: str | None = ...,
    ) -> None: ...

class ProblemFeedback(_message.Message):
    __slots__ = (
        "explanation",
        "identification",
        "is_priority",
        "monitoring",
        "name",
        "plan_recommendation",
    )
    NAME_FIELD_NUMBER: _ClassVar[int]
    IS_PRIORITY_FIELD_NUMBER: _ClassVar[int]
    IDENTIFICATION_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    PLAN_RECOMMENDATION_FIELD_NUMBER: _ClassVar[int]
    MONITORING_FIELD_NUMBER: _ClassVar[int]
    name: str
    is_priority: bool
    identification: FeedbackSection
    explanation: FeedbackSection
    plan_recommendation: FeedbackSection
    monitoring: FeedbackSection
    def __init__(
        self,
        name: str | None = ...,
        is_priority: bool = ...,
        identification: FeedbackSection | _Mapping | None = ...,
        explanation: FeedbackSection | _Mapping | None = ...,
        plan_recommendation: FeedbackSection | _Mapping | None = ...,
        monitoring: FeedbackSection | _Mapping | None = ...,
    ) -> None: ...

class GradeRequest(_message.Message):
    __slots__ = (
        "job_id",
        "model_name",
        "model_provider",
        "system_prompt",
        "trace_id",
        "user_prompt",
    )
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    USER_PROMPT_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    system_prompt: str
    user_prompt: str
    model_provider: str
    model_name: str
    trace_id: str
    job_id: str
    def __init__(
        self,
        system_prompt: str | None = ...,
        user_prompt: str | None = ...,
        model_provider: str | None = ...,
        model_name: str | None = ...,
        trace_id: str | None = ...,
        job_id: str | None = ...,
    ) -> None: ...

class GradeResponse(_message.Message):
    __slots__ = ("feedback",)
    FEEDBACK_FIELD_NUMBER: _ClassVar[int]
    feedback: ProblemFeedback
    def __init__(self, feedback: ProblemFeedback | _Mapping | None = ...) -> None: ...
