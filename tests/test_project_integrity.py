from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pandas as pd

import src
from app.streamlit_app import read_table
from src.decision.baselines import majority_vote
from src.decision.dynamic_decision import dynamic_decision
from src.evaluation.risk_labeler import label_risks
from src.llm.clients import parse_json_from_text


def test_all_src_modules_importable() -> None:
    package_root = Path(src.__file__).resolve().parent
    failures = []
    for module_info in pkgutil.walk_packages([str(package_root)], prefix="src."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:
            failures.append(f"{module_info.name}: {exc}")
    assert failures == []


def test_csv_field_chain_for_decision_and_risk_labeler() -> None:
    samples = pd.DataFrame(
        [
            {
                "id": "s1",
                "dataset": "commonsenseqa",
                "task_type": "commonsense_reasoning",
                "question": "Which option is correct?",
                "options": "",
                "gold_answer": "A",
                "gold_label": "A",
                "evidence": "",
                "category": "",
                "source_file": "mock",
            }
        ]
    )
    outputs = pd.DataFrame(
        [
            {"sample_id": "s1", "model": "deepseek", "answer": "A", "confidence": 0.7, "evidence": "e", "parse_error": ""},
            {"sample_id": "s1", "model": "qwen", "answer": "A", "confidence": 0.8, "evidence": "e", "parse_error": ""},
            {"sample_id": "s1", "model": "glm", "answer": "B", "confidence": 0.6, "evidence": "e", "parse_error": ""},
        ]
    )
    majority = majority_vote(outputs)
    dynamic = dynamic_decision(samples.iloc[0].to_dict(), outputs.to_dict(orient="records"))
    risks = label_risks(samples, outputs)

    assert majority.iloc[0]["final_answer"] == "A"
    assert dynamic["final_answer"] == "A"
    assert "true_consensus" in risks.iloc[0]["risk_labels"]


def test_json_parse_failure_is_handled() -> None:
    parsed = parse_json_from_text("this is not json")
    assert parsed["raw_output"] == "this is not json"
    assert parsed["parse_error"]


def test_streamlit_read_missing_file_returns_empty_df(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    df = read_table(str(missing))
    assert df.empty
