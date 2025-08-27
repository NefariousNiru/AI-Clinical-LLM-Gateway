# gateway/server.py
import asyncio
import logging
import grpc
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2_grpc
from gateway.service import grader_service


async def serve() -> None:
    """
    Start the async gRPC server and block until termination.
    """
    logging.basicConfig(
        level=getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logger = logging.getLogger("grader.service")

    server = grpc.aio.server()  # cross-platform
    grader_pb2_grpc.add_GraderServicer_to_server(grader_service.GraderService(), server)

    bind_addr = f"{settings.host}:{settings.port}"
    server.add_insecure_port(bind_addr)

    logger.info("[LLM Gateway] listening on %s (TLS disabled)", bind_addr)
    await server.start()

    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        logger.info("Shutdown requested, stopping gRPC server...")
        await server.stop(grace=None)  # graceful stop


if __name__ == "__main__":
    asyncio.run(serve())
