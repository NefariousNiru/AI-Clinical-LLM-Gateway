# gateway/util/functions.py
import json
from gateway.grader.v1.grader_pb2 import RubricPayload, DrugRelatedProblem


def serialize(rubric: RubricPayload, problems: list[DrugRelatedProblem]):
    rubric_dict = {
        "rubric_id": rubric.rubric_id,
        "guideline_hint": rubric.guideline_hint,
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "max_points": s.max_points,
                "evaluation_question": s.evaluation_question,
                "criteria": [
                    {
                        "key": c.key,
                        "type": c.type,
                        "verbiage": c.verbiage,
                        "weight": c.weight if c.HasField("weight") else None,
                    }
                    for c in s.criteria
                ],
            }
            for s in rubric.sections
        ],
    }
    problems_dict = [
        {
            "is_priority": p.is_priority,
            "identification": p.identification,
            "explanation": p.explanation,
            "plan_recommendation": p.plan_recommendation,
            "monitoring": p.monitoring,
        }
        for p in problems
    ]
    return rubric_dict, problems_dict


def create_prompt(user_prompt_template: str, rubric_dict: dict, problems_dict):
    return user_prompt_template.format(
        rubric_json=json.dumps(rubric_dict, ensure_ascii=False, indent=2),
        problems_json=json.dumps(problems_dict, ensure_ascii=False, indent=2),
    )
