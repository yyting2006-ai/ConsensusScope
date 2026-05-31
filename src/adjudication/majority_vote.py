from __future__ import annotations

from collections import Counter
from typing import List

from src.parsing.answer_normalizer import normalize_answer
from src.schemas import AdjudicationResult, ModelAnswer, QuestionSample


def majority_vote(sample: QuestionSample, answers: List[ModelAnswer]) -> AdjudicationResult:
    valid = [a for a in answers if a.parse_ok and a.answer]
    if not valid:
        return AdjudicationResult(sample_id=sample.id, strategy="majority_vote", final_answer="", recommendation="人工复核")

    normalized = [normalize_answer(a.answer, sample) for a in valid]
    final_answer, count = Counter(normalized).most_common(1)[0]
    confidence = count / len(valid)
    return AdjudicationResult(
        sample_id=sample.id,
        strategy="majority_vote",
        final_answer=final_answer,
        confidence=confidence,
        recommendation="采纳多数答案" if confidence >= 0.5 else "人工复核",
        details={"valid_models": len(valid), "majority_count": count},
    )
