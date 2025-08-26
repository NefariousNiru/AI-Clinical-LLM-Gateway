import asyncio
from typing import List
import grpc
from gateway.config import settings
from gateway.grader.v1 import grader_pb2, grader_pb2_grpc
from gateway.providers.dummy import DummyProvider

provider = DummyProvider()

# ---- helpers ---------------------------------------------------------------

TRANSIENT_CODES = {
    "network_error",
    "provider_timeout",
    "rate_limited",
    "schema_mismatch",
}
TERMINAL_CODES = {
    "invalid_rubric",
    "unsupported_model",
    "auth_failed",
    "invalid_payload",
}


def _abort_with_code(
    context: grpc.aio.ServicerContext, status: grpc.StatusCode, code: str, details: str
):
    # Attach your string error code for the worker to map -> TransientError/TerminalError
    context.set_trailing_metadata((("x-error-code", code),))
    context.abort(status, details)


def _make_feedback_for_problem(
    p: grader_pb2.DrugRelatedProblem,
) -> grader_pb2.ProblemFeedback:
    # Deterministic dummy content; keeps structure aligned with your Pydantic models
    def section(head: str) -> grader_pb2.FeedbackSection:
        return grader_pb2.FeedbackSection(
            score="0",  # string on purpose, to match your model
            evaluation=f"auto-eval: {head[:32]}",
            feedback=f"auto-feedback: {head[:64]}",
        )

    return grader_pb2.ProblemFeedback(
        is_priority=p.is_priority,
        identification=section(p.identification),
        explanation=section(p.explanation),
        plan_recommendation=section(p.plan_recommendation),
        monitoring=section(p.monitoring),
    )


# ---- service ---------------------------------------------------------------


class GraderService(grader_pb2_grpc.GraderServicer):
    async def Grade(
        self, request: grader_pb2.GradeRequest, context: grpc.aio.ServicerContext
    ) -> grader_pb2.GradeResponse:
        # Basic validation
        if not request.HasField("rubric"):
            _abort_with_code(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid_rubric",
                "rubric is required",
            )

        if len(request.rubric.sections) == 0:
            _abort_with_code(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid_rubric",
                "rubric.sections cannot be empty",
            )

        if len(request.problems) == 0:
            _abort_with_code(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid_payload",
                "problems cannot be empty",
            )

        # Produce one feedback per problem, preserving order
        feedback_items: List[grader_pb2.ProblemFeedback] = await provider.grade(
            rubric=request.rubric,
            problems=list(request.problems),
            system_prompt=request.system_prompt,
            user_prompt_template=request.user_prompt_template,
            model_name=request.model_name,
            trace_id=request.trace_id,
            job_id=request.job_id,
        )

        return grader_pb2.GradeResponse(
            feedback=feedback_items,
            model_name=request.model_name or "dummy-model",
        )


# ---- bootstrap -------------------------------------------------------------


async def serve() -> None:
    server = grpc.aio.server()  # works on Linux/macOS/Windows
    grader_pb2_grpc.add_GraderServicer_to_server(GraderService(), server)
    bind_addr = f"{settings.host}:{settings.port}"
    server.add_insecure_port(bind_addr)

    print(f"[gateway] listening on {bind_addr} (TLS disabled)")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
