from __future__ import annotations

import pandas as pd

import scripts.run_pipeline as pipeline


def test_model_calls_step_resumes_existing_success(tmp_path, monkeypatch) -> None:
    samples_path = tmp_path / "samples.csv"
    outputs_path = tmp_path / "model_outputs.csv"
    pd.DataFrame(
        [
            {"id": "s1", "dataset": "mock", "question": "Q1"},
            {"id": "s2", "dataset": "mock", "question": "Q2"},
        ]
    ).to_csv(samples_path, index=False)
    pd.DataFrame(
        [
            {
                "sample_id": "s1",
                "dataset": "mock",
                "model": "deepseek",
                "answer": "A",
                "reason": "",
                "confidence": 0.9,
                "evidence": "e",
                "raw_output": "{}",
                "parse_error": "",
                "prompt": "p",
                "created_at": "now",
            }
        ]
    ).to_csv(outputs_path, index=False)

    monkeypatch.setitem(pipeline.PATHS, "model_outputs", outputs_path)

    calls = []

    def fake_call(sample, model_name, temperature, max_tokens):
        calls.append((sample["id"], model_name))
        return {
            "sample_id": sample["id"],
            "dataset": sample.get("dataset", ""),
            "model": model_name,
            "answer": "B",
            "reason": "",
            "confidence": 0.5,
            "evidence": "e",
            "raw_output": "{}",
            "parse_error": "",
            "prompt": "p",
            "created_at": "now",
        }

    monkeypatch.setattr(pipeline, "call_one_model", fake_call)
    pipeline.model_calls_step(samples_path, ["deepseek"], limit=None, max_workers=1)

    assert calls == [("s2", "deepseek")]
    out = pd.read_csv(outputs_path)
    assert len(out) == 2
    assert set(out["sample_id"]) == {"s1", "s2"}
    assert list(out.columns) == [
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
