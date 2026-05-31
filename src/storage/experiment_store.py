from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from src.schemas import ModelAnswer


def group_answers_by_sample(answers: Iterable[ModelAnswer]) -> Dict[str, List[ModelAnswer]]:
    grouped: Dict[str, List[ModelAnswer]] = defaultdict(list)
    for answer in answers:
        grouped[answer.sample_id].append(answer)
    return dict(grouped)
