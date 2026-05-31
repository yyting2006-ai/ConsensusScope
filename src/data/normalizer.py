from __future__ import annotations

from typing import Dict

from src.schemas import QuestionSample


def sample_to_record(sample: QuestionSample) -> Dict:
    return sample.model_dump()
