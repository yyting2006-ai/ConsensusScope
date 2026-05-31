from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from src.utils import read_jsonl, write_jsonl


def save_models_jsonl(path: str | Path, records: Iterable[BaseModel]) -> None:
    write_jsonl(path, (record.model_dump() for record in records))


def load_records_jsonl(path: str | Path) -> list[dict]:
    return read_jsonl(path)
