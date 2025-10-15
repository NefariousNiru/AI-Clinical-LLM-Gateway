# gateway/service/grader_service.py
import time
from typing import Optional
import grpc
from gateway.config.pydantic_models import ProblemFeedback, ChatServiceResponse
from gateway.grader.v1 import grader_pb2_grpc, grader_pb2
from gateway.grader.v1.grader_pb2 import FeedbackSection
from gateway.providers.provider_registry import get_provider
from gateway.service.chat_service import ChatService
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


class GraderService(grader_pb2_grpc.GraderServicer):
    """gRPC service that validates input, delegates to a model provider, and maps results."""

    async def Grade(
        self,
        request: grader_pb2.GradeRequest,
        context: grpc.aio.ServicerContext,
    ) -> grader_pb2.GradeResponse:
        """Validate request, call provider, and return structured feedback."""

        # 1) Start end-2-end timer
        e2e_start = time.perf_counter()

        # 2) Validate Prompts
        await self._validate_prompts(request=request, context=context)

        # 3) Get chat_service
        chat_service = await self._get_chat_service(request=request, context=context)

        # 4) Grade with Provider
        response: ProblemFeedback = await self._perform_grading(
            chat_service=chat_service, request=request, context=context
        )

        # 5) Log Finish
        logger.info(
            "Grading request finished: trace_id=%s job_id=%s duration=%f seconds",
            request.trace_id,
            request.job_id,
            time.perf_counter() - e2e_start,
        )

        # 6) Return response
        return grader_pb2.GradeResponse(
            feedback=self._pydantic_to_proto_problem_feedback(response),
        )

    @staticmethod
    async def _validate_prompts(request, context):
        if not request.system_prompt.strip():
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.INVALID_RUBRIC,
                "System Prompt cannot be empty",
            )
        if not request.user_prompt.strip():
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.INVALID_PAYLOAD,
                "User Prompt cannot be empty",
            )

    @staticmethod
    async def _get_chat_service(request, context) -> ChatService:
        try:
            return ChatService(raw_client=get_provider(request.model_provider))

        except ValueError as e:
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.UNSUPPORTED_MODEL,
                str(e),
            )
            raise

    @staticmethod
    async def _perform_grading(
        chat_service: ChatService, request, context
    ) -> Optional[ProblemFeedback]:
        logger.info(
            "Grade request: provider=%s model=%s trace_id=%s job_id=%s",
            request.model_provider,
            request.model_name,
            request.trace_id,
            request.job_id,
        )
        try:
            model_start = time.perf_counter()
            response: ChatServiceResponse = await chat_service.grade(
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                model_name=request.model_name,
                trace_id=request.trace_id,
                job_id=request.job_id,
            )
            logger.info(
                "Grade success: provider=%s model=%s input_tokens=%s output_tokens=%s trace_id=%s job_id=%s. Model Took %.3f seconds",
                request.model_provider,
                request.model_name,
                response.input_tokens,
                response.output_tokens,
                request.trace_id,
                request.job_id,
                time.perf_counter() - model_start,
            )
            return response.envelope.feedback

        except TimeoutError:
            await abort_with_error(
                context,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                TransientError.PROVIDER_TIMEOUT,
                "LLM Provider timed out",
            )

        except PermissionError:
            await abort_with_error(
                context,
                grpc.StatusCode.UNAUTHENTICATED,
                TerminalError.AUTH_FAILED,
                "Auth failed - Possible API Key Failure",
            )

        except ValueError as e:
            msg = str(e)
            if msg.startswith(TerminalError.INVALID_PAYLOAD):
                code = TerminalError.INVALID_PAYLOAD
            elif msg.startswith(TerminalError.INVALID_RUBRIC):
                code = TerminalError.INVALID_RUBRIC
            else:
                code = TransientError.SCHEMA_MISMATCH
            logger.warning(
                "Client error: %s (%s) trace_id=%s job_id=%s",
                msg,
                code,
                request.trace_id,
                request.job_id,
            )
            await abort_with_error(context, grpc.StatusCode.INVALID_ARGUMENT, code, msg)

        except Exception as e:
            logger.exception(
                "Unexpected provider failure trace_id=%s job_id=%s",
                request.trace_id,
                request.job_id,
            )
            await abort_with_error(
                context,
                grpc.StatusCode.UNAVAILABLE,
                TransientError.NETWORK_ERROR,
                f"Transient error: {e}",
            )

    @staticmethod
    def _pydantic_to_proto_feedback_section(
        section: FeedbackSection,
    ) -> grader_pb2.FeedbackSection:
        return grader_pb2.FeedbackSection(
            score=section.score,
            evaluation=section.evaluation,
            feedback=section.feedback,
        )

    def _pydantic_to_proto_problem_feedback(
        self, feedback: ProblemFeedback
    ) -> grader_pb2.ProblemFeedback:
        return grader_pb2.ProblemFeedback(
            name=feedback.name,
            is_priority=feedback.is_priority,
            identification=self._pydantic_to_proto_feedback_section(
                feedback.identification
            ),
            explanation=self._pydantic_to_proto_feedback_section(feedback.explanation),
            plan_recommendation=self._pydantic_to_proto_feedback_section(
                feedback.plan_recommendation
            ),
            monitoring=self._pydantic_to_proto_feedback_section(feedback.monitoring),
        )
