# gateway/providers/dummy.py
from typing import List
from gateway.grader.v1 import grader_pb2


def _mk_section(head: str) -> grader_pb2.FeedbackSection:
    return grader_pb2.FeedbackSection(
        score="0",
        evaluation=f"auto-eval: {head[:32]}",
        feedback=f"auto-feedback: {head[:64]}",
    )


class DummyProvider:
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
        out: List[grader_pb2.ProblemFeedback] = []
        for p in problems:
            out.append(
                grader_pb2.ProblemFeedback(
                    is_priority=p.is_priority,
                    identification=_mk_section(p.identification),
                    explanation=_mk_section(p.explanation),
                    plan_recommendation=_mk_section(p.plan_recommendation),
                    monitoring=_mk_section(p.monitoring),
                )
            )
        return out
