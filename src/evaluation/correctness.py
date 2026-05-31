from __future__ import annotations

from src.parsing.answer_normalizer import normalize_answer
from src.schemas import QuestionSample
from src.utils import normalize_text


def is_correct(sample: QuestionSample, answer: str) -> bool:
    predicted = normalize_answer(answer, sample)
    gold = normalize_answer(sample.gold_answer, sample)
    if sample.answer_type in {"choice", "boolean"}:
        return predicted == gold
    return gold in predicted or predicted in gold
