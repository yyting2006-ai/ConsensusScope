from __future__ import annotations

from typing import List

from src.adjudication.majority_vote import majority_vote
from src.schemas import AdjudicationResult, ModelAnswer, QuestionSample


def fixed_judge_placeholder(sample: QuestionSample, answers: List[ModelAnswer]) -> AdjudicationResult:
    """Baseline fixed judge placeholder.

    The production version will call a selected judge model with judge_prompt.
    For the skeleton, this returns majority vote while marking the strategy.
    """

    result = majority_vote(sample, answers)
    result.strategy = "fixed_judge_placeholder"
    result.recommendation = "固定裁决器占位结果，后续接入 judge model"
    return result
