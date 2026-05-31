from pathlib import Path

import pandas as pd
import pytest

from src.decision.ml_reliability import build_feature_table, run_ml_reliability


def test_build_feature_table() -> None:
    samples = pd.DataFrame([{"id": "s1", "gold_answer": "A", "gold_label": "A"}])
    outputs = pd.DataFrame(
        [
            {"sample_id": "s1", "answer": "A", "confidence": 0.9, "evidence": "证据", "parse_error": ""},
            {"sample_id": "s1", "answer": "A", "confidence": 0.8, "evidence": "证据", "parse_error": ""},
            {"sample_id": "s1", "answer": "B", "confidence": 0.95, "evidence": "反证", "parse_error": ""},
        ]
    )

    features = build_feature_table(samples, outputs).iloc[0]

    assert features["sample_id"] == "s1"
    assert features["agreement_rate"] == pytest.approx(2 / 3)
    assert features["model_count"] == 3
    assert features["max_vote_count"] == 2
    assert features["minority_warning"] == 1


def test_run_ml_reliability_saves_metrics_and_models(tmp_path: Path) -> None:
    samples = pd.DataFrame(
        [
            {"id": f"s{i}", "gold_answer": "A" if i % 2 == 0 else "B", "gold_label": "A" if i % 2 == 0 else "B"}
            for i in range(12)
        ]
    )
    rows = []
    for i in range(12):
        sample_id = f"s{i}"
        correct = "A" if i % 2 == 0 else "B"
        wrong = "B" if correct == "A" else "A"
        answers = [correct, correct, wrong] if i < 6 else [wrong, wrong, correct]
        for j, answer in enumerate(answers):
            rows.append(
                {
                    "sample_id": sample_id,
                    "model": f"m{j}",
                    "answer": answer,
                    "confidence": 0.9 - j * 0.1,
                    "evidence": "证据",
                    "parse_error": "",
                }
            )
    outputs = pd.DataFrame(rows)

    samples_path = tmp_path / "samples.csv"
    outputs_path = tmp_path / "outputs.csv"
    metrics_path = tmp_path / "results" / "ml_reliability_metrics.csv"
    models_dir = tmp_path / "models"
    samples.to_csv(samples_path, index=False)
    outputs.to_csv(outputs_path, index=False)

    metrics = run_ml_reliability(samples_path, outputs_path, metrics_path, models_dir, seed=1, test_size=0.25)

    assert metrics_path.exists()
    assert len(metrics) == 4
    assert set(metrics["model_type"]) == {"logistic_regression", "random_forest"}
    assert (models_dir / "ml_reliability_majority_vote_logistic_regression.pkl").exists()
    assert (models_dir / "ml_reliability_dynamic_decision_random_forest.pkl").exists()
