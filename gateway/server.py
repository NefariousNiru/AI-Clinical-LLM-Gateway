# gateway/server.py
import asyncio
import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
import grpc
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2_grpc
from gateway.service import grader_service
import signal
import os


def init_logger() -> Logger:
    os.makedirs("logs", exist_ok=True)
    log_level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    log_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    logger = logging.getLogger("grader.service")
    return logger


async def serve() -> None:
    """Start the async gRPC server and block until termination."""
    logger = init_logger()

    server = grpc.aio.server()  # cross-platform grpc aio server
    grader_pb2_grpc.add_GraderServicer_to_server(
        grader_service.GraderService(), server
    )  # add the grading service method to grpc

    bind_addr = f"{settings.host}:{settings.port}"  # Bind ports
    server.add_insecure_port(bind_addr)

    logger.info("[LLM Gateway] listening on %s (TLS disabled)", bind_addr)
    await server.start()

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
