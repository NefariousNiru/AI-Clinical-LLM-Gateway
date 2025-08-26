# gateway/providers/interface.py
from typing import Protocol, List
from gateway.grader.v1 import grader_pb2


class Provider(Protocol):
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
    ) -> List[grader_pb2.ProblemFeedback]: ...
