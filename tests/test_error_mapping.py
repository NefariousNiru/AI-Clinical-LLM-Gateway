# tests/test_error_mapping.py
import types
import pytest
import grpc
from pydantic import ValidationError
from gateway.util.error_mapping import classify_exception
from gateway.util.errors import ErrorKind, TerminalError, TransientError


class _StatusExc(Exception):
    """
    Exception test double that carries .status_code and .response.status_code,
    and whose __str__ returns the provided message so error_mapping can parse hints.
    """

    def __init__(self, status_code: int, msg: str = "boom"):
        super().__init__(msg)
        self.status_code = status_code
        self.response = types.SimpleNamespace(status_code=status_code)


def _exc_with_status(status_code: int, msg: str = "boom"):
    return _StatusExc(status_code, msg)


@pytest.mark.parametrize(
    "status,code,kind,grpc_status",
    [
        (401, TerminalError.AUTH_FAILED, ErrorKind.TERMINAL, grpc.StatusCode.UNAUTHENTICATED),
        (403, TerminalError.AUTH_FAILED, ErrorKind.TERMINAL, grpc.StatusCode.UNAUTHENTICATED),
        (
            404,
            TerminalError.UNSUPPORTED_MODEL,
            ErrorKind.TERMINAL,
            grpc.StatusCode.INVALID_ARGUMENT,
        ),
        (429, TerminalError.RATE_LIMITED, ErrorKind.TERMINAL, grpc.StatusCode.RESOURCE_EXHAUSTED),
        (500, TransientError.PROVIDER_5XX, ErrorKind.TRANSIENT, grpc.StatusCode.UNAVAILABLE),
        (503, TransientError.PROVIDER_5XX, ErrorKind.TRANSIENT, grpc.StatusCode.UNAVAILABLE),
    ],
)
def test_status_code_mapping(status, code, kind, grpc_status):
    err = classify_exception(_exc_with_status(status))
    assert err.code == code
    assert err.kind == kind
    assert err.grpc_status == grpc_status


def test_bad_request_context_too_long():
    e = _exc_with_status(400, "Input exceeds the maximum context length supported by the model")
    err = classify_exception(e)
    assert err.code == TerminalError.CONTEXT_TOO_LONG
    assert err.grpc_status == grpc.StatusCode.FAILED_PRECONDITION


def test_bad_request_unknown_model():
    e = _exc_with_status(400, "unknown model foo-1")
    err = classify_exception(e)
    assert err.code == TerminalError.UNSUPPORTED_MODEL
    assert err.grpc_status == grpc.StatusCode.INVALID_ARGUMENT


def test_validation_error_maps_to_schema_mismatch():
    # Create a minimal ValidationError without relying on a real model instance
    try:
        raise ValidationError.from_exception_data("X", [])
    except ValidationError as ve:
        err = classify_exception(ve)
        assert err.code == TransientError.SCHEMA_MISMATCH
        assert err.kind == ErrorKind.TRANSIENT
        assert err.grpc_status == grpc.StatusCode.UNAVAILABLE
