# gateway/util/functions.py
import json


def create_prompt(
    user_prompt_template: str, rubrics: list[dict], payload: list[dict]
) -> str:
    return user_prompt_template.format(
        rubrics_json=json.dumps(rubrics, ensure_ascii=False, indent=2),
        payload_json=json.dumps(payload, ensure_ascii=False, indent=2),
    )
