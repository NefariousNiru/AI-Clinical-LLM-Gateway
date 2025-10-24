# tests/test_pydantic_constraints.py
import pytest
from pydantic import ValidationError
from gateway.config.pydantic_models import FeedbackSection


@pytest.mark.parametrize("field", ["score", "evaluation", "feedback"])
def test_feedback_section_non_empty_string(field):
    # Build kwargs with one field empty
    data = {"score": "1", "evaluation": "ok", "feedback": "ok"}
    data[field] = ""
    with pytest.raises(ValidationError):
        FeedbackSection(**data)
