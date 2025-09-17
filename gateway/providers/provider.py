# gateway/interface/provider.py
"""Concrete OpenAI/Ollama provider using Instructor for strict schema parsing.

Responsibilities:
- Build the prompt from rubrics + payload via the user template.
- Call the model through Instructor with JSON→Pydantic enforcement.
- Surface validation failures as ValueError('schema_mismatch: ...').
- Avoid logging sensitive prompt/response contents at INFO level.
"""
import instructor
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import ValidationError
from gateway.config.pydantic_models import ProblemFeedback, FeedbackEnvelope
from gateway.config.settings import settings
from gateway.providers.dummy_provider import DummyProvider
from gateway.util import functions
from typing import List, Any, Dict
import logging

logger = logging.getLogger(__name__)


def get_provider(provider: str) -> AsyncOpenAI | DummyProvider:
    """Returns a Provider instance which can be used to call models.
    :rtype: AsyncOpenAI or DummyProvider
    :param provider: Provider name from ['openai', 'ollama', 'dummy']
    :raises ValueError: If provider name is invalid
    """
    provider_name = provider.lower()
    if provider_name == "dummy":
        return DummyProvider()
    elif provider_name == "openai":
        return AsyncOpenAI(api_key=settings.openai_api_key)
    elif provider_name == "ollama":
        return AsyncOpenAI(base_url=settings.ollama_host, api_key="ollama")
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")


class Provider:
    """Schema-enforcing provider with transparent retries and analytics tracing."""
    def __init__(self, raw_client: AsyncOpenAI):
        self.client = instructor.from_openai(raw_client, mode=instructor.Mode.JSON)

    async def grade(
        self,
        *,
        rubrics: List[Dict[str, Any]],
        payload: List[Dict[str, Any]],
        system_prompt: str,
        user_prompt_template: str,
        model_name: str,
        trace_id: str,
        job_id: str,
    ) -> List[ProblemFeedback]:
        """
        Return rubric-aligned feedback for each input problem.
        :param rubrics: List of rubric JSON dicts payload: List of problem JSON dicts.
        :param payload: the student answer payload
        :param system_prompt: System message instructing model behavior.
        :param user_prompt_template: Format string used to render rubrics/payload.
        :param model_name: Provider-specific model identifier.
        :param trace_id: Correlation id for observability.
        :param job_id: Backend job identifier for traceability.

        :raises ValueError('schema_mismatch: ...') on validation errors.
        :raises ValueError('llm_error: ...') if the envelope reports error=True.
        """

        # Build prompt from flexible JSON inputs
        prompt = functions.create_prompt(user_prompt_template, rubrics, payload)

        # Get Response
        try:
            envelope: FeedbackEnvelope = await self._get_response(
                model_name, system_prompt, prompt
            )
        except ValidationError as ve:
            logger.warning("Validation error from provider: %s", ve)
            raise ValueError(f"schema_mismatch: {ve}")  # handled upstream
        except Exception as e:
            # Network or other transient issue at the provider level
            # Let the service classify this as network_error
            logger.error("Provider request failed: %s", e)
            raise e

        if envelope.error:
            reason = (
                "; ".join(envelope.errors) if envelope.errors else "unspecified error"
            )
            raise ValueError(f"llm_error: {reason}")

        feedback_models = envelope.feedback

        # Cardinality check vs input payload
        if len(feedback_models) != len(payload):
            raise ValueError(
                f"schema_mismatch: expected {len(payload)} feedback, got {len(feedback_models)}"
            )

        logger.debug(
            "Received %d feedback items: %s",
            len(feedback_models),
            [fm.name for fm in feedback_models],
        )

        return feedback_models

    async def _get_response(
        self, model_name: str, system_prompt: str, prompt: str
    ) -> FeedbackEnvelope:
        """Call the chat model with Instructor enforcing FeedbackEnvelope.
        Notes:
            - We pass through INSTRUCTOR_MAX_RETRY for Instructor's internal retry.
            - Temperature is omitted for GPT-5* models (as requested).
        """
        logger.debug("Dispatching chat completion to model=%s", model_name)
        kwargs = dict(
            response_model=FeedbackEnvelope,
            model=model_name,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=prompt),
            ],
            max_retries=settings.instructor_max_retry,
            strict=True,
        )

        # Only add temperature if model supports it
        if "gpt-5" not in model_name.lower():
            kwargs["temperature"] = settings.model_temperature

        return await self.client.chat.completions.create(**kwargs)
