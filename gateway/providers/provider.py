# gateway/interface/provider.py
from typing import List, Any, Dict
import instructor
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import ValidationError
from gateway.config.pydantic_models import ProblemFeedback, FeedbackEnvelope
from gateway.config.settings import settings
from gateway.providers.dummy_provider import DummyProvider
from gateway.util import functions

def get_provider(provider: str) -> AsyncOpenAI | DummyProvider:
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

        # Build prompt from flexible JSON inputs
        prompt = functions.create_prompt(user_prompt_template, rubrics, payload)

        # Get Response
        try:
            envelope: FeedbackEnvelope = await self._get_response(model_name, system_prompt, prompt)
        except ValidationError as ve:
            raise ValueError(f"schema_mismatch: {ve}")  # handled upstream
        except Exception as e:
            # Network or other transient issue at the provider level
            # Let the service classify this as network_error
            raise e

        feedback_models = envelope.feedback

        # Cardinality check vs input payload
        if len(feedback_models) != len(payload):
            raise ValueError(
                f"schema_mismatch: expected {len(payload)} feedback, got {len(feedback_models)}"
            )

        return feedback_models

    async def _get_response(self, model_name: str, system_prompt: str, prompt: str):
        return await self.client.chat.completions.create(
            model=model_name,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=prompt),
            ],
            response_model=FeedbackEnvelope,
            temperature=settings.model_temperature,
            max_retries=settings.instructor_max_retry
        )