from __future__ import annotations

"""Deprecated legacy adjudication script.

The EMNLP 2026 demo pipeline uses ``src.experiments.run_decisions`` for
majority vote, rule-based dynamic adjudication and the real fixed-judge
baseline. This script is kept only for the original skeleton workflow defined
in ``config.yaml``.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adjudication.dynamic_judge import dynamic_judge
from src.adjudication.majority_vote import majority_vote
from src.config import load_config, resolve_path
from src.data.dataset_loader import load_samples
from src.schemas import ModelAnswer
from src.storage.experiment_store import group_answers_by_sample
from src.storage.io import load_records_jsonl
from legacy.fixed_judge_placeholder import fixed_judge_placeholder


def main() -> None:
    config = load_config()
    exp = config["experiment"]
    samples = load_samples(resolve_path(exp["sample_file"]))
    answers = [ModelAnswer.model_validate(row) for row in load_records_jsonl(resolve_path(exp["output_file"]))]
    grouped = group_answers_by_sample(answers)

    rows = []
    for sample in samples:
        sample_answers = grouped.get(sample.id, [])
        for result in [
            majority_vote(sample, sample_answers),
            fixed_judge_placeholder(sample, sample_answers),
            dynamic_judge(sample, sample_answers),
        ]:
            rows.append(result.model_dump())

    output_path = resolve_path(exp["adjudication_file"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Wrote adjudication results to {output_path}")


if __name__ == "__main__":
    main()
