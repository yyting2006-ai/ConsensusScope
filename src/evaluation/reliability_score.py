from __future__ import annotations

from typing import List

from src.evaluation.correctness import is_correct
from src.evaluation.metrics import answer_consistency_rate, evidence_support_score
from src.schemas import ModelAnswer, QuestionSample


def compute_reliability_score(sample: QuestionSample, answers: List[ModelAnswer], final_answer: str) -> float:
    valid = [a for a in answers if a.parse_ok and a.answer]
    if not valid:
        return 0.0

    consistency = answer_consistency_rate(sample, valid)
    evidence = evidence_support_score(valid)
    confidence_values = [a.confidence for a in valid]
    avg_confidence = sum(confidence_values) / len(confidence_values)
    final_correct_proxy = 1.0 if is_correct(sample, final_answer) else 0.0
    calibration = 1.0 - abs(avg_confidence - final_correct_proxy)
    minority_penalty = 0.0 if consistency >= 0.75 else 0.5

    score = (
        0.35 * consistency
        + 0.25 * evidence
        + 0.15 * 1.0
        + 0.15 * calibration
        + 0.10 * (1.0 - minority_penalty)
    )
    return round(max(0.0, min(100.0, score * 100.0)), 1)
