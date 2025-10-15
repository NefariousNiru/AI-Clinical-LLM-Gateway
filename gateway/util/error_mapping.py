import asyncio
import socket
import grpc
import re
from typing import Optional

# httpx is used under the hood by both SDKs; import defensively
try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

from pydantic import ValidationError
from gateway.util.errors import AppError, ErrorKind, ErrorMessages
from gateway.util.errors import TerminalError, TransientError

# -------- Provider SDK imports (tolerate absence) --------
try:
    from openai import (
        APIError as OpenAIApiError,
        AuthenticationError as OpenAIAuthError,
        BadRequestError as OpenAIBadRequestError,
        APITimeoutError as OpenAITimeoutError,
        NotFoundError as OpenAINotFoundError,
        RateLimitError as OpenAIRateLimitError,
    )
except Exception:  # pragma: no cover
    OpenAIApiError = OpenAIAuthError = OpenAIBadRequestError = OpenAITimeoutError = (
        OpenAINotFoundError
    ) = OpenAIRateLimitError = None

try:
    from anthropic import (
        APIError as AnthropicApiError,
        AuthenticationError as AnthropicAuthError,
        BadRequestError as AnthropicBadRequestError,
        NotFoundError as AnthropicNotFoundError,
        RateLimitError as AnthropicRateLimitError,
        APITimeoutError as AnthropicAPITimeoutError,
    )
except Exception:  # pragma: no cover
    AnthropicApiError = AnthropicAuthError = AnthropicBadRequestError = (
        AnthropicNotFoundError
    ) = AnthropicRateLimitError = AnthropicAPITimeoutError = None

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


def _status_code_of(e: Exception) -> Optional[int]:
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
def _rate_limited(cause: Optional[str]) -> AppError:
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
            TerminalError.AUTH_FAILED,
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
