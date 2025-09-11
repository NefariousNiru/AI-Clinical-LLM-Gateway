# gateway/providers/dummy_provider.py
from typing import List, Any, Dict
from gateway.config.pydantic_models import ProblemFeedback, FeedbackSection


class DummyProvider:
    """No-LLM provider that echoes basic structure back as ProblemFeedback."""

    @staticmethod
    def _mk_section(head: str | None) -> FeedbackSection:
        text = head or ""
        return FeedbackSection(
            score="0",
            evaluation=f"auto-eval: {text[:32]}",
            feedback=f"auto-feedback: {text[:64]}",
        )

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
        out: list[ProblemFeedback] = []

        for p in payload:
            out.append(
                ProblemFeedback(
                    name=str(p.get("name", "unknown_problem")),
                    is_priority=bool(p.get("is_priority", False)),
                    identification=self._mk_section(p.get("identification")),
                    explanation=self._mk_section(p.get("explanation")),
                    plan_recommendation=self._mk_section(p.get("plan_recommendation")),
                    monitoring=self._mk_section(p.get("monitoring")),
                )
            )

        # Cardinality guard for safety (parity with other providers)
        if len(out) != len(payload):
            raise ValueError(
                f"schema_mismatch: expected {len(payload)} feedback, got {len(out)}"
            )

        return out
