from __future__ import annotations

import re

from src.schemas import QuestionSample
from src.utils import normalize_text


def normalize_answer(answer: str, sample: QuestionSample) -> str:
    text = normalize_text(answer)
    if sample.answer_type == "choice":
        match = re.match(r"^([a-e])\b", text)
        if match:
            return match.group(1).upper()
    if sample.answer_type == "boolean":
        if any(token in text for token in ["false", "no", "incorrect", "not true"]):
            return "false"
        if any(token in text for token in ["true", "yes", "correct"]):
            return "true"
    return text
