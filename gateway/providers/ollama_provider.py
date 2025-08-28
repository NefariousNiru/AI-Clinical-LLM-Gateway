# gateway/providers/ollama_provider.py
import json
from typing import List
from ollama import AsyncClient
from gateway.config.settings import settings
from gateway.grader.v1 import grader_pb2
from gateway.interface.provider_interface import Provider
from gateway.util import functions


class OllamaProvider(Provider):
    def __init__(self):
        self.host = settings.ollama_host
        self.client = AsyncClient(host=self.host)

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
    ) -> list[grader_pb2.ProblemFeedback]:
        rubric_dict, problems_dict = functions.serialize(rubric, problems)
        prompt = functions.create_prompt(user_prompt_template, rubric_dict, problems_dict)

        # Call Ollama
        resp = await self.client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            format="json",
            options={
                "temperature" : settings.model_temperature,
            }
        )

        # Extract the assistant message text
        content = resp["message"]["content"]
        print(content)

        # Some models occasionally wrap JSON in code fences. Strip common wrappers.
        content_stripped = content.strip()
        if content_stripped.startswith("```"):
            # remove first fence and last fence if present
            content_stripped = content_stripped.strip("` \n")
            # handle possible "json" language hint at the start
            if content_stripped.lower().startswith("json"):
                content_stripped = content_stripped[4:].lstrip()

        # Parse and map to proto
        parsed = json.loads(content_stripped)
        feedback_list = parsed["feedback"]

        out: List[grader_pb2.ProblemFeedback] = []
        for fb in feedback_list:
            out.append(
                grader_pb2.ProblemFeedback(
                    is_priority=fb.get("is_priority", False),
                    identification=grader_pb2.FeedbackSection(**fb.get("identification", {})),
                    explanation=grader_pb2.FeedbackSection(**fb.get("explanation", {})),
                    plan_recommendation=grader_pb2.FeedbackSection(**fb.get("plan_recommendation", {})),
                    monitoring=grader_pb2.FeedbackSection(**fb.get("monitoring", {})),
                )
            )

        # Provider-side cardinality guard
        if len(out) != len(problems):
            raise ValueError(f"schema_mismatch: expected {len(problems)} feedback, got {len(out)}")

        return out