from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
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
        "rubrics",
        "payload",
        "system_prompt",
        "user_prompt_template",
        "model_provider",
        "model_name",
        "trace_id",
        "job_id",
    )
    RUBRICS_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    USER_PROMPT_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    rubrics: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    payload: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    system_prompt: str
    user_prompt_template: str
    model_provider: str
    model_name: str
    trace_id: str
    job_id: str
    def __init__(
        self,
        rubrics: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...,
        payload: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...,
        system_prompt: _Optional[str] = ...,
        user_prompt_template: _Optional[str] = ...,
        model_provider: _Optional[str] = ...,
        model_name: _Optional[str] = ...,
        trace_id: _Optional[str] = ...,
        job_id: _Optional[str] = ...,
    ) -> None: ...

class GradeResponse(_message.Message):
    __slots__ = ("feedback", "model_provider", "model_name")
    FEEDBACK_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    feedback: _containers.RepeatedCompositeFieldContainer[ProblemFeedback]
    model_provider: str
    model_name: str
    def __init__(
        self,
        feedback: _Optional[_Iterable[_Union[ProblemFeedback, _Mapping]]] = ...,
        model_provider: _Optional[str] = ...,
        model_name: _Optional[str] = ...,
    ) -> None: ...
