#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.esl_writing_feedback import build_review_evidence, evaluate_routing_against_expected, route_feedback_dataframe


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "esl_writing_demo"
OUT_DIR = ROOT / "reports" / "esl_writing_feedback_analysis"


def _write_eval(name: str, routing: pd.DataFrame, expected: pd.DataFrame) -> dict:
    metrics = evaluate_routing_against_expected(routing, expected)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    routing.merge(expected, on="feedback_item_id", how="left").to_csv(OUT_DIR / f"{name}_routing_eval.csv", index=False)
    with (OUT_DIR / f"{name}_routing_eval_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2, ensure_ascii=False)
    return metrics


def main() -> None:
    feedback = pd.read_csv(DATA_DIR / "feedback_items.csv")
    evidence = pd.read_csv(DATA_DIR / "review_evidence.csv")
    expected = pd.read_csv(DATA_DIR / "expected_routing_labels.csv")
    routing = route_feedback_dataframe(feedback, evidence)
    synthetic_metrics = _write_eval("synthetic", routing, expected)

    stress = pd.read_csv(DATA_DIR / "ai_review_stress_cases.csv")
    stress_expected = stress[["feedback_item_id", "expected_risk_level", "expected_action", "expected_reason"]].copy()
    stress_feedback = stress.drop(columns=["expected_risk_level", "expected_action", "expected_reason"])
    stress_evidence = build_review_evidence(stress_feedback)
    stress_routing = route_feedback_dataframe(stress_feedback, stress_evidence)
    stress_metrics = _write_eval("stress", stress_routing, stress_expected)

    combined_routing = pd.concat([routing, stress_routing], ignore_index=True)
    combined_expected = pd.concat([expected, stress_expected], ignore_index=True)
    combined_metrics = _write_eval("combined", combined_routing, combined_expected)

    print(
        json.dumps(
            {
                "synthetic": synthetic_metrics,
                "stress": stress_metrics,
                "combined": combined_metrics,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
