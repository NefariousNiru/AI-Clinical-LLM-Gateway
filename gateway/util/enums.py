"""
file: gateway/util/enums.py

Global enums
"""

from enum import Enum


class EmbeddingSectionType(str, Enum):
    """
    Attributes:
        IDENTIFICATION (str): Identification box
        EXPLANATION (str): Explanation box
        PLAN_RECOMMENDATION (str): Plan recommendation box
        MONITORING (str): Monitoring box
    """

    IDENTIFICATION = "identification"
    EXPLANATION = "explanation"
    PLAN_RECOMMENDATION = "plan_recommendation"
    MONITORING = "monitoring"
