"""
file: server.py

Async gRPC server bootstrap for the LLM Gateway.

- build_server: assemble the grpc.aio server (interceptors, services, bind/listen).
- serve: run the server with graceful shutdown on SIGINT/SIGTERM.

Notes:
- Enforces shared-token auth via AuthTokenInterceptor.
- Supports TLS when enabled; requires cert/key and shared token in TLS mode.
"""

import asyncio
import signal
import grpc
from logging import Logger
from typing import Optional
from grpc import Server
import gateway.util.logger as lg
from gateway.auth_token_interceptor import AuthTokenInterceptor
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2_grpc
from gateway.service import grader_service


def _bind_port(server: Server, logger: Logger):
    """
    Bind the gRPC server to host:port with optional TLS.

    Args:
        server (grpc.Server): server instance to bind.
        logger (Logger): configured logger.

    Raises:
        SystemExit: when TLS is enabled but certs are missing or unreadable,
                    or when shared token is missing under TLS.
    """

    bind_addr = f"{settings.host}:{settings.port}"
    if settings.tls_enabled:
        # 1) Validate TLS configuration
        if not settings.tls_cert_path or not settings.tls_key_path:
            logger.error("TLS enabled but GATEWAY_TLS_CERT_PATH or GATEWAY_TLS_KEY_PATH missing")
            raise SystemExit(1)

        # 2) Read key/cert material
        try:
            with open(settings.tls_key_path, "rb") as f:
                private_key = f.read()
            with open(settings.tls_cert_path, "rb") as f:
                cert_chain = f.read()
        except Exception as e:
            logger.exception("Failed to read TLS cert/key: %s", e)
            raise SystemExit(1)

        # 3) Configure TLS port
        server_creds = grpc.ssl_server_credentials(((private_key, cert_chain),))
        server.add_secure_port(bind_addr, server_creds)
        logger.info("[LLM Gateway] listening on %s (TLS enabled)", bind_addr)

        # 4) Enforce shared token in TLS mode
        if not settings.shared_token:
            logger.error("GATEWAY_SHARED_TOKEN is required when TLS is enabled")
            raise SystemExit(1)
    else:
        # 5) Plaintext port
        server.add_insecure_port(bind_addr)
        logger.info("[LLM Gateway] listening on %s (TLS disabled)", bind_addr)


def build_server(logger: Optional[Logger] = None) -> grpc.aio.Server:
    """
    Compose and return an async gRPC server instance.

    Responsibilities:
        - Initialize interceptors (auth token).
        - Register services.
        - Bind network ports (TLS or insecure).

    Args:
        logger (Optional[Logger]): preconfigured logger; if None, one is created.

    Returns:
        grpc.aio.Server: fully wired server, ready to start.
    """

    # 1) Logger
    _logger = logger or lg.init_logger()

    # 2) Interceptors (auth header enforced for all RPCs)
    interceptors = [AuthTokenInterceptor(settings.shared_token)]

    # 3) Server
    server = grpc.aio.server(interceptors=interceptors)

    # 4) Services
    grader_pb2_grpc.add_GraderServicer_to_server(grader_service.GraderService(), server)

    # 5) Networking
    _bind_port(server=server, logger=_logger)

    return server


async def serve() -> None:
    """Start the async gRPC server and block until termination."""

    logger = lg.init_logger()

    # 1) Build server composition in one place (testable)
    server = build_server(logger=logger)

    # 2) Start serving
    await server.start()

    # 3) Graceful Shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        logger.info("Shutdown requested, stopping gRPC server...")
    finally:
        # 4) Allow in-flight RPCs to finish
        await server.stop(grace=5.0)


if __name__ == "__main__":
    asyncio.run(serve())
