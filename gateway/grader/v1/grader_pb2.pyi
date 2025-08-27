from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CriterionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CRITERION_TYPE_UNSPECIFIED: _ClassVar[CriterionType]
    MUST: _ClassVar[CriterionType]
    SHOULD: _ClassVar[CriterionType]
    BONUS: _ClassVar[CriterionType]
    CONTRAINDICATION: _ClassVar[CriterionType]

CRITERION_TYPE_UNSPECIFIED: CriterionType
MUST: CriterionType
SHOULD: CriterionType
BONUS: CriterionType
CONTRAINDICATION: CriterionType

class Criterion(_message.Message):
    __slots__ = ("key", "type", "verbiage", "weight")
    KEY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VERBIAGE_FIELD_NUMBER: _ClassVar[int]
    WEIGHT_FIELD_NUMBER: _ClassVar[int]
    key: str
    type: CriterionType
    verbiage: str
    weight: float
    def __init__(
        self,
        key: _Optional[str] = ...,
        type: _Optional[_Union[CriterionType, str]] = ...,
        verbiage: _Optional[str] = ...,
        weight: _Optional[float] = ...,
    ) -> None: ...

class Section(_message.Message):
    __slots__ = ("id", "title", "max_points", "evaluation_question", "criteria")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    MAX_POINTS_FIELD_NUMBER: _ClassVar[int]
    EVALUATION_QUESTION_FIELD_NUMBER: _ClassVar[int]
    CRITERIA_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    max_points: float
    evaluation_question: str
    criteria: _containers.RepeatedCompositeFieldContainer[Criterion]
    def __init__(
        self,
        id: _Optional[str] = ...,
        title: _Optional[str] = ...,
        max_points: _Optional[float] = ...,
        evaluation_question: _Optional[str] = ...,
        criteria: _Optional[_Iterable[_Union[Criterion, _Mapping]]] = ...,
    ) -> None: ...

class RubricPayload(_message.Message):
    __slots__ = ("rubric_id", "guideline_hint", "sections")
    RUBRIC_ID_FIELD_NUMBER: _ClassVar[int]
    GUIDELINE_HINT_FIELD_NUMBER: _ClassVar[int]
    SECTIONS_FIELD_NUMBER: _ClassVar[int]
    rubric_id: str
    guideline_hint: str
    sections: _containers.RepeatedCompositeFieldContainer[Section]
    def __init__(
        self,
        rubric_id: _Optional[str] = ...,
        guideline_hint: _Optional[str] = ...,
        sections: _Optional[_Iterable[_Union[Section, _Mapping]]] = ...,
    ) -> None: ...

class DrugRelatedProblem(_message.Message):
    __slots__ = (
        "is_priority",
        "identification",
        "explanation",
        "plan_recommendation",
        "monitoring",
    )
    IS_PRIORITY_FIELD_NUMBER: _ClassVar[int]
    IDENTIFICATION_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    PLAN_RECOMMENDATION_FIELD_NUMBER: _ClassVar[int]
    MONITORING_FIELD_NUMBER: _ClassVar[int]
    is_priority: bool
    identification: str
    explanation: str
    plan_recommendation: str
    monitoring: str
    def __init__(
        self,
        is_priority: bool = ...,
        identification: _Optional[str] = ...,
        explanation: _Optional[str] = ...,
        plan_recommendation: _Optional[str] = ...,
        monitoring: _Optional[str] = ...,
    ) -> None: ...

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
        "is_priority",
        "identification",
        "explanation",
        "plan_recommendation",
        "monitoring",
    )
    IS_PRIORITY_FIELD_NUMBER: _ClassVar[int]
    IDENTIFICATION_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    PLAN_RECOMMENDATION_FIELD_NUMBER: _ClassVar[int]
    MONITORING_FIELD_NUMBER: _ClassVar[int]
    is_priority: bool
    identification: FeedbackSection
    explanation: FeedbackSection
    plan_recommendation: FeedbackSection
    monitoring: FeedbackSection
    def __init__(
        self,
        is_priority: bool = ...,
        identification: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
        explanation: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
        plan_recommendation: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
        monitoring: _Optional[_Union[FeedbackSection, _Mapping]] = ...,
    ) -> None: ...

class GradeRequest(_message.Message):
    __slots__ = (
        "rubric",
        "problems",
        "system_prompt",
        "user_prompt_template",
        "model_provider",
        "model_name",
        "trace_id",
        "job_id",
    )
    RUBRIC_FIELD_NUMBER: _ClassVar[int]
    PROBLEMS_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    USER_PROMPT_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    rubric: RubricPayload
    problems: _containers.RepeatedCompositeFieldContainer[DrugRelatedProblem]
    system_prompt: str
    user_prompt_template: str
    model_provider: str
    model_name: str
    trace_id: str
    job_id: str
    def __init__(
        self,
        rubric: _Optional[_Union[RubricPayload, _Mapping]] = ...,
        problems: _Optional[_Iterable[_Union[DrugRelatedProblem, _Mapping]]] = ...,
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
