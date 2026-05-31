from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments import run_model_answers as rma


def test_run_model_answers_resume_and_immediate_save(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "clean_dataset.csv"
    output_path = tmp_path / "model_outputs.csv"
    log_path = tmp_path / "run_log.txt"
    pd.DataFrame(
        [
            {
                "id": "s1",
                "dataset": "mock",
                "task_type": "mock_task",
                "question": "Q1",
                "options": "",
                "gold_answer": "A",
                "gold_label": "A",
                "evidence": "",
                "category": "",
                "source_file": "mock",
            },
            {
                "id": "s2",
                "dataset": "mock",
                "task_type": "mock_task",
                "question": "Q2",
                "options": "",
                "gold_answer": "B",
                "gold_label": "B",
                "evidence": "",
                "category": "",
                "source_file": "mock",
            },
        ]
    ).to_csv(input_path, index=False)
    pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "dataset": "mock",
                "task_type": "mock_task",
                "model": "deepseek",
                "answer": "A",
                "reason": "",
                "confidence": 0.9,
                "evidence": "",
                "raw_output": "{}",
                "parse_error": "",
                "prompt": "old",
                "created_at": "old",
            }
        ]
    ).to_csv(output_path, index=False)

    calls = []

    def fake_call_model(sample, model):
        calls.append((sample["id"], model))
        return {
            "sample_id": sample["id"],
            "dataset": sample["dataset"],
            "task_type": sample["task_type"],
            "model": model,
            "answer": "B",
            "reason": "mock",
            "confidence": 0.5,
            "evidence": "mock evidence",
            "raw_output": '{"answer":"B"}',
            "parse_error": "",
            "prompt": "prompt",
            "created_at": "now",
        }

    monkeypatch.setattr(rma, "check_api_keys", lambda models: None)
    monkeypatch.setattr(rma, "call_model", fake_call_model)

    result = rma.run_model_answers(
        input_path=input_path,
        output_path=output_path,
        models=["deepseek"],
        limit=2,
        resume=True,
        log_path=log_path,
    )

    assert calls == [("s2", "deepseek")]
    assert list(result.columns) == rma.STANDARD_COLUMNS
    written = pd.read_csv(output_path)
    assert list(written.columns) == rma.STANDARD_COLUMNS
    assert len(written) == 2
    assert log_path.exists()


def test_call_model_records_parse_error(monkeypatch) -> None:
    class DummyClient:
        def call_json(self, prompt, temperature=0.2, max_tokens=800):
            return {"raw_output": "not json", "parse_error": "JSON error"}

    monkeypatch.setattr(rma, "get_client", lambda model: DummyClient())
    row = rma.call_model({"id": "s1", "dataset": "d", "task_type": "t", "question": "Q"}, "deepseek")
    assert row["raw_output"] == "not json"
    assert row["parse_error"] == "JSON error"
