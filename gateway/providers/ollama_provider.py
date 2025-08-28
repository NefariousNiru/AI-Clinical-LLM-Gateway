# gateway/providers/ollama_provider.py
from typing import List
from gateway.grader.v1 import grader_pb2
from gateway.interface.provider_interface import Provider


class OllamaProvider(Provider):
    def __init__(self):
        pass

    def grade(
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
        pass
