from __future__ import annotations

import pandas as pd

from src.data.dataset_builder import COLUMNS as CLEAN_DATASET_COLUMNS
from src.decision.baselines import fixed_judge_decision, majority_vote
from src.decision.dynamic_decision import dynamic_decision
from src.evaluation.risk_labeler import label_risks


MODEL_OUTPUT_COLUMNS = [
    "sample_id",
    "dataset",
    "task_type",
    "model",
    "answer",
    "reason",
    "confidence",
    "evidence",
    "raw_output",
    "parse_error",
    "prompt",
    "created_at",
]


def test_clean_dataset_schema_constant() -> None:
    assert CLEAN_DATASET_COLUMNS == [
        "id",
        "dataset",
        "task_type",
        "question",
        "options",
        "gold_answer",
        "gold_label",
        "evidence",
        "category",
        "source_file",
    ]


def test_decision_result_schemas() -> None:
    outputs = pd.DataFrame(
        [
            {"sample_id": "s1", "model": "deepseek", "answer": "A", "confidence": 0.8, "evidence": "e", "parse_error": ""},
            {"sample_id": "s1", "model": "qwen", "answer": "A", "confidence": 0.7, "evidence": "e", "parse_error": ""},
        ]
    )
    majority = majority_vote(outputs)
    assert list(majority.columns) == [
        "sample_id",
        "method",
        "final_answer",
        "vote_distribution",
        "agreement_rate",
        "risk_level",
        "decision_note",
    ]

    dynamic = pd.DataFrame([dynamic_decision({"id": "s1"}, outputs.to_dict(orient="records"))])
    assert list(dynamic.columns) == [
        "sample_id",
        "method",
        "final_answer",
        "reliability_score",
        "risk_level",
        "agreement_rate",
        "avg_confidence",
        "evidence_support_score",
        "answer_diversity",
        "minority_warning",
        "decision_note",
    ]


def test_fixed_judge_and_risk_label_schemas() -> None:
    class DummyJudge:
        def call_json(self, prompt, temperature=0.0, max_tokens=800):
            return {
                "final_answer": "A",
                "decision_reason": "多数一致",
                "risk_level": "low",
                "confidence": 0.9,
                "raw_output": "{}",
            }

    fixed = pd.DataFrame([fixed_judge_decision({"id": "s1"}, [], DummyJudge())])
    assert list(fixed.columns) == [
        "sample_id",
        "method",
        "final_answer",
        "decision_reason",
        "risk_level",
        "confidence",
    ]

    samples = pd.DataFrame([{"id": "s1", "gold_answer": "A", "gold_label": "A"}])
    outputs = pd.DataFrame(
        [
            {"sample_id": "s1", "model": "deepseek", "answer": "A", "confidence": 0.8, "parse_error": ""},
            {"sample_id": "s1", "model": "qwen", "answer": "B", "confidence": 0.6, "parse_error": ""},
        ]
    )
    risk = label_risks(samples, outputs)
    assert list(risk.columns) == [
        "sample_id",
        "risk_labels",
        "majority_answer",
        "correct_models",
        "incorrect_models",
        "majority_is_correct",
    ]
