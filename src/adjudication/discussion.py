from __future__ import annotations

from typing import List

from src.schemas import ModelAnswer


def answer_drift_rate(before: List[ModelAnswer], after: List[ModelAnswer]) -> float:
    if not before:
        return 0.0
    after_by_model = {(a.provider, a.model_name): a.answer for a in after}
    drift_count = 0
    compared = 0
    for item in before:
        key = (item.provider, item.model_name)
        if key in after_by_model:
            compared += 1
            drift_count += int(item.answer != after_by_model[key])
    return drift_count / compared if compared else 0.0
