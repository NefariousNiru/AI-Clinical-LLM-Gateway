# gateway/util/error_mapping.py
"""
file: gateway/util/error_mapping.py

Error normalization layer: converts diverse provider/SDK exceptions into a single
`AppError` type with stable codes, kinds, and gRPC statuses.

Decision order (short-circuited):
  1) HTTP status code (robust against SDK surface changes)
  2) SDK-specific exception classes (OpenAI / Anthropic)
  3) Generic timeouts / network / httpx
  4) Fallback -> UNEXPECTED_ERROR

Policy:
  - TREAT_RATE_LIMIT_AS_TERMINAL: if True, 429 -> Terminal (RESOURCE_EXHAUSTED)
  - Context-length and model-not-found hints map to specific Terminal codes

Notes on optional imports:
  - Providers/SDKs (openai, anthropic, httpx) may be optional dependencies depending on
    the runtime environment. We import them inside `try` blocks and gracefully degrade
    to feature-detection via attributes and status-code paths when absent.
"""

# 1) Imports & optional SDKs
import asyncio
import re
import socket
import grpc
from pydantic import ValidationError

from gateway.util.errors import AppError, ErrorKind, ErrorMessages, TerminalError, TransientError

# Optional: httpx
try:  # ok if httpx is not installed at runtime
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

# Optional: OpenAI SDK exceptions
try:  # ok if openai is not installed
    from openai import (  # type: ignore
        APIError as OpenAIApiError,
        APITimeoutError as OpenAITimeoutError,
        AuthenticationError as OpenAIAuthError,
        BadRequestError as OpenAIBadRequestError,
        NotFoundError as OpenAINotFoundError,
        RateLimitError as OpenAIRateLimitError,
    )
except Exception:  # pragma: no cover
    OpenAIApiError = OpenAITimeoutError = OpenAIAuthError = OpenAIBadRequestError = OpenAINotFoundError = OpenAIRateLimitError = None  # type: ignore

# Optional: Anthropic SDK exceptions
try:  # ok if anthropic is not installed
    from anthropic import (  # type: ignore
        APIError as AnthropicApiError,
        APITimeoutError as AnthropicAPITimeoutError,
        AuthenticationError as AnthropicAuthError,
        BadRequestError as AnthropicBadRequestError,
        NotFoundError as AnthropicNotFoundError,
        RateLimitError as AnthropicRateLimitError,
    )
except Exception:  # pragma: no cover
    AnthropicApiError = AnthropicAPITimeoutError = AnthropicAuthError = AnthropicBadRequestError = AnthropicNotFoundError = AnthropicRateLimitError = None  # type: ignore


# 2) Policy flags & heuristics
TREAT_RATE_LIMIT_AS_TERMINAL = True

_CONTEXT_LEN_HINTS = ("maximum context length", "too long", "context_length_exceeded")
_MODEL_NOT_FOUND_HINTS = ("model_not_found", "does not exist", "unknown model", "no such model")


# 3) Small helpers
def _match_any_instance(obj: object, classes: tuple | None) -> bool:
    """Return True iff obj is an instance of any class in `classes` (when provided)."""
    return bool(classes) and isinstance(obj, classes)  # type: ignore[arg-type]


def _is_context_len(msg: str) -> bool:
    m = (msg or "").lower()
    return any(h in m for h in _CONTEXT_LEN_HINTS)


def _is_model_not_found(msg: str) -> bool:
    m = (msg or "").lower()
    return any(h in m for h in _MODEL_NOT_FOUND_HINTS)


def _status_code_of(e: Exception) -> int | None:
    """Best-effort extraction of an HTTP status code from diverse SDK exceptions."""
    # 1) direct attribute
    sc = getattr(e, "status_code", None)
    if isinstance(sc, int):
        return sc
    # 2) response.status_code (httpx, SDK wrappers)
    resp = getattr(e, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if isinstance(sc, int):
            return sc
    # 3) last-ditch: parse digits in str(e)
    m = re.search(r"\b(4\d{2}|5\d{2})\b", str(e))
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


# 4) Tiny constructors (stable AppError shapes)
def _as_rate_limited(cause: str | None) -> AppError:
    if TREAT_RATE_LIMIT_AS_TERMINAL:
        return AppError(
            TerminalError.RATE_LIMITED,
            ErrorKind.TERMINAL,
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            ErrorMessages.RATE_LIMITED,
            cause,
        )
    return AppError(
        TransientError.NETWORK_ERROR,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.NETWORK_ERROR,
        cause,
    )


def _as_bad_request(msg: str) -> AppError:
    if _is_context_len(msg):
        return AppError(
            TerminalError.CONTEXT_TOO_LONG,
            ErrorKind.TERMINAL,
            grpc.StatusCode.FAILED_PRECONDITION,
            ErrorMessages.CONTEXT_TOO_LONG,
            msg,
        )
    if _is_model_not_found(msg):
        return AppError(
            TerminalError.UNSUPPORTED_MODEL,
            ErrorKind.TERMINAL,
            grpc.StatusCode.INVALID_ARGUMENT,
            ErrorMessages.UNSUPPORTED_MODEL,
            msg,
        )
    return AppError(
        TerminalError.INVALID_PAYLOAD,
        ErrorKind.TERMINAL,
        grpc.StatusCode.INVALID_ARGUMENT,
        ErrorMessages.INVALID_PAYLOAD,
        msg,
    )


def _as_api_5xx(msg: str) -> AppError:
    return AppError(
        TransientError.PROVIDER_5XX,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.PROVIDER_5XX,
        msg,
    )


def _as_timeout(msg: str) -> AppError:
    return AppError(
        TransientError.PROVIDER_TIMEOUT,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        ErrorMessages.PROVIDER_TIMEOUT,
        msg,
    )


def _as_network(msg: str) -> AppError:
    return AppError(
        TransientError.NETWORK_ERROR,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.NETWORK_ERROR,
        msg,
    )


def _from_status_code(sc: int, msg: str) -> AppError | None:
    """Map an HTTP status code to a canonical AppError (or None if not mapped)."""
    if sc in (401, 403):
        return AppError(
            TerminalError.AUTH_FAILED,
            ErrorKind.TERMINAL,
            grpc.StatusCode.UNAUTHENTICATED,
            ErrorMessages.AUTH_FAILED,
            msg,
        )
    if sc == 404:
        return AppError(
            TerminalError.UNSUPPORTED_MODEL,
            ErrorKind.TERMINAL,
            grpc.StatusCode.INVALID_ARGUMENT,
            ErrorMessages.UNSUPPORTED_MODEL,
            msg,
        )
    if sc == 429:
        return _as_rate_limited(msg)
    if sc == 400:
        return _as_bad_request(msg)
    if 500 <= sc <= 599:
        return _as_api_5xx(msg)
    return None


# 5) Public classifier
def classify_exception(e: Exception) -> AppError:
    """
    Normalize arbitrary exceptions into AppError with stable code/kind/grpc_status.

    Returns:
        AppError
    """

    # A) Instructor / Pydantic schema mismatch -> transient
    if isinstance(e, ValidationError):
        return AppError(
            TransientError.SCHEMA_MISMATCH,
            ErrorKind.TRANSIENT,
            grpc.StatusCode.UNAVAILABLE,
            ErrorMessages.SCHEMA_MISMATCH,
            str(e),
        )

    # B) Status-code–first (works across httpx/OpenAI/Anthropic wrappers)
    sc = _status_code_of(e)
    if sc is not None:
        mapped = _from_status_code(sc, str(e))
        if mapped:
            return mapped

    # C) SDK-specific exception classes
    #    Build tuples only for classes that are actually available at runtime.
    auth_excs = tuple(filter(None, (OpenAIAuthError, AnthropicAuthError))) or None
    not_found_excs = tuple(filter(None, (OpenAINotFoundError, AnthropicNotFoundError))) or None
    rate_limit_excs = tuple(filter(None, (OpenAIRateLimitError, AnthropicRateLimitError))) or None
    bad_request_excs = (
        tuple(filter(None, (OpenAIBadRequestError, AnthropicBadRequestError))) or None
    )
    api_error_excs = tuple(filter(None, (OpenAIApiError, AnthropicApiError))) or None
    timeout_excs = tuple(filter(None, (OpenAITimeoutError, AnthropicAPITimeoutError))) or None

    if _match_any_instance(e, auth_excs):
        return AppError(
            TerminalError.AUTH_FAILED,
            ErrorKind.TERMINAL,
            grpc.StatusCode.UNAUTHENTICATED,
            ErrorMessages.AUTH_FAILED,
            str(e),
        )
    if _match_any_instance(e, not_found_excs):
        return AppError(
            TerminalError.UNSUPPORTED_MODEL,
            ErrorKind.TERMINAL,
            grpc.StatusCode.INVALID_ARGUMENT,
            ErrorMessages.UNSUPPORTED_MODEL,
            str(e),
        )
    if _match_any_instance(e, rate_limit_excs):
        return _as_rate_limited(str(e))
    if _match_any_instance(e, bad_request_excs):
        return _as_bad_request(str(e))
    if _match_any_instance(e, api_error_excs):
        # If SDK exposes non-5xx here, status-code path above would already have mapped it.
        return _as_api_5xx(str(e))
    if _match_any_instance(e, timeout_excs):
        return _as_timeout(str(e))

    # D) Generic timeouts / network / httpx family
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return _as_timeout(str(e))
    if isinstance(e, (socket.gaierror, ConnectionError, OSError)):
        return _as_network(str(e))

    if httpx:
        # D.1) timeouts
        if isinstance(e, (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.TimeoutException)):  # type: ignore[attr-defined]
            return _as_timeout(str(e))
        # D.2) network-ish
        if isinstance(
            e,
            (  # type: ignore[attr-defined]
                httpx.ConnectError,
                httpx.NetworkError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
                httpx.WriteError,
            ),
        ):
            return _as_network(str(e))
        # D.3) explicit HTTP status error (NO RECURSION)
        if isinstance(e, httpx.HTTPStatusError):  # type: ignore[attr-defined]
            sc2 = _status_code_of(e)
            mapped = _from_status_code(sc2, str(e)) if sc2 is not None else None
            return mapped or _as_network(str(e))

    # E) Fallback: unexpected terminal error
    return AppError(
        TerminalError.UNEXPECTED_ERROR,
        ErrorKind.TERMINAL,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.UNEXPECTED_ERROR,
        str(e),
    )


def extract_error_headers(
    error: OpenAIRateLimitError,
) -> dict[str, str]:
    """
    Extract lower-cased headers from an OpenAI rate-limit exception.

    Args:
        error: OpenAI rate-limit exception.

    Returns:
        Dictionary of lower-cased header names to values.
    """
    # 1) Read response object if present.
    response = getattr(error, "response", None)
    if response is None:
        return {}

    # 2) Read headers if present.
    raw_headers = getattr(response, "headers", None)
    if raw_headers is None:
        return {}

    # 3) Normalize header names to lower case.
    return {str(k).lower(): str(v) for k, v in raw_headers.items()}
