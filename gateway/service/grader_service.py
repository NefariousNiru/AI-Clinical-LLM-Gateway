"""
file: gateway/service/grader_service.py
Core grading service invoked by GRPC Grade method.

Responsibilities:
- Call the underlying ChatProvider (model provider)
- Delegate Grading to Provider
- Handle top level errors and return appropriate responses.
"""

import logging
import time
import grpc
from gateway.config.pydantic_models import ChatServiceResponse, ProblemFeedback, FeedbackSection
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2, grader_pb2_grpc
from gateway.providers.provider_registry import get_provider
from gateway.service.chat_service import ChatService
from gateway.util.errors import AppError, ErrorMessages, TerminalError, TransientError

logger = logging.getLogger(__name__)


async def abort_with_error(
    context: grpc.aio.ServicerContext,
    status: grpc.StatusCode,
    code: str,
    details: str,
) -> None:
    """
    Abort the RPC with a status and attach a machine-readable error code.

    Notes:
        The `x-error-code` trailer enables downstream components to classify errors
        without string-parsing the gRPC details.
    """

    context.set_trailing_metadata(((settings.error_metadata_key, code),))
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
        # 1) Required System Prompt
        if not request.system_prompt.strip():
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.INVALID_SYSTEM_PROMPT,
                ErrorMessages.INVALID_SYSTEM_PROMPT,
            )

        # 2) Required User Prompt
        if not request.user_prompt.strip():
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.INVALID_USER_PROMPT,
                ErrorMessages.INVALID_USER_PROMPT,
            )

    @staticmethod
    async def _get_chat_service(request, context) -> ChatService | None:
        """Return a chat service based on argument based request.model_provider"""

        try:
            return ChatService(raw_client=get_provider(request.model_provider))

        except ValueError as e:
            await abort_with_error(
                context,
                grpc.StatusCode.INVALID_ARGUMENT,
                TerminalError.UNSUPPORTED_PROVIDER,
                f"{ErrorMessages.UNSUPPORTED_PROVIDER}: {e!s}",
            )

    @staticmethod
    async def _perform_grading(
        chat_service: ChatService, request, context
    ) -> ProblemFeedback | None:
        """Helper to delegate, deal with errors and send back response for grading"""

        # 1) Log start
        logger.info(
            "Grade request: provider=%s model=%s trace_id=%s job_id=%s",
            request.model_provider,
            request.model_name,
            request.trace_id,
            request.job_id,
        )
        try:
            # 2) Start counter
            model_start = time.perf_counter()

            # 3) Delegate grading to ChatService
            response: ChatServiceResponse = await chat_service.grade(
                system_prompt=request.system_prompt,
                user_prompt=request.user_prompt,
                model_name=request.model_name,
                trace_id=request.trace_id,
                job_id=request.job_id,
            )

            # 4) Log Finish
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

            # 5) Return
            return response.envelope.feedback

        # 6) Exceptions
        except AppError as ae:
            logger.error(
                "Provider error code=%s kind=%s status=%s trace_id=%s job_id=%s details=%s",
                ae.code,
                ae.kind.value,
                ae.grpc_status.name,
                request.trace_id,
                request.job_id,
                ae.details,
            )
            await abort_with_error(context, ae.grpc_status, ae.code, ae.details)

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
                f"{ErrorMessages.NETWORK_ERROR}: {e}",
            )

    @staticmethod
    def _pydantic_to_proto_feedback_section(
        section: FeedbackSection,
    ) -> grader_pb2.FeedbackSection:
        """Adapters for pydantic to proto feedback sections."""

        return grader_pb2.FeedbackSection(
            score=section.score,
            evaluation=section.evaluation,
            feedback=section.feedback,
        )

    def _pydantic_to_proto_problem_feedback(
        self, feedback: ProblemFeedback
    ) -> grader_pb2.ProblemFeedback:
        """Adapters for pydantic to proto problem feedback."""

        return grader_pb2.ProblemFeedback(
            name=feedback.name,
            is_priority=feedback.is_priority,
            identification=self._pydantic_to_proto_feedback_section(feedback.identification),
            explanation=self._pydantic_to_proto_feedback_section(feedback.explanation),
            plan_recommendation=self._pydantic_to_proto_feedback_section(
                feedback.plan_recommendation
            ),
            monitoring=self._pydantic_to_proto_feedback_section(feedback.monitoring),
        )
