from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config, resolve_path
from src.data.dataset_loader import load_samples
from src.evaluation.experiment_analyzer import summarize_sample
from src.schemas import ModelAnswer
from src.storage.experiment_store import group_answers_by_sample
from src.storage.io import load_records_jsonl


def main() -> None:
    config = load_config()
    exp = config["experiment"]
    samples = load_samples(resolve_path(exp["sample_file"]))
    answers = [ModelAnswer.model_validate(row) for row in load_records_jsonl(resolve_path(exp["output_file"]))]
    grouped = group_answers_by_sample(answers)
    rows = [summarize_sample(sample, grouped.get(sample.id, [])) for sample in samples]

    output_path = resolve_path(exp["metrics_file"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Wrote metrics to {output_path}")


if __name__ == "__main__":
    main()
