from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from src.schemas import QuestionSample
from src.utils import read_jsonl


def load_samples(path: str | Path) -> List[QuestionSample]:
    path = Path(path)
    if path.suffix == ".jsonl":
        return [QuestionSample.model_validate(row) for row in read_jsonl(path)]
    if path.suffix == ".csv":
        df = pd.read_csv(path)
        return [QuestionSample.model_validate(row) for row in df.to_dict(orient="records")]
    raise ValueError(f"Unsupported sample file format: {path.suffix}")
