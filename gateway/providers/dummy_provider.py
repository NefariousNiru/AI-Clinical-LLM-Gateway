"""
file: gateway/providers/dummy_provider.py

Schema-synced dummy provider for tests and local development.

Purpose:
- Return a deterministic, schema-valid ChatServiceResponse without calling any LLM.
- Enables exercising service paths, gRPC wiring, and UI flows offline.

Maintenance:
- The returned payload mirrors the current FeedbackEnvelope/ProblemFeedback schema.
- If pydantic models change, update this file to keep test coverage meaningful.
"""

import asyncio
import json
from typing import Any
from gateway.config.pydantic_models import (
    ChatServiceResponse,
    FeedbackEnvelope,
    FeedbackSection,
    ProblemFeedback,
)


class DummyProvider:
    """No-LLM provider used to test service behavior without network I/O."""

    _LOREM_SENTENCE = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi "
        "ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit "
        "in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
        "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia "
        "deserunt mollit anim id est laborum. "
    )

    @classmethod
    def _extract_student_submission(cls, user_prompt: str) -> dict[str, Any]:
        """
        Parse the first JSON object after `student_submission:` by taking
        everything from the first `{` to the last `}`.
        """

        prefix = "student_submission:"
        if prefix not in user_prompt:
            return {}

        payload_str = user_prompt.split(prefix, 1)[1].strip()

        start = payload_str.find("{")
        end = payload_str.rfind("}")

        if start == -1 or end == -1 or end < start:
            return {}

        json_str = payload_str[start : end + 1]

        try:
            parsed = json.loads(json_str)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @classmethod
    def _make_lorem_text(cls) -> str:
        """
        Create a long lorem ipsum block.

        Rough heuristic:
        - 1 token is often around 0.75 words in English prose
        - 1000 tokens is roughly 700-800 words
        """

        target_words = 400
        chunk_words = len(cls._LOREM_SENTENCE.split())
        repeat_count = max(1, target_words // chunk_words + 1)
        return (cls._LOREM_SENTENCE * repeat_count).strip()

    @classmethod
    async def get_dummy_response(cls, user_prompt: str) -> ChatServiceResponse:
        """
        Return a mock ChatServiceResponse for testing ChatService without a real provider.

        Behavior:
        - sleeps for 120 seconds to simulate slow LLM latency
        - extracts `name` and `isPriority` from student_submission JSON
        - returns large text in each feedback box
        """

        await asyncio.sleep(60)        # Simulate LLM latency

        submission = cls._extract_student_submission(user_prompt)
        if "name" not in submission:
            raise ValueError("Missing 'name' in submission")
        problem_name = submission["name"]
        is_priority = bool(submission.get("isPriority", False))

        long_evaluation = cls._make_lorem_text()
        long_feedback = cls._make_lorem_text()

        identification_section = FeedbackSection(
            score="1.0",
            evaluation=long_evaluation,
            feedback=long_feedback,
        )

        explanation_section = FeedbackSection(
            score="1.0",
            evaluation=long_evaluation,
            feedback=long_feedback,
        )

        plan_recommendation_section = FeedbackSection(
            score="1.0",
            evaluation=long_evaluation,
            feedback=long_feedback,
        )

        monitoring_section = FeedbackSection(
            score="1.0",
            evaluation=long_evaluation,
            feedback=long_feedback,
        )

        dummy_feedback = ProblemFeedback(
            name=problem_name,
            is_priority=is_priority,
            identification=identification_section,
            explanation=explanation_section,
            plan_recommendation=plan_recommendation_section,
            monitoring=monitoring_section,
        )

        dummy_envelope = FeedbackEnvelope(
            feedback=dummy_feedback,
            error=False,
            errors=[],
        )

        return ChatServiceResponse(
            envelope=dummy_envelope,
            input_tokens=1050,
            output_tokens=4000,
        )
