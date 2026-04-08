from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EmbedRowRequest(_message.Message):
    __slots__ = (
        "workup_id",
        "submission_id",
        "disease_id",
        "section_type",
        "student_answer_text",
        "feedback_text",
    )
    WORKUP_ID_FIELD_NUMBER: _ClassVar[int]
    SUBMISSION_ID_FIELD_NUMBER: _ClassVar[int]
    DISEASE_ID_FIELD_NUMBER: _ClassVar[int]
    SECTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    STUDENT_ANSWER_TEXT_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_TEXT_FIELD_NUMBER: _ClassVar[int]
    workup_id: int
    submission_id: str
    disease_id: str
    section_type: str
    student_answer_text: str
    feedback_text: str
    def __init__(
        self,
        workup_id: _Optional[int] = ...,
        submission_id: _Optional[str] = ...,
        disease_id: _Optional[str] = ...,
        section_type: _Optional[str] = ...,
        student_answer_text: _Optional[str] = ...,
        feedback_text: _Optional[str] = ...,
    ) -> None: ...

class EmbedRowResponse(_message.Message):
    __slots__ = (
        "workup_id",
        "submission_id",
        "disease_id",
        "section_type",
        "student_answer_text",
        "student_answer_vector",
        "feedback_text",
        "feedback_vector",
        "embedding_model",
    )
    WORKUP_ID_FIELD_NUMBER: _ClassVar[int]
    SUBMISSION_ID_FIELD_NUMBER: _ClassVar[int]
    DISEASE_ID_FIELD_NUMBER: _ClassVar[int]
    SECTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    STUDENT_ANSWER_TEXT_FIELD_NUMBER: _ClassVar[int]
    STUDENT_ANSWER_VECTOR_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_TEXT_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_VECTOR_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_MODEL_FIELD_NUMBER: _ClassVar[int]
    workup_id: int
    submission_id: str
    disease_id: str
    section_type: str
    student_answer_text: str
    student_answer_vector: _containers.RepeatedScalarFieldContainer[float]
    feedback_text: str
    feedback_vector: _containers.RepeatedScalarFieldContainer[float]
    embedding_model: str
    def __init__(
        self,
        workup_id: _Optional[int] = ...,
        submission_id: _Optional[str] = ...,
        disease_id: _Optional[str] = ...,
        section_type: _Optional[str] = ...,
        student_answer_text: _Optional[str] = ...,
        student_answer_vector: _Optional[_Iterable[float]] = ...,
        feedback_text: _Optional[str] = ...,
        feedback_vector: _Optional[_Iterable[float]] = ...,
        embedding_model: _Optional[str] = ...,
    ) -> None: ...

class EmbedBatchRequest(_message.Message):
    __slots__ = ("rows", "model_provider", "model_name", "trace_id", "job_id")
    ROWS_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedCompositeFieldContainer[EmbedRowRequest]
    model_provider: str
    model_name: str
    trace_id: str
    job_id: str
    def __init__(
        self,
        rows: _Optional[_Iterable[_Union[EmbedRowRequest, _Mapping]]] = ...,
        model_provider: _Optional[str] = ...,
        model_name: _Optional[str] = ...,
        trace_id: _Optional[str] = ...,
        job_id: _Optional[str] = ...,
    ) -> None: ...

class EmbedBatchResponse(_message.Message):
    __slots__ = ("rows",)
    ROWS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedCompositeFieldContainer[EmbedRowResponse]
    def __init__(
        self, rows: _Optional[_Iterable[_Union[EmbedRowResponse, _Mapping]]] = ...
    ) -> None: ...
