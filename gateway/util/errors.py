# gateway/util/errors.py
from dataclasses import dataclass
from enum import Enum

import grpc


class ErrorKind(Enum):
    TERMINAL = "TERMINAL"
    TRANSIENT = "TRANSIENT"


@dataclass
class AppError(Exception):
    code: str
    kind: ErrorKind
    grpc_status: grpc.StatusCode
    details: str
    cause: str

    def __str__(self) -> str:
        return f"{self.code} [{self.kind.value}]: {self.details}"


class TerminalError:
    AUTH_FAILED = "auth_failed"
    UNSUPPORTED_MODEL = "unsupported_model"
    UNSUPPORTED_PROVIDER = "unsupported_provider"
    INVALID_SYSTEM_PROMPT = "invalid_system_prompt"
    INVALID_USER_PROMPT = "invalid_user_prompt"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    CONTEXT_TOO_LONG = "context_too_long"
    UNEXPECTED_ERROR = "unexpected_error"
    INVALID_PAYLOAD = "invalid_payload"


class TransientError:
    PROVIDER_TIMEOUT = "provider_timeout"
    NETWORK_ERROR = "network_error"
    PROVIDER_5XX = "provider_5xx"
    SCHEMA_MISMATCH = "schema_mismatch"
    LLM_SIGNALED_ERROR = "llm_signaled_error"


class ErrorMessages:
    """Maps messages for TransientError and TerminalError and Others"""

    # Terminal errors (non-retryable)
    AUTH_FAILED = "Authentication failed. Please check your API key or credentials."
    UNSUPPORTED_MODEL = "The requested model is not supported by this provider."
    UNSUPPORTED_PROVIDER = "The requested provider is not supported."
    INVALID_SYSTEM_PROMPT = "The system prompt is invalid or improperly formatted."
    INVALID_USER_PROMPT = "The user prompt is invalid or empty."
    QUOTA_EXCEEDED = "Quota exceeded. Please upgrade your plan or try again later."
    RATE_LIMITED = "Too many requests. Please slow down and retry after some time."
    CONTEXT_TOO_LONG = "The input exceeds the maximum context length supported by the model."
    INVALID_PAYLOAD = "Invalid payload received."
    UNEXPECTED_ERROR = "An unexpected error occurred."

    # Transient errors (retryable)
    PROVIDER_TIMEOUT = "The provider did not respond in time. Please retry."
    NETWORK_ERROR = "A network issue occurred while contacting the provider."
    PROVIDER_5XX = "The provider encountered an internal error (5xx). Retry may succeed."
    SCHEMA_MISMATCH = "The model's response did not match the expected schema."
    LLM_SIGNALED_ERROR = "The model signaled an internal error or aborted unexpectedly."

    # Others
    SET_SHARED_TOKEN = "SHARED_TOKEN not set in env or is invalid"
