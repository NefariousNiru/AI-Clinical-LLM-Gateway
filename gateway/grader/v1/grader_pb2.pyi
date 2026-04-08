from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FeedbackSection(_message.Message):
    __slots__ = ("score", "evaluation", "feedback")
    SCORE_FIELD_NUMBER: _ClassVar[int]
    EVALUATION_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_FIELD_NUMBER: _ClassVar[int]
    score: str
    evaluation: str
    feedback: str
    def __init__(
        self,
        score: _Optional[str] = ...,
        evaluation: _Optional[str] = ...,
        feedback: _Optional[str] = ...,
    ) -> None: ...

class ProblemFeedback(_message.Message):
    __slots__ = (
        "name",
        "is_priority",
        "identification",
        "explanation",
        "plan_recommendation",
        "monitoring",
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
        name: _Optional[str] = ...,
        is_priority: bool = ...,
        identification: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
        explanation: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
        plan_recommendation: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
        monitoring: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
    ) -> None: ...

class GradeRequest(_message.Message):
    __slots__ = (
        "system_prompt",
        "user_prompt",
        "model_provider",
        "model_name",
        "trace_id",
        "job_id",
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
        system_prompt: _Optional[str] = ...,
        user_prompt: _Optional[str] = ...,
        model_provider: _Optional[str] = ...,
        model_name: _Optional[str] = ...,
        trace_id: _Optional[str] = ...,
        job_id: _Optional[str] = ...,
    ) -> None: ...

class GradeResponse(_message.Message):
    __slots__ = ("feedback",)
    FEEDBACK_FIELD_NUMBER: _ClassVar[int]
    feedback: ProblemFeedback
    def __init__(self, feedback: _Optional[_Union[ProblemFeedback, _Mapping]] = ...) -> None: ...
