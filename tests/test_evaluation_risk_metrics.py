import pandas as pd

from src.evaluation.metrics import compute_accuracy, compute_false_consensus_rate, is_correct, risk_level_effectiveness
from src.evaluation.risk_labeler import label_risks


def test_is_correct_uses_gold_label() -> None:
    assert is_correct("A", gold_answer="scissors", gold_label="A")
    assert is_correct("SUPPORTED", gold_answer="", gold_label="SUPPORTED")
    assert not is_correct("REFUTED", gold_answer="", gold_label="SUPPORTED")


def test_label_risks_false_consensus_minority_correct() -> None:
    samples = pd.DataFrame(
        [{"id": "s1", "gold_answer": "SUPPORTED", "gold_label": "SUPPORTED"}]
    )
    outputs = pd.DataFrame(
        [
            {"sample_id": "s1", "answer": "REFUTED", "confidence": 0.9, "parse_error": ""},
            {"sample_id": "s1", "answer": "REFUTED", "confidence": 0.8, "parse_error": ""},
            {"sample_id": "s1", "answer": "SUPPORTED", "confidence": 0.6, "parse_error": ""},
        ]
    )
    risks = label_risks(samples, outputs)
    labels = risks.iloc[0]["risk_labels"]
    assert "false_consensus" in labels
    assert "minority_correct" in labels
    assert "confidence_mismatch" in labels


def test_compute_accuracy_and_risk_rate() -> None:
    samples = pd.DataFrame(
        [
            {"id": "s1", "gold_answer": "A", "gold_label": "A"},
            {"id": "s2", "gold_answer": "B", "gold_label": "B"},
        ]
    )
    decisions = pd.DataFrame(
        [
            {"sample_id": "s1", "final_answer": "A", "risk_level": "low"},
            {"sample_id": "s2", "final_answer": "A", "risk_level": "high"},
        ]
    )
    risks = pd.DataFrame(
        [
            {"sample_id": "s1", "risk_labels": "true_consensus"},
            {"sample_id": "s2", "risk_labels": "false_consensus"},
        ]
    )
    assert compute_accuracy(decisions, samples) == 0.5
    assert compute_false_consensus_rate(risks) == 0.5
    eff = risk_level_effectiveness(decisions, samples)
    assert set(eff["risk_level"]) == {"low", "high"}
