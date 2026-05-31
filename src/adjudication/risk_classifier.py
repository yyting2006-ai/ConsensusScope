from __future__ import annotations

from collections import Counter
from typing import List

from src.evaluation.correctness import is_correct
from src.parsing.answer_normalizer import normalize_answer
from src.schemas import ModelAnswer, QuestionSample


def classify_risk(sample: QuestionSample, answers: List[ModelAnswer], final_answer: str) -> str:
    valid = [a for a in answers if a.parse_ok and a.answer]
    if not valid:
        return "无有效输出"

    normalized = [normalize_answer(a.answer, sample) for a in valid]
    most_common_answer, count = Counter(normalized).most_common(1)[0]
    agreement = count / len(valid)
    correctness = [is_correct(sample, a.answer) for a in valid]
    correct_count = sum(correctness)
    final_correct = is_correct(sample, final_answer)
    avg_confidence = sum(a.confidence for a in valid) / len(valid)

    if agreement >= 0.75 and final_correct:
        return "真实共识"
    if agreement >= 0.75 and not final_correct:
        return "虚假共识"
    if 0 < correct_count <= len(valid) // 2:
        return "少数派正确" if final_correct else "少数派正确被压制"
    if agreement < 0.50:
        return "高分歧不确定"
    if avg_confidence >= 0.70 and not final_correct:
        return "置信错配"
    return "中等分歧"
