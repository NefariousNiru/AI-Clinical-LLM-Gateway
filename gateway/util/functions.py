# gateway/util/functions.py
import json


def create_prompt(
    user_prompt_template: str, rubrics: list[dict], payload: list[dict]
) -> str:
    # The replacements have to be same as UserPromptBeingSent meaning the format argument
    return user_prompt_template.format(
        rubrics_json=json.dumps(rubrics, ensure_ascii=False, indent=2),
        problems_json=json.dumps(payload, ensure_ascii=False, indent=2),
        guidelines_json="",
    )
