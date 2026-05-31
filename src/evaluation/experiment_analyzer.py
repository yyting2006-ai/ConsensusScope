from __future__ import annotations

from typing import Dict, List

from src.evaluation.metrics import answer_consistency_rate, evidence_support_score, model_accuracy
from src.schemas import ModelAnswer, QuestionSample


def summarize_sample(sample: QuestionSample, answers: List[ModelAnswer]) -> Dict:
    return {
        "sample_id": sample.id,
        "dataset": sample.dataset,
        "model_accuracy": model_accuracy(sample, answers),
        "answer_consistency_rate": answer_consistency_rate(sample, answers),
        "evidence_support_score": evidence_support_score(answers),
        "valid_outputs": sum(1 for a in answers if a.parse_ok),
    }
