"""
file: gateway/util/functions.py

Utility to store functions
"""

import grpc


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
