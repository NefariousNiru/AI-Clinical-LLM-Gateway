# server.py
import asyncio
import signal
from logging import Logger

import grpc
from grpc import Server

import gateway.util.logger as lg
from gateway.auth_token_interceptor import AuthTokenInterceptor
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2_grpc
from gateway.service import grader_service


def bind_port(server: Server, logger: Logger):
    bind_addr = f"{settings.host}:{settings.port}"
    if settings.tls_enabled:
        if not settings.tls_cert_path or not settings.tls_key_path:
            logger.error("TLS enabled but GATEWAY_TLS_CERT_PATH or GATEWAY_TLS_KEY_PATH missing")
            raise SystemExit(1)
        try:
            with open(settings.tls_key_path, "rb") as f:
                private_key = f.read()
            with open(settings.tls_cert_path, "rb") as f:
                cert_chain = f.read()
        except Exception as e:
            logger.exception("Failed to read TLS cert/key: %s", e)
            raise SystemExit(1)

        server_creds = grpc.ssl_server_credentials(((private_key, cert_chain),))
        server.add_secure_port(bind_addr, server_creds)
        logger.info("[LLM Gateway] listening on %s (TLS enabled)", bind_addr)

        # Enforce shared token in TLS mode
        if not settings.shared_token:
            logger.error("GATEWAY_SHARED_TOKEN is required when TLS is enabled")
            raise SystemExit(1)
    else:
        server.add_insecure_port(bind_addr)
        logger.info("[LLM Gateway] listening on %s (TLS disabled)", bind_addr)


async def serve() -> None:
    """Start the async gRPC server and block until termination."""
    logger = lg.init_logger()

    # Init Auth + Cross-Platform aio Server
    interceptors = [AuthTokenInterceptor(settings.shared_token)]
    server = grpc.aio.server(interceptors=interceptors)

    # Add the grading service method to grpc
    grader_pb2_grpc.add_GraderServicer_to_server(grader_service.GraderService(), server)

    # Bind ports
    bind_port(server=server, logger=logger)

    # Start server
    await server.start()

    # Graceful Shutdown
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
        await server.stop(grace=5.0)


if __name__ == "__main__":
    asyncio.run(serve())
