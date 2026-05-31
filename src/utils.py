from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Iterable, List

import numpy as np


def set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", "", text).strip()


def read_jsonl(path: str | Path) -> List[dict]:
    records: List[dict] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_jsonl(path: str | Path, records: Iterable[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
