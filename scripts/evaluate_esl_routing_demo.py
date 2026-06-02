#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.esl_writing_feedback import evaluate_routing_against_expected, route_feedback_dataframe


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    feedback = pd.read_csv(ROOT / "data" / "esl_writing_demo" / "feedback_items.csv")
    evidence = pd.read_csv(ROOT / "data" / "esl_writing_demo" / "review_evidence.csv")
    expected = pd.read_csv(ROOT / "data" / "esl_writing_demo" / "expected_routing_labels.csv")
    routing = route_feedback_dataframe(feedback, evidence)
    metrics = evaluate_routing_against_expected(routing, expected)
    out_dir = ROOT / "reports" / "esl_writing_feedback_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    routing.merge(expected, on="feedback_item_id", how="left").to_csv(out_dir / "synthetic_routing_eval.csv", index=False)
    with (out_dir / "synthetic_routing_eval_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, ensure_ascii=False)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

