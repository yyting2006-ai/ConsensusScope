from __future__ import annotations

import json
from collections import Counter
from typing import Any, Dict, List, Tuple

import pandas as pd

from src.evaluation.metrics import is_correct, normalize_answer


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _parse_ok(row: Dict[str, Any]) -> bool:
    if "parse_error" in row and _safe_str(row.get("parse_error", "")):
        return False
    if "parse_ok" not in row:
        return True
    return str(row.get("parse_ok")).lower() in {"true", "1", "yes"}


def _valid_outputs(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [row for row in rows if _parse_ok(row) and _safe_str(row.get("answer", ""))]


def _majority(counts: Counter) -> Tuple[str, int, bool]:
    if not counts:
        return "", 0, False
    answer, count = counts.most_common(1)[0]
    unique = sum(1 for c in counts.values() if c == count) == 1
    return answer, count, unique


def label_sample_risks(sample: Dict[str, Any], model_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid = _valid_outputs(model_outputs)
    sample_id = _safe_str(sample.get("id", ""))
    gold_answer = sample.get("gold_answer", "")
    gold_label = sample.get("gold_label", "")

    normalized_answers = [normalize_answer(row.get("answer", "")) for row in valid]
    counts = Counter(answer for answer in normalized_answers if answer)
    majority_answer, majority_count, unique_majority = _majority(counts)
    model_count = len(valid)
    agreement_rate = majority_count / model_count if model_count else 0.0

    labels: List[str] = []
    correct_flags = [
        is_correct(row.get("answer", ""), gold_answer=gold_answer, gold_label=gold_label)
        for row in valid
    ]
    correct_model_count = sum(correct_flags)
    majority_correct = bool(majority_answer) and is_correct(
        majority_answer,
        gold_answer=gold_answer,
        gold_label=gold_label,
    )

    if not unique_majority or agreement_rate < 0.5:
        labels.append("high_disagreement")
    elif majority_correct:
        labels.append("true_consensus")
    else:
        labels.append("false_consensus")

    if unique_majority and not majority_correct:
        minority_correct = any(
            correct
            and normalize_answer(row.get("answer", "")) != majority_answer
            for row, correct in zip(valid, correct_flags)
        )
        if minority_correct:
            labels.append("minority_correct")

    wrong_high_confidence_count = 0
    for row, correct in zip(valid, correct_flags):
        if _safe_float(row.get("confidence", 0.0)) >= 0.8 and not correct:
            wrong_high_confidence_count += 1
    if wrong_high_confidence_count > 0:
        labels.append("confidence_mismatch")

    if not labels:
        labels.append("normal")

    return {
        "sample_id": sample_id,
        "risk_labels": ";".join(labels),
        "majority_answer": majority_answer,
        "correct_models": correct_model_count,
        "incorrect_models": model_count - correct_model_count,
        "majority_is_correct": majority_correct,
    }


def label_risks(samples_df: pd.DataFrame, outputs_df: pd.DataFrame) -> pd.DataFrame:
    if "id" not in samples_df.columns:
        raise ValueError("samples_df must contain id")
    if "sample_id" not in outputs_df.columns:
        raise ValueError("outputs_df must contain sample_id")

    outputs_by_sample = {
        str(sample_id): group.to_dict(orient="records")
        for sample_id, group in outputs_df.groupby("sample_id", sort=False)
    }
    rows = [
        label_sample_risks(sample, outputs_by_sample.get(str(sample.get("id", "")), []))
        for sample in samples_df.to_dict(orient="records")
    ]
    return pd.DataFrame(rows)
