# gateway/service/ChatService.py
"""Concrete chat service using Instructor for strict schema parsing.

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
        Return feedback for input.

        :param system_prompt: System message instructing model behavior.
        :param user_prompt: User Prompt message.
        :param model_name: Provider-specific model identifier.
        :param trace_id: Correlation id for observability.
        :param job_id: Backend job identifier for traceability.

        :raises AppError
        :return: ChatServiceResponse.
        """
        logger.debug(
            "ChatService.grade start provider=%s model=%s trace_id=%s job_id=%s",
            type(self.raw_client).__name__,
            model_name,
            trace_id,
            job_id,
        )

        # 0) If Dummy Provider
        if isinstance(self.raw_client, DummyProvider):
            return self.raw_client.get_dummy_response()

        try:
            # 1) Chat with LLM
            response: ChatServiceResponse = await self._get_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model_name=model_name,
            )

            # 2) Check if LLM Generated an Error - Treat as transient
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

            return response

        except AppError:
            raise
        except ValidationError as ve:
            raise classify_exception(ve)
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
            - We pass through INSTRUCTOR_MAX_RETRY for Instructor's internal retry.
            - Temperature is omitted for GPT-5* models
            - Anthropic requires passing max_tokens
        """
        # 1) Create kwargs for chat
        assert isinstance(self.client, AsyncInstructor)

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

        # 2) Add model specific kwargs
        if "gpt-5" not in model_name.lower():
            # GPT-5 Models do not support temperature
            kwargs["temperature"] = settings.model_temperature

        if isinstance(self.raw_client, AsyncAnthropic):
            # Anthropic Requires max_tokens
            kwargs["max_tokens"] = settings.anthropic_max_tokens

        # 3) Call chat, get (pydantic model, raw message)
        envelope, completion = await self.client.chat.completions.create_with_completion(**kwargs)

        # 4) Normalize token fields across providers
        usage = getattr(completion, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", getattr(usage, "input_tokens", None))
        output_tokens = getattr(usage, "completion_tokens", getattr(usage, "output_tokens", None))

        # 5) Return ChatServiceResponse
        return ChatServiceResponse(
            envelope=envelope, input_tokens=input_tokens, output_tokens=output_tokens
        )
