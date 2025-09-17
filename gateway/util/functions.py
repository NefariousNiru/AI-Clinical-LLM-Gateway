# gateway/util/functions.py
"""Utility helpers for templating prompts passed to providers."""
import json


def create_prompt(
    user_prompt_template: str, rubrics: list[dict], payload: list[dict]
) -> str:
    """Materialize a prompt from a flexible JSON template.

    The template must contain named placeholders:
      - {rubrics_json}
      - {problems_json}
    """
    return user_prompt_template.format(
        rubrics_json=json.dumps(rubrics, ensure_ascii=False, indent=2),
        problems_json=json.dumps(payload, ensure_ascii=False, indent=2),
        # guidelines_json="", add later
    )
