from __future__ import annotations

from typing import Any


def normalize_answer(answer: Any) -> str:
    text = " ".join(str(answer or "").strip().split())
    upper = text.upper()
    if upper == "SUPPORTS":
        return "SUPPORTED"
    if upper == "REFUTES":
        return "REFUTED"
    if upper in {"A", "B", "C", "D", "E"}:
        return upper
    if upper in {"SUPPORTED", "REFUTED", "NOT ENOUGH INFO", "UNKNOWN", "TRUTHFUL"}:
        return upper
    lowered = text.lower().strip(" .。!！?？,，;；:")
    if lowered in {"true", "yes", "correct", "supported"}:
        return "SUPPORTED"
    if lowered in {"false", "no", "incorrect", "refuted"}:
        return "REFUTED"
    return lowered


def is_correct(pred: Any, gold_answer: Any = "", gold_label: Any = "") -> bool:
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
