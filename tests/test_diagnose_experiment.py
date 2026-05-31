from __future__ import annotations

import pandas as pd

from scripts.diagnose_experiment import (
    expansion_recommendation,
    majority_dynamic_gap,
    model_output_summary,
    risk_distribution,
)


def test_diagnosis_helpers() -> None:
    outputs = pd.DataFrame(
        [
            {"model": "deepseek", "confidence": 0.8, "parse_error": ""},
            {"model": "deepseek", "confidence": 0.4, "parse_error": "bad json"},
            {"model": "qwen", "confidence": 0.6, "parse_error": ""},
        ]
    )
    summary = model_output_summary(outputs)
    deepseek = summary[summary["model"] == "deepseek"].iloc[0]
    assert deepseek["success_count"] == 1
    assert deepseek["json_parse_failed_count"] == 1

    metrics = pd.DataFrame(
        [
            {"method": "majority_vote", "accuracy": 0.6},
            {"method": "dynamic_decision", "accuracy": 0.8},
        ]
    )
    gap = majority_dynamic_gap(metrics)
    assert round(gap["gap"], 4) == 0.2

    risks = pd.DataFrame(
        [
            {"risk_labels": "false_consensus;confidence_mismatch"},
            {"risk_labels": "true_consensus"},
        ]
    )
    dist = risk_distribution(risks)
    assert set(dist["risk_type"]) == {"false_consensus", "confidence_mismatch", "true_consensus"}


def test_expansion_recommendation_positive() -> None:
    samples = pd.DataFrame([{"id": f"s{i}"} for i in range(30)])
    outputs = pd.DataFrame(
        [{"model": "m", "parse_error": ""} for _ in range(120)]
    )
    model_summary = model_output_summary(outputs)
    metrics = pd.DataFrame(
        [
            {"method": "majority_vote", "accuracy": 0.7},
            {"method": "dynamic_decision", "accuracy": 0.75},
        ]
    )
    risk_dist = pd.DataFrame([{"risk_type": "true_consensus", "count": 20}])
    ok, reasons = expansion_recommendation(samples, outputs, model_summary, metrics, risk_dist)
    assert ok is True
    assert any("可以扩大" in reason for reason in reasons)
