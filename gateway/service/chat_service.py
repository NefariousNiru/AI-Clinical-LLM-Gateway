"""
file: gateway/service/chat_service.py

Concrete chat service using Instructor for strict schema parsing.

Responsibilities:
- Call the model through Instructor with JSON → Pydantic enforcement.
- Convert provider/instructor failures into AppError using classify_exception.
- Avoid logging sensitive prompt/response contents at INFO level.
"""

import logging
import grpc
import instructor
from anthropic import AsyncAnthropic
from instructor import AsyncInstructor
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import ValidationError
from gateway.config.pydantic_models import (
    ChatServiceResponse,
    FeedbackEnvelope,
)
from gateway.config.settings import settings
from gateway.providers.dummy_provider import DummyProvider
from gateway.providers.provider_registry import Provider
from gateway.util.error_mapping import classify_exception
from gateway.util.errors import AppError, ErrorKind, ErrorMessages, TransientError

logger = logging.getLogger(__name__)


class ChatService:
    """Schema-enforcing chat service with transparent retries and analytics tracing."""

    def __init__(self, raw_client: Provider):
        self.raw_client = raw_client
        if isinstance(raw_client, AsyncOpenAI):
            self.client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)
        elif isinstance(raw_client, AsyncAnthropic):
            self.client = instructor.from_anthropic(raw_client, mode=instructor.Mode.ANTHROPIC_JSON)
        elif isinstance(raw_client, DummyProvider):
            self.client = raw_client

    async def grade(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        trace_id: str,
        job_id: str,
    ) -> ChatServiceResponse:
        """
        Return structured feedback for input prompts.

        Args:
            system_prompt (str): System message instructing model behavior.
            user_prompt (str): User prompt message.
            model_name (str): Provider-specific model identifier.
            trace_id (str): Correlation id for observability.
            job_id (str): Backend job identifier for traceability.

        Returns:
            ChatServiceResponse: typed envelope with token usage.

        Raises:
            AppError: provider/SDK errors mapped to application domain.
            ValidationError: when model output fails schema validation.
        """

        # 1) Trace (debug only: avoid prompt content in logs)
        logger.debug(
            "ChatService.grade start provider=%s model=%s trace_id=%s job_id=%s",
            type(self.raw_client).__name__,
            model_name,
            trace_id,
            job_id,
        )

        # 2) Short-circuit for the Dummy provider (no network I/O)
        if isinstance(self.raw_client, DummyProvider):
            return self.raw_client.get_dummy_response()

        try:
            # 3) Call provider via Instructor to get a typed response
            response: ChatServiceResponse = await self._get_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_name=model_name,
            )

            # 4) Treat an envelope-marked error as transient (retryable upstream)
            if response.envelope.error:
                reason = (
                    "; ".join(response.envelope.errors)
                    if response.envelope.errors
                    else "unspecified error"
                )
                raise AppError(
                    code=TransientError.LLM_SIGNALED_ERROR,
                    kind=ErrorKind.TRANSIENT,
                    grpc_status=grpc.StatusCode.UNAVAILABLE,
                    details=ErrorMessages.LLM_SIGNALED_ERROR,
                    cause=reason,
                )

            # 5) Success path
            return response

        # 6) Preserve already-classified AppErrors
        except AppError:
            raise

        # 7) Convert Pydantic validation into domain error
        except ValidationError as ve:
            raise classify_exception(ve)

        # 8) Catch-all mapping for provider/SDK/runtime errors
        except Exception as e:
            raise classify_exception(e)

    async def _get_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
    ) -> ChatServiceResponse:
        """Call the chat model with Instructor enforcing FeedbackEnvelope.

        Notes:
            - Behaviour
                - Uses Instructor to coerce the model output into `FeedbackEnvelope` (strict=True).
                - Retries are governed by INSTRUCTOR_MAX_RETRY (from settings).
                - Temperature is skipped for GPT-5* models, per provider constraints.
                - Anthropic requires `max_tokens` and is passed via settings.

            - Token Normalization:
                - Different SDKs expose usage fields differently. We normalize as:
                  input_tokens  := usage.prompt_tokens OR usage.input_tokens
                  output_tokens := usage.completion_tokens OR usage.output_tokens
                - If a provider omits usage entirely, these may be None.

        Returns:
            ChatServiceResponse with the parsed envelope and normalized token counts.

        Raises:
            AppError via classify_exception for provider/SDK issues.
            ValidationError when the model output fails schema validation.
        """

        # 1) Ensure the client is Instructor-wrapped (except dummy path handled earlier)
        assert isinstance(self.client, AsyncInstructor)

        # 2) Base kwargs for chat.completions.create_with_completion
        kwargs = dict(
            response_model=FeedbackEnvelope,
            model=model_name,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=user_prompt),
            ],
            max_retries=settings.instructor_max_retry,
            strict=True,
        )

        # 3) Add model specific kwargs
        if "gpt-5" not in model_name.lower():
            # GPT-5 Models do not support temperature
            kwargs["temperature"] = settings.model_temperature

        if isinstance(self.raw_client, AsyncAnthropic):
            # Anthropic Requires max_tokens
            kwargs["max_tokens"] = settings.anthropic_max_tokens

        # 4) Invoke and receive (pydantic model, raw completion)
        envelope, completion = await self.client.chat.completions.create_with_completion(**kwargs)

        # 5) Normalize token accounting across providers
        usage = getattr(completion, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", None))
        output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", None))

        # 6) Package typed response
        return ChatServiceResponse(
            envelope=envelope, input_tokens=input_tokens, output_tokens=output_tokens
        )
