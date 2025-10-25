"""
file: gateway/util/errors.py

Typed error primitives for the gateway layer.

- ErrorKind: terminal vs transient classification.
- AppError: canonical error shape surfaced across the gateway.
- TerminalError / TransientError: stable machine-readable codes.
- ErrorMessages: short, user-facing messages for each error category.
"""

import grpc
from dataclasses import dataclass
from enum import Enum


class ErrorKind(Enum):
    """
    Attributes:
        TERMINAL: Non-retryable error; caller should not auto-retry.
        TRANSIENT: Retryable error; caller may retry with backoff.
    """

    TERMINAL = "TERMINAL"
    TRANSIENT = "TRANSIENT"


@dataclass
class AppError(Exception):
    """
    Canonical gateway error carrying a stable code, kind, gRPC status, and message.

    Attributes:
        code (str): Stable machine-readable error code (see TerminalError/TransientError).
        kind (ErrorKind): Whether the error is TERMINAL or TRANSIENT.
        grpc_status (grpc.StatusCode): gRPC status to return on the wire.
        details (str): Short human-readable description suitable for logs/clients.
        cause (Optional[str]): Optional raw/provider-specific detail for debugging.
    """

    code: str
    kind: ErrorKind
    grpc_status: grpc.StatusCode
    details: str
    cause: str

    def __str__(self) -> str:
        return f"{self.code} [{self.kind.value}]: {self.details}"


@dataclass(frozen=True)
class TerminalError:
    """
    Stable terminal error codes (non-retryable).

    Attributes:
        AUTH_FAILED: Authentication/authorization failed.
        UNSUPPORTED_MODEL: Requested model is not available/supported.
        UNSUPPORTED_PROVIDER: Requested provider is not supported.
        INVALID_SYSTEM_PROMPT: System prompt missing or malformed.
        INVALID_USER_PROMPT: User prompt missing or malformed.
        QUOTA_EXCEEDED: Account quota exceeded.
        RATE_LIMITED: Request rate limited (policy dependent).
        CONTEXT_TOO_LONG: Input exceeded model context window.
        UNEXPECTED_ERROR: Unknown/uncategorized terminal failure.
        INVALID_PAYLOAD: Client sent an invalid payload.
    """

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


@dataclass(frozen=True)
class TransientError:
    """
    Stable transient error codes (retryable).

    Attributes:
        PROVIDER_TIMEOUT: Upstream provider timed out.
        NETWORK_ERROR: Network/transport failure.
        PROVIDER_5XX: Provider returned a 5xx error.
        SCHEMA_MISMATCH: Model output failed schema validation.
        LLM_SIGNALED_ERROR: Model indicated an internal error.
    """

    PROVIDER_TIMEOUT = "provider_timeout"
    NETWORK_ERROR = "network_error"
    PROVIDER_5XX = "provider_5xx"
    SCHEMA_MISMATCH = "schema_mismatch"
    LLM_SIGNALED_ERROR = "llm_signaled_error"


@dataclass(frozen=True)
class ErrorMessages:
    """
    Short, user-facing messages corresponding to error codes.

    Attributes:
        AUTH_FAILED: authentication failures.
        UNSUPPORTED_MODEL: unsupported model requests.
        UNSUPPORTED_PROVIDER: unsupported provider requests.
        INVALID_SYSTEM_PROMPT: invalid system prompt.
        INVALID_USER_PROMPT: invalid user prompt.
        QUOTA_EXCEEDED: quota exhaustion.
        RATE_LIMITED: rate limiting.
        CONTEXT_TOO_LONG: context window overflow.
        INVALID_PAYLOAD: invalid client payloads.
        UNEXPECTED_ERROR: uncategorized failures.

        PROVIDER_TIMEOUT: provider timeouts.
        NETWORK_ERROR: network issues.
        PROVIDER_5XX: provider 5xx errors.
        SCHEMA_MISMATCH: schema validation failures.
        LLM_SIGNALED_ERROR: when model signals an error.

        SET_SHARED_TOKEN: when shared token env is not configured.
    """

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
