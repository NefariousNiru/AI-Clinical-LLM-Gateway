# gateway/util/error_mapping.py
"""
Maps provider/SDK exceptions to AppError with stable codes and gRPC status.

Decision order:
  1) HTTP status-code (robust to SDK churn)
  2) SDK-specific exception classes (OpenAI/Anthropic)
  3) Generic timeouts/network/httpx
  4) Fallback -> unexpected_error

Policy:
  - TREAT_RATE_LIMIT_AS_TERMINAL: if True, 429 -> Terminal (RESOURCE_EXHAUSTED).
  - Context-length and model-not-found are normalized to specific Terminal codes.

This layer is the single source of truth for error semantics surfaced by gRPC.
"""
import asyncio
import re
import socket
import grpc

try:
    import httpx
except Exception:
    httpx = None
from pydantic import ValidationError
from gateway.util.errors import AppError, ErrorKind, ErrorMessages, TerminalError, TransientError

try:
    from openai import (
        APIError as OpenAIApiError,
    )
    from openai import (
        APITimeoutError as OpenAITimeoutError,
    )
    from openai import (
        AuthenticationError as OpenAIAuthError,
    )
    from openai import (
        BadRequestError as OpenAIBadRequestError,
    )
    from openai import (
        NotFoundError as OpenAINotFoundError,
    )
    from openai import (
        RateLimitError as OpenAIRateLimitError,
    )
except Exception:  # pragma: no cover
    OpenAIApiError = OpenAIAuthError = OpenAIBadRequestError = OpenAITimeoutError = (
        OpenAINotFoundError
    ) = OpenAIRateLimitError = None
try:
    from anthropic import (
        APIError as AnthropicApiError,
    )
    from anthropic import (
        APITimeoutError as AnthropicAPITimeoutError,
    )
    from anthropic import (
        AuthenticationError as AnthropicAuthError,
    )
    from anthropic import (
        BadRequestError as AnthropicBadRequestError,
    )
    from anthropic import (
        NotFoundError as AnthropicNotFoundError,
    )
    from anthropic import (
        RateLimitError as AnthropicRateLimitError,
    )
except Exception:  # pragma: no cover
    AnthropicApiError = AnthropicAuthError = AnthropicBadRequestError = AnthropicNotFoundError = (
        AnthropicRateLimitError
    ) = AnthropicAPITimeoutError = None

# -------- Policy & heuristics --------
TREAT_RATE_LIMIT_AS_TERMINAL = True
CONTEXT_LEN_HINTS = ("maximum context length", "too long", "context_length_exceeded")
MODEL_NOT_FOUND_HINTS = (
    "model_not_found",
    "does not exist",
    "unknown model",
    "no such model",
)


def _is_context_len(msg: str) -> bool:
    m = (msg or "").lower()
    return any(h in m for h in CONTEXT_LEN_HINTS)


def _is_model_not_found(msg: str) -> bool:
    m = (msg or "").lower()
    return any(h in m for h in MODEL_NOT_FOUND_HINTS)


def _status_code_of(e: Exception) -> int | None:
    sc = getattr(e, "status_code", None)
    if isinstance(sc, int):
        return sc
    resp = getattr(e, "response", None)
    if resp is not None:
        sc = getattr(resp, "status_code", None)
        if isinstance(sc, int):
            return sc
    m = re.search(r"\b(4\d{2}|5\d{2})\b", str(e))
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    return None


# -------- Small constructors (short, stable details; raw in cause) --------
def _rate_limited(cause: str | None) -> AppError:
    if TREAT_RATE_LIMIT_AS_TERMINAL:
        return AppError(
            TerminalError.RATE_LIMITED,
            ErrorKind.TERMINAL,
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            ErrorMessages.RATE_LIMITED,
            cause,
        )
    # TODO: Mark as Network error for now. Surface when backend can handle timeouts as transient
    return AppError(
        TransientError.NETWORK_ERROR,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.NETWORK_ERROR,
        cause,
    )


def _bad_request(msg: str) -> AppError:
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


def _api_5xx(msg: str) -> AppError:
    return AppError(
        TransientError.PROVIDER_5XX,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.PROVIDER_5XX,
        msg,
    )


def _timeout(msg: str) -> AppError:
    return AppError(
        TransientError.PROVIDER_TIMEOUT,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.DEADLINE_EXCEEDED,
        ErrorMessages.PROVIDER_TIMEOUT,
        msg,
    )


def _network(msg: str) -> AppError:
    return AppError(
        TransientError.NETWORK_ERROR,
        ErrorKind.TRANSIENT,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.NETWORK_ERROR,
        msg,
    )


# ------------ Public classifier ------------
def classify_exception(e: Exception) -> AppError:
    """
    Normalize arbitrary exceptions into AppError with stable code/kind/grpc_status.
    Returns:
        AppError: One of Terminal/Transient variants defined in `gateway.util.errors`.
    """
    # 0) Instructor / Pydantic
    if isinstance(e, ValidationError):
        return AppError(
            TransientError.SCHEMA_MISMATCH,
            ErrorKind.TRANSIENT,
            grpc.StatusCode.UNAVAILABLE,
            ErrorMessages.SCHEMA_MISMATCH,
            str(e),
        )

    # 1) Status-code–first (robust to SDK churn and httpx wrappers)
    sc = _status_code_of(e)
    if sc is not None:
        msg = str(e)
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
            return _rate_limited(msg)
        if sc == 400:
            return _bad_request(msg)
        if 500 <= sc <= 599:
            return _api_5xx(msg)

    # 2) SDK-specific classes (OR-groups; concise)
    if (OpenAIAuthError and isinstance(e, OpenAIAuthError)) or (
        AnthropicAuthError and isinstance(e, AnthropicAuthError)
    ):
        return AppError(
            TerminalError.AUTH_FAILED,
            ErrorKind.TERMINAL,
            grpc.StatusCode.UNAUTHENTICATED,
            ErrorMessages.AUTH_FAILED,
            str(e),
        )
    if (OpenAINotFoundError and isinstance(e, OpenAINotFoundError)) or (
        AnthropicNotFoundError and isinstance(e, AnthropicNotFoundError)
    ):
        return AppError(
            TerminalError.UNSUPPORTED_MODEL,
            ErrorKind.TERMINAL,
            grpc.StatusCode.INVALID_ARGUMENT,
            ErrorMessages.UNSUPPORTED_MODEL,
            str(e),
        )
    if (OpenAIRateLimitError and isinstance(e, OpenAIRateLimitError)) or (
        AnthropicRateLimitError and isinstance(e, AnthropicRateLimitError)
    ):
        return _rate_limited(str(e))
    if (OpenAIBadRequestError and isinstance(e, OpenAIBadRequestError)) or (
        AnthropicBadRequestError and isinstance(e, AnthropicBadRequestError)
    ):
        return _bad_request(str(e))
    if (OpenAIApiError and isinstance(e, OpenAIApiError)) or (
        AnthropicApiError and isinstance(e, AnthropicApiError)
    ):
        # if SDK exposes non-5xx here, status-code path would have handled; treat as 5xx-ish
        return _api_5xx(str(e))
    if (OpenAITimeoutError and isinstance(e, OpenAITimeoutError)) or (
        AnthropicAPITimeoutError and isinstance(e, AnthropicAPITimeoutError)
    ):
        return _timeout(str(e))

    # 3) Generic timeouts / network / httpx
    if isinstance(e, (asyncio.TimeoutError, TimeoutError)):
        return _timeout(str(e))
    if isinstance(e, (socket.gaierror, ConnectionError, OSError)):
        return _network(str(e))
    if httpx:
        if isinstance(
            e,
            (
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                httpx.PoolTimeout,
                httpx.TimeoutException,
            ),
        ):
            return _timeout(str(e))
        if isinstance(
            e,
            (
                httpx.ConnectError,
                httpx.NetworkError,
                httpx.ReadError,
                httpx.RemoteProtocolError,
                httpx.WriteError,
            ),
        ):
            return _network(str(e))
        if isinstance(e, httpx.HTTPStatusError):
            return classify_exception(e)

    # 4) Fallback
    return AppError(
        TerminalError.UNEXPECTED_ERROR,
        ErrorKind.TERMINAL,
        grpc.StatusCode.UNAVAILABLE,
        ErrorMessages.UNEXPECTED_ERROR,
        str(e),
    )
