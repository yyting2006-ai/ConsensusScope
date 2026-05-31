import pandas as pd
import pytest

from src.decision.baselines import majority_vote, single_model_decision
from src.decision.dynamic_decision import dynamic_decision


def test_majority_vote_unique_winner() -> None:
    df = pd.DataFrame(
        [
            {"sample_id": "s1", "model": "a", "answer": "A", "parse_error": ""},
            {"sample_id": "s1", "model": "b", "answer": "A", "parse_error": ""},
            {"sample_id": "s1", "model": "c", "answer": "B", "parse_error": ""},
        ]
    )
    result = majority_vote(df).iloc[0]
    assert result["final_answer"] == "A"
    assert result["agreement_rate"] == pytest.approx(2 / 3)
    assert result["decision_note"] == "采纳唯一最高票答案"


def test_majority_vote_tie() -> None:
    df = pd.DataFrame(
        [
            {"sample_id": "s1", "model": "a", "answer": "A", "parse_error": ""},
            {"sample_id": "s1", "model": "b", "answer": "B", "parse_error": ""},
        ]
    )
    result = majority_vote(df).iloc[0]
    assert result["final_answer"] == ""
    assert result["risk_level"] == "high"
    assert "平票" in result["decision_note"]


def test_single_model_decision_matches_provider() -> None:
    df = pd.DataFrame(
        [
            {"sample_id": "s1", "model": "deepseek", "answer": "A"},
            {"sample_id": "s1", "model": "qwen", "answer": "B"},
        ]
    )
    result = single_model_decision(df, "deepseek").iloc[0]
    assert result["final_answer"] == "A"


def test_dynamic_decision_high_confidence_minority_warning() -> None:
    sample = {"id": "s1"}
    outputs = [
        {"answer": "A", "confidence": 0.6, "evidence": "证据1", "parse_error": ""},
        {"answer": "A", "confidence": 0.6, "evidence": "证据2", "parse_error": ""},
        {"answer": "A", "confidence": 0.6, "evidence": "证据3", "parse_error": ""},
        {"answer": "B", "confidence": 0.9, "evidence": "反证", "parse_error": ""},
    ]
    result = dynamic_decision(sample, outputs)
    assert result["final_answer"] == "A"
    assert result["minority_warning"] is True
    assert result["decision_note"] == "触发少数派预警"
