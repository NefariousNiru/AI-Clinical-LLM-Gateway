# gateway/service/grader_service.py
import grpc
from gateway.config.provider_factory import get_provider
from gateway.grader.v1 import grader_pb2_grpc, grader_pb2
from gateway.interface.provider_interface import Provider

ERROR_METADATA_KEY = "x-error-code"

# Error codes are surfaced to workers via trailing metadata.
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


def abort_with_error(
    context: grpc.aio.ServicerContext,
    status: grpc.StatusCode,
    code: str,
    details: str,
) -> None:
    """
    Abort the RPC and attach a machine-readable error code for downstream
    classification (transient vs terminal).
    """
    context.set_trailing_metadata(((ERROR_METADATA_KEY, code),))
    context.abort(status, details)


class GraderService(grader_pb2_grpc.GraderServicer):
    async def Grade(
        self,
        request: grader_pb2.GradeRequest,
        context: grpc.aio.ServicerContext,
    ) -> grader_pb2.GradeResponse:
        """
        Validate request, delegate to provider, and return feedback.
        """
        # Basic validation
        if not request.HasField("rubric"):
            abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid_rubric",
                "rubric is required",
            )

        if len(request.rubric.sections) == 0:
            abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid_rubric",
                "rubric.sections cannot be empty",
            )

        if len(request.problems) == 0:
            abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                "invalid_payload",
                "problems cannot be empty",
            )

        # Resolve provider (throws if unsupported)
        print("Model Requested: ", request.model_provider, request.model_name)
        provider: Provider = get_provider(request.model_provider)

        # Delegate grading
        feedback_items: list[grader_pb2.ProblemFeedback] = await provider.grade(
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
            model_provider=request.model_provider,
            model_name=request.model_name or "dummy-model",
        )
