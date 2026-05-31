from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from src.evaluation.correctness import is_correct as sample_is_correct
from src.parsing.answer_normalizer import normalize_answer as normalize_sample_answer
from src.schemas import ModelAnswer, QuestionSample
from src.utils import normalize_text


def normalize_answer(answer: Any) -> str:
    """Normalize free-form answers for dataset-level evaluation."""

    text = normalize_text("" if answer is None else str(answer))
    upper = text.upper()
    if upper == "SUPPORTS":
        return "SUPPORTED"
    if upper == "REFUTES":
        return "REFUTED"
    if upper in {"A", "B", "C", "D", "E"}:
        return upper
    if upper in {"SUPPORTED", "REFUTED", "NOT ENOUGH INFO"}:
        return upper
    if text in {"true", "yes", "correct", "supported"}:
        return "SUPPORTED"
    if text in {"false", "no", "incorrect", "refuted"}:
        return "REFUTED"
    return text


def is_correct(pred: Any, gold_answer: Any = "", gold_label: Any = "") -> bool:
    """Check a prediction against either gold_label or gold_answer."""

    pred_norm = normalize_answer(pred)
    gold_label_norm = normalize_answer(gold_label)
    gold_answer_norm = normalize_answer(gold_answer)
    if not pred_norm:
        return False
    if gold_label_norm and pred_norm == gold_label_norm:
        return True
    if gold_answer_norm and pred_norm == gold_answer_norm:
        return True
    if gold_answer_norm and (pred_norm in gold_answer_norm or gold_answer_norm in pred_norm):
        return True
    return False


def _sample_gold_map(samples_df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    return {
        str(row["id"]): {
            "gold_answer": row.get("gold_answer", ""),
            "gold_label": row.get("gold_label", ""),
        }
        for row in samples_df.to_dict(orient="records")
    }


def _aligned_truth_pred(decision_df: pd.DataFrame, samples_df: pd.DataFrame) -> tuple[List[str], List[str]]:
    if decision_df.empty:
        return [], []
    gold_map = _sample_gold_map(samples_df)
    y_true: List[str] = []
    y_pred: List[str] = []
    for row in decision_df.to_dict(orient="records"):
        sample_id = str(row.get("sample_id", ""))
        gold = gold_map.get(sample_id)
        if not gold:
            continue
        gold_label = normalize_answer(gold.get("gold_label"))
        gold_answer = normalize_answer(gold.get("gold_answer"))
        if gold_label in {"TRUTHFUL", "TRUTHFULNESS", "UNKNOWN"} and gold_answer:
            y_true.append(gold_answer)
        else:
            y_true.append(gold_label or gold_answer)
        y_pred.append(normalize_answer(row.get("final_answer", "")))
    return y_true, y_pred


def compute_accuracy(decision_df: pd.DataFrame, samples_df: pd.DataFrame) -> float:
    if decision_df.empty:
        return 0.0
    gold_map = _sample_gold_map(samples_df)
    correct = 0
    total = 0
    for row in decision_df.to_dict(orient="records"):
        sample_id = str(row.get("sample_id", ""))
        gold = gold_map.get(sample_id)
        if not gold:
            continue
        total += 1
        if is_correct(row.get("final_answer", ""), gold.get("gold_answer", ""), gold.get("gold_label", "")):
            correct += 1
    return float(correct / total) if total else 0.0


def compute_macro_f1(decision_df: pd.DataFrame, samples_df: pd.DataFrame) -> float:
    y_true, y_pred = _aligned_truth_pred(decision_df, samples_df)
    if not y_true:
        return 0.0
    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def _risk_rate(risk_df: pd.DataFrame, label: str) -> float:
    if risk_df.empty or "risk_labels" not in risk_df.columns:
        return 0.0
    return float(risk_df["risk_labels"].fillna("").str.contains(label, regex=False).mean())


def compute_false_consensus_rate(risk_df: pd.DataFrame) -> float:
    return _risk_rate(risk_df, "false_consensus")


def compute_minority_correct_rate(risk_df: pd.DataFrame) -> float:
    return _risk_rate(risk_df, "minority_correct")


def compute_high_disagreement_rate(risk_df: pd.DataFrame) -> float:
    return _risk_rate(risk_df, "high_disagreement")


def compute_confidence_mismatch_rate(risk_df: pd.DataFrame) -> float:
    return _risk_rate(risk_df, "confidence_mismatch")


def risk_level_effectiveness(decision_df: pd.DataFrame, samples_df: pd.DataFrame) -> pd.DataFrame:
    """Accuracy/error rate grouped by decision risk_level."""

    if decision_df.empty or "risk_level" not in decision_df.columns:
        return pd.DataFrame(columns=["risk_level", "sample_count", "accuracy", "error_rate"])
    gold_map = _sample_gold_map(samples_df)
    rows: List[Dict[str, Any]] = []
    for row in decision_df.to_dict(orient="records"):
        sample_id = str(row.get("sample_id", ""))
        gold = gold_map.get(sample_id)
        if not gold:
            continue
        rows.append(
            {
                "risk_level": str(row.get("risk_level", "unknown")).lower(),
                "correct": is_correct(row.get("final_answer", ""), gold.get("gold_answer", ""), gold.get("gold_label", "")),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["risk_level", "sample_count", "accuracy", "error_rate"])
    df = pd.DataFrame(rows)
    grouped = (
        df.groupby("risk_level")
        .agg(sample_count=("correct", "size"), accuracy=("correct", "mean"))
        .reset_index()
    )
    grouped["error_rate"] = 1.0 - grouped["accuracy"]
    return grouped[["risk_level", "sample_count", "accuracy", "error_rate"]]


def answer_consistency_rate(sample: QuestionSample, answers: List[ModelAnswer]) -> float:
    valid = [a for a in answers if a.parse_ok and a.answer]
    if not valid:
        return 0.0
    counts = Counter(normalize_sample_answer(a.answer, sample) for a in valid)
    return counts.most_common(1)[0][1] / len(valid)


def evidence_support_score(answers: List[ModelAnswer]) -> float:
    valid = [a for a in answers if a.parse_ok]
    if not valid:
        return 0.0
    scores = []
    for answer in valid:
        evidence = (answer.evidence or "").strip().lower()
        reason = (answer.reason or "").strip()
        score = 0.0
        if evidence and evidence != "unknown":
            score += 0.6
        if len(reason) >= 15:
            score += 0.4
        scores.append(score)
    return float(np.mean(scores))


def classification_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, float]:
    if not y_true:
        return {"accuracy": 0.0, "f1_macro": 0.0}
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def model_accuracy(sample: QuestionSample, answers: List[ModelAnswer]) -> float:
    valid = [a for a in answers if a.parse_ok and a.answer]
    if not valid:
        return 0.0
    return sum(sample_is_correct(sample, a.answer) for a in valid) / len(valid)
