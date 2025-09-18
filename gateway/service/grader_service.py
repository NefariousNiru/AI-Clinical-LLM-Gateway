# gateway/service/grader_service.py
import time
from typing import List
import grpc
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from gateway.config.pydantic_models import ProblemFeedback
from gateway.grader.v1 import grader_pb2_grpc, grader_pb2
from gateway.providers.provider import Provider, get_provider
from google.protobuf import struct_pb2
from gateway.providers.dummy_provider import DummyProvider
from gateway.util.errors import TerminalError, TransientError
import logging

logger = logging.getLogger(__name__)
ERROR_METADATA_KEY = "x-error-code"


async def abort_with_error(
    context: grpc.aio.ServicerContext,
    status: grpc.StatusCode,
    code: str,
    details: str,
) -> None:
    """Abort the RPC with a status and attach a machine-readable error code.

    The `x-error-code` trailer enables downstream components to classify errors
    without string-parsing the gRPC details.
    """
    context.set_trailing_metadata(((ERROR_METADATA_KEY, code),))
    await context.abort(status, details)


def _json_value_to_py(v: struct_pb2.Value):
    """Convert a google.protobuf.Value into the corresponding Python object."""
    kind = v.WhichOneof("kind")
    if kind == "null_value":
        return None
    if kind == "number_value":
        return v.number_value
    if kind == "string_value":
        return v.string_value
    if kind == "bool_value":
        return v.bool_value
    if kind == "struct_value":
        return {k: _json_value_to_py(x) for k, x in v.struct_value.fields.items()}
    if kind == "list_value":
        return [_json_value_to_py(x) for x in v.list_value.values]
    return None


def _struct_to_dict(s: struct_pb2.Struct) -> dict:
    """Convert a google.protobuf.Struct to a python dict
    :rtype: dict
    :param: grpc struct
    """
    return {k: _json_value_to_py(v) for k, v in s.fields.items()}


class GraderService(grader_pb2_grpc.GraderServicer):
    """gRPC service that validates input, delegates to a model provider, and maps results."""

    async def Grade(
        self,
        request: grader_pb2.GradeRequest,
        context: grpc.aio.ServicerContext,
    ) -> grader_pb2.GradeResponse:
        """Validate request, call provider, and return structured feedback.

        Error semantics:
          - gRPC status code communicates class (INVALID_ARGUMENT, UNAVAILABLE, etc.).
          - Trailer metadata x-error-code is one of TransientError.* or TerminalError.*.
        """
        e2e_start = time.perf_counter()  # Start end-2-end timer

        if len(request.rubrics) == 0:
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.INVALID_RUBRIC,
                "rubrics cannot be empty",
            )
        if len(request.payload) == 0:
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.INVALID_PAYLOAD,
                "payload cannot be empty",
            )

        rubrics = [_struct_to_dict(s) for s in request.rubrics]
        payload = [_struct_to_dict(s) for s in request.payload]

        logger.info(
            "Grade request: provider=%s model=%s items(DRPs)=%d trace_id=%s job_id=%s",
            request.model_provider,
            request.model_name,
            len(payload),
            request.trace_id,
            request.job_id,
        )

        try:
            raw_client: AsyncOpenAI | DummyProvider | AsyncAnthropic = get_provider(
                request.model_provider
            )
        except ValueError as e:
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.UNSUPPORTED_MODEL,
                str(e),
            )
            raise

        provider = (
            Provider(raw_client=raw_client)
            if isinstance(raw_client, (AsyncOpenAI, AsyncAnthropic))
            else raw_client
        )

        # Delegate grading
        feedback_models: List[ProblemFeedback] = []
        try:
            model_start = time.perf_counter()  # start inference specific timer
            feedback_models = await provider.grade(
                rubrics=rubrics,
                payload=payload,
                system_prompt=request.system_prompt,
                user_prompt_template=request.user_prompt_template,
                model_name=request.model_name,
                trace_id=request.trace_id,
                job_id=request.job_id,
            )
            model_end = time.perf_counter()  # end inference specific timer
        except TimeoutError:
            await abort_with_error(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                TransientError.PROVIDER_TIMEOUT,
                "Provider timed out",
            )
        except PermissionError:
            await abort_with_error(
                context,
                grpc.StatusCode.UNAUTHENTICATED,
                TerminalError.AUTH_FAILED,
                "Auth failed",
            )
        except ValueError as e:
            # Provider may raise ValueError prefixed with known codes.
            msg = str(e)
            if msg.startswith(TerminalError.INVALID_PAYLOAD):
                code = TerminalError.INVALID_PAYLOAD
            elif msg.startswith(TerminalError.INVALID_RUBRIC):
                code = TerminalError.INVALID_RUBRIC
            else:
                code = TransientError.SCHEMA_MISMATCH
            logger.warning("Client error: %s (%s)", msg, code)
            await abort_with_error(context, grpc.StatusCode.INVALID_ARGUMENT, code, msg)
        except Exception as e:
            logger.exception("Unexpected provider failure")
            await abort_with_error(
                context,
                grpc.StatusCode.UNAVAILABLE,
                TransientError.NETWORK_ERROR,
                f"Transient error: {e}",
            )

        if len(feedback_models) != len(payload):
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TransientError.SCHEMA_MISMATCH,
                f"expected {len(payload)} feedback items, got {len(feedback_models)}",
            )

        logger.info(
            "Grade success: provider=%s model=%s items(DRPs)=%d trace_id=%s job_id=%s",
            request.model_provider,
            request.model_name,
            len(feedback_models),
            request.trace_id,
            request.job_id,
        )

        # Parse to stub
        feedback = self._parse_problem_feedback_to_stub(feedback_models)

        e2e_end = time.perf_counter()  # End e2e timer
        logger.info("Model took %f seconds", model_end - model_start)
        logger.info("Total grading request took %f seconds \n", e2e_end - e2e_start)

        return grader_pb2.GradeResponse(
            feedback=feedback,
            model_provider=request.model_provider,
            model_name=request.model_name or "dummy-model",
        )

    @staticmethod
    def _parse_problem_feedback_to_stub(
        feedback_models: List[ProblemFeedback],
    ) -> List[grader_pb2.ProblemFeedback]:
        """Convert pydantic ProblemFeedback models into protobuf DTOs."""
        feedback_items: List[grader_pb2.ProblemFeedback] = []
        for fb in feedback_models:
            feedback_items.append(
                grader_pb2.ProblemFeedback(
                    name=fb.name,
                    is_priority=fb.is_priority,
                    identification=grader_pb2.FeedbackSection(
                        score=fb.identification.score,
                        evaluation=fb.identification.evaluation,
                        feedback=fb.identification.feedback,
                    ),
                    explanation=grader_pb2.FeedbackSection(
                        score=fb.explanation.score,
                        evaluation=fb.explanation.evaluation,
                        feedback=fb.explanation.feedback,
                    ),
                    plan_recommendation=grader_pb2.FeedbackSection(
                        score=fb.plan_recommendation.score,
                        evaluation=fb.plan_recommendation.evaluation,
                        feedback=fb.plan_recommendation.feedback,
                    ),
                    monitoring=grader_pb2.FeedbackSection(
                        score=fb.monitoring.score,
                        evaluation=fb.monitoring.evaluation,
                        feedback=fb.monitoring.feedback,
                    ),
                )
            )
        return feedback_items
