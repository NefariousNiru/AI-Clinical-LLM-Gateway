"""
file: gateway/util/functions.py

Utility to store functions
"""

import grpc
import re
from typing import Optional


async def abort_with_error(
    context: grpc.aio.ServicerContext,
    status: grpc.StatusCode,
    code: str,
    details: str,
) -> None:
    """
    Abort the RPC with a status and machine-readable error metadata.

    Args:
        context: Active gRPC async servicer context.
        status: gRPC status code to return.
        code: Machine-readable error code string.
        details: Human-readable error message.

    Raises:
        grpc.RpcError: Raised by `context.abort(...)`.
    """

    # 1) Attach trailing metadata for downstream error classification.
    context.set_trailing_metadata((("x-error-code", code),))

    # 2) Abort the RPC.
    await context.abort(status, details)


def parse_duration_to_seconds(
    value: str,
) -> Optional[float]:
    """
    Parse a duration header value into seconds.

    Args:
        value: Header string value.

    Returns:
        Duration in seconds if parseable, else None.
    """

    # 1) Normalize input.
    normalized = value.strip().lower()

    # 2) Handle plain numeric seconds.
    try:
        return float(normalized)
    except ValueError:
        pass

    # 3) Handle number + unit format.
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(ms|s|m)", normalized)
    if not match:
        return None

    amount = float(match.group(1))
    unit = match.group(2)

    # 4) Convert to seconds.
    if unit == "ms":
        return amount / 1000.0
    if unit == "s":
        return amount
    if unit == "m":
        return amount * 60.0

    return None
