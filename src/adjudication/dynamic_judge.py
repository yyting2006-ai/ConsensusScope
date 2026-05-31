from __future__ import annotations

from typing import List

from src.adjudication.majority_vote import majority_vote
from src.adjudication.risk_classifier import classify_risk
from src.evaluation.reliability_score import compute_reliability_score
from src.schemas import AdjudicationResult, ModelAnswer, QuestionSample


def dynamic_judge(sample: QuestionSample, answers: List[ModelAnswer]) -> AdjudicationResult:
    majority = majority_vote(sample, answers)
    risk_type = classify_risk(sample, answers, majority.final_answer)
    score = compute_reliability_score(sample, answers, majority.final_answer)
    if score >= 76 and risk_type == "真实共识":
        recommendation = "直接采纳"
    elif score >= 55:
        recommendation = "谨慎采纳，并保留风险标记"
    else:
        recommendation = "建议人工复核"
    return AdjudicationResult(
        sample_id=sample.id,
        strategy="dynamic_judge",
        final_answer=majority.final_answer,
        confidence=majority.confidence,
        risk_type=risk_type,
        reliability_score=score,
        recommendation=recommendation,
        details=majority.details,
    )
