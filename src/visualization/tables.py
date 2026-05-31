from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
from pydantic import BaseModel


def models_to_dataframe(records: Iterable[BaseModel]) -> pd.DataFrame:
    return pd.DataFrame([item.model_dump() for item in records])


def save_table(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif path.suffix in {".xlsx", ".xls"}:
        df.to_excel(path, index=False)
    else:
        df.to_markdown(path, index=False)
