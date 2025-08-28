# gateway/providers/openai_provider.py
from typing import List, Union
import json
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2
from gateway.grader.v1.grader_pb2 import DrugRelatedProblem, RubricPayload
from gateway.interface.provider_interface import Provider
from gateway.util import functions


class OpenAIProvider(Provider):
    def __init__(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY must be set")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def grade(
        self,
        *,
        rubric: grader_pb2.RubricPayload,
        problems: List[grader_pb2.DrugRelatedProblem],
        system_prompt: str,
        user_prompt_template: str,
        model_name: str,
        trace_id: str,
        job_id: str,
    ) -> List[grader_pb2.ProblemFeedback]:
        # Serialize rubric + problems into JSON
        rubric_dict, problems_dict = functions.serialize(rubric, problems)

        # Create prompt
        prompt = functions.create_prompt(
            user_prompt_template, rubric_dict, problems_dict
        )
        print(system_prompt + prompt)

        # get response
        response = await self._get_response(model_name, system_prompt, prompt)
        return self._parse_response(response=response)

    async def _get_response(self, model_name: str, system_prompt: str, prompt: str):
        return await self.client.chat.completions.create(
            model=model_name,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=prompt),
            ],
            temperature=settings.model_temperature,
        )

    @staticmethod
    def _parse_response(response) -> List[grader_pb2.ProblemFeedback]:
        content = response.choices[0].message.content
        feedback_list = json.loads(content)["feedback"]
        out = []
        for fb in feedback_list:
            out.append(
                grader_pb2.ProblemFeedback(
                    is_priority=fb.get("is_priority", False),
                    identification=grader_pb2.FeedbackSection(
                        **fb.get("identification", {})
                    ),
                    explanation=grader_pb2.FeedbackSection(**fb.get("explanation", {})),
                    plan_recommendation=grader_pb2.FeedbackSection(
                        **fb.get("plan_recommendation", {})
                    ),
                    monitoring=grader_pb2.FeedbackSection(**fb.get("monitoring", {})),
                )
            )
        return out
