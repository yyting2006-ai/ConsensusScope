from __future__ import annotations

"""Deprecated legacy prototype; not used in the EMNLP 2026 demo pipeline.

The current fixed-judge baseline is implemented by
``src.decision.baselines.fixed_judge_decision`` and writes
``data/results/fixed_judge_results.csv``. This module remains only so the old
``legacy/03_run_adjudication_placeholder.py`` skeleton can be inspected without breaking
historical examples.
"""

from typing import List

from src.adjudication.majority_vote import majority_vote
from src.schemas import AdjudicationResult, ModelAnswer, QuestionSample


def fixed_judge_placeholder(sample: QuestionSample, answers: List[ModelAnswer]) -> AdjudicationResult:
    """Deprecated placeholder that returns majority vote for legacy scripts."""

    result = majority_vote(sample, answers)
    result.strategy = "fixed_judge_placeholder"
    result.recommendation = "固定裁决器占位结果，后续接入 judge model"
    return result
