from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

import pandas as pd


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


def _valid_model_outputs(model_outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    valid: List[Dict[str, Any]] = []
    for item in model_outputs:
        if "parse_error" in item and _safe_str(item.get("parse_error", "")):
            continue
        if "parse_ok" in item and str(item.get("parse_ok")).lower() not in {"true", "1", "yes"}:
            continue
        if _safe_str(item.get("answer", "")):
            valid.append(item)
    return valid


def _evidence_present(value: Any) -> bool:
    text = _safe_str(value).lower()
    if not text or text in {"无", "none", "null", "unknown", "n/a", "na"}:
        return False
    # Very short generic evidence is usually just a placeholder, not real support.
    return len(text) >= 2


def _canonical_label(value: Any) -> str:
    text = _safe_str(value)
    upper = text.upper()
    if upper in {"SUPPORTED", "SUPPORTS", "TRUE", "YES"}:
        return "SUPPORTED"
    if upper in {"REFUTED", "REFUTES", "FALSE", "NO"}:
        return "REFUTED"
    if upper in {"NOT ENOUGH INFO", "NEI", "UNKNOWN", "UNCERTAIN"}:
        return "NOT ENOUGH INFO"
    return text


def _is_verification_label(value: Any) -> bool:
    return _canonical_label(value) in {"SUPPORTED", "REFUTED", "NOT ENOUGH INFO"}


def _majority_info(outputs: List[Dict[str, Any]]) -> Tuple[str, int, Counter, bool, int]:
    counts = Counter(_safe_str(item.get("answer", "")) for item in outputs if _safe_str(item.get("answer", "")))
    if not counts:
        return "", 0, counts, False, 0
    ranked = counts.most_common()
    answer, count = ranked[0]
    second_count = ranked[1][1] if len(ranked) > 1 else 0
    unique_majority = len(ranked) == 1 or count > second_count
    return answer, count, counts, unique_majority, second_count


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def dynamic_decision(sample: Dict[str, Any], model_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rule-based dynamic adjudication mechanism."""

    outputs = _valid_model_outputs(model_outputs)
    sample_id = _safe_str(sample.get("id", ""))
    task_type = _safe_str(sample.get("task_type", ""))
    n_models = len(outputs)
    if n_models == 0:
        return {
            "sample_id": sample_id,
            "method": "dynamic_decision",
            "final_answer": "",
            "reliability_score": 0.0,
            "risk_level": "high",
            "agreement_rate": 0.0,
            "avg_confidence": 0.0,
            "evidence_support_score": 0.0,
            "answer_diversity": 0.0,
            "minority_warning": False,
            "decision_note": "无有效模型输出，建议人工复核",
        }

    if task_type == "fact_verification":
        normalized_outputs: List[Dict[str, Any]] = []
        for item in outputs:
            copied = dict(item)
            copied["answer"] = _canonical_label(copied.get("answer", ""))
            normalized_outputs.append(copied)
        outputs = normalized_outputs

    majority_answer, majority_count, counts, unique_majority, second_count = _majority_info(outputs)
    agreement_rate = majority_count / n_models
    confidences = [_safe_float(item.get("confidence", 0.0)) for item in outputs]
    avg_confidence = _avg(confidences)
    evidence_support_score = sum(1.0 for item in outputs if _evidence_present(item.get("evidence", ""))) / n_models
    answer_diversity = len(counts) / n_models
    consensus_margin = (majority_count - second_count) / n_models if n_models else 0.0

    majority_confidences = [
        _safe_float(item.get("confidence", 0.0))
        for item in outputs
        if _safe_str(item.get("answer", "")) == majority_answer
    ]
    minority_confidences = [
        _safe_float(item.get("confidence", 0.0))
        for item in outputs
        if _safe_str(item.get("answer", "")) != majority_answer
    ]
    majority_avg_confidence = _avg(majority_confidences)
    minority_max_confidence = max(minority_confidences) if minority_confidences else 0.0

    # Be deliberately sensitive to minority signals. In small-N multi-model
    # settings, a correct minority can be buried by a correlated majority.
    high_confidence_minority = bool(minority_confidences) and (
        minority_max_confidence >= max(0.60, majority_avg_confidence - 0.15)
    )
    minority_warning_penalty = 1.0 if high_confidence_minority else 0.0
    weak_evidence_penalty = 1.0 if agreement_rate >= 0.75 and evidence_support_score < 0.5 else 0.0

    # Optimized for risk calibration rather than maximum raw accuracy:
    # high agreement still matters, but low evidence and high-confidence
    # minorities prevent over-confident low-risk labels.
    reliability_score = (
        0.40 * agreement_rate
        + 0.20 * evidence_support_score
        + 0.15 * avg_confidence
        + 0.15 * (1 - answer_diversity)
        + 0.10 * consensus_margin
        - 0.12 * minority_warning_penalty
        - 0.08 * weak_evidence_penalty
    )
    reliability_score = max(0.0, min(1.0, reliability_score))

    if reliability_score >= 0.75:
        risk_level = "low"
    elif reliability_score >= 0.50:
        risk_level = "medium"
    else:
        risk_level = "high"

    minority_warning = high_confidence_minority
    final_answer = majority_answer

    if not unique_majority:
        final_answer = ""
        risk_level = "high"
        decision_note = "无唯一多数答案，建议人工复核"
    elif agreement_rate == 1:
        if evidence_support_score >= 0.75 and avg_confidence >= 0.65:
            risk_level = "low"
            decision_note = "低风险采纳"
        else:
            risk_level = "medium"
            decision_note = "一致但证据或置信度不足，标记为风险共识"
        if task_type == "fact_verification" and majority_answer != "NOT ENOUGH INFO":
            risk_level = "medium"
            decision_note = "事实核查非NEI共识仍需证据审查，避免低风险误判"
        elif task_type == "truthfulness_qa" and _is_verification_label(majority_answer):
            risk_level = "medium"
            decision_note = "开放式真实性问答输出核查标签，避免低风险误判"
    elif agreement_rate >= 0.75 and high_confidence_minority:
        decision_note = "触发少数派预警"
        risk_level = "medium" if risk_level == "low" else risk_level
    elif agreement_rate < 0.5:
        final_answer = ""
        risk_level = "high"
        decision_note = "高分歧，建议人工复核"
    elif reliability_score >= 0.75 and not high_confidence_minority and evidence_support_score >= 0.5:
        decision_note = "低风险采纳"
        risk_level = "low"
        if task_type == "fact_verification" and majority_answer != "NOT ENOUGH INFO":
            risk_level = "medium"
            decision_note = "事实核查存在分歧，避免低风险误判"
    else:
        if risk_level == "high" and agreement_rate >= 0.5:
            # Avoid turning most ambiguous-but-usable samples into high risk.
            risk_level = "medium"
        decision_note = "采纳多数答案，并根据可靠性评分分级"

    return {
        "sample_id": sample_id,
        "method": "dynamic_decision",
        "final_answer": final_answer,
        "reliability_score": round(reliability_score, 6),
        "risk_level": risk_level,
        "agreement_rate": round(agreement_rate, 6),
        "avg_confidence": round(avg_confidence, 6),
        "evidence_support_score": round(evidence_support_score, 6),
        "answer_diversity": round(answer_diversity, 6),
        "minority_warning": minority_warning,
        "decision_note": decision_note,
    }


def estimate_model_reliability(samples_df: pd.DataFrame, outputs_df: pd.DataFrame) -> Dict[str, float]:
    """Estimate historical model reliability from the available audited corpus.

    The estimate supports experimental auxiliary analyses only. It is
    intentionally stored as aggregate model-level calibration, not as API keys
    or private prompts.
    """

    from src.evaluation.metrics import is_correct

    if samples_df.empty or outputs_df.empty or "id" not in samples_df.columns or "sample_id" not in outputs_df.columns:
        return {}
    sample_by_id = {str(row["id"]): row for row in samples_df.to_dict(orient="records")}
    buckets: Dict[str, List[int]] = defaultdict(list)
    for row in outputs_df.to_dict(orient="records"):
        sample = sample_by_id.get(_safe_str(row.get("sample_id", "")))
        if not sample:
            continue
        model = _safe_str(row.get("model", row.get("provider", row.get("model_name", ""))))
        if not model:
            continue
        buckets[model].append(
            int(is_correct(row.get("answer", ""), sample.get("gold_answer", ""), sample.get("gold_label", "")))
        )
    return {
        model: round((sum(vals) + 1.0) / (len(vals) + 2.0), 6)
        for model, vals in buckets.items()
        if vals
    }


def learned_meta_judge_decision(
    sample: Dict[str, Any],
    model_outputs: List[Dict[str, Any]],
    model_reliability: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """Experimental auxiliary learned meta-judge over answer candidates.

    This variant is not part of the EMNLP 2026 main demo claim. The main demo
    reports majority vote, fixed judge and rule-based dynamic adjudication.
    """

    model_reliability = model_reliability or {}
    outputs = _valid_model_outputs(model_outputs)
    sample_id = _safe_str(sample.get("id", ""))
    if not outputs:
        return {
            "sample_id": sample_id,
            "method": "learned_meta_judge",
            "final_answer": "",
            "reliability_score": 0.0,
            "risk_level": "high",
            "agreement_rate": 0.0,
            "avg_confidence": 0.0,
            "evidence_support_score": 0.0,
            "answer_diversity": 0.0,
            "minority_warning": False,
            "decision_note": "无有效模型输出，学习型裁决器建议人工复核",
            "meta_weights": "{}",
        }

    task_type = _safe_str(sample.get("task_type", ""))
    if task_type == "fact_verification":
        normalized_outputs: List[Dict[str, Any]] = []
        for item in outputs:
            copied = dict(item)
            copied["answer"] = _canonical_label(copied.get("answer", ""))
            normalized_outputs.append(copied)
        outputs = normalized_outputs

    majority_answer, majority_count, counts, unique_majority, second_count = _majority_info(outputs)
    n_models = len(outputs)
    agreement_rate = majority_count / n_models if n_models else 0.0
    answer_diversity = len(counts) / n_models if n_models else 0.0
    confidences = [_safe_float(item.get("confidence", 0.0)) for item in outputs]
    avg_confidence = _avg(confidences)
    evidence_support_score = sum(1.0 for item in outputs if _evidence_present(item.get("evidence", ""))) / n_models

    answer_scores: Dict[str, float] = defaultdict(float)
    answer_details: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in outputs:
        answer = _safe_str(item.get("answer", ""))
        model = _safe_str(item.get("model", item.get("provider", item.get("model_name", ""))))
        provider = _safe_str(item.get("provider", ""))
        history = model_reliability.get(model, model_reliability.get(provider, 0.50))
        confidence = _safe_float(item.get("confidence", 0.0))
        evidence = 1.0 if _evidence_present(item.get("evidence", "")) else 0.0
        vote_support = counts[answer] / n_models
        # Offline-calibrated linear meta-score. The strongest coefficient is
        # model reliability because the training corpus shows stable model-level
        # differences; evidence and confidence break ties and surface minorities.
        weight = 0.62 * history + 0.16 * confidence + 0.14 * evidence + 0.08 * vote_support
        answer_scores[answer] += weight
        answer_details[answer].append(
            {
                "model": model or provider,
                "history": round(history, 3),
                "confidence": round(confidence, 3),
                "evidence": round(evidence, 3),
                "vote_support": round(vote_support, 3),
                "weight": round(weight, 3),
            }
        )

    ranked = sorted(answer_scores.items(), key=lambda pair: pair[1], reverse=True)
    final_answer, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    total_score = sum(answer_scores.values()) or 1.0
    weighted_agreement = top_score / total_score
    margin = (top_score - second_score) / total_score
    minority_warning = bool(unique_majority and final_answer != majority_answer)

    reliability_score = (
        0.34 * weighted_agreement
        + 0.18 * agreement_rate
        + 0.18 * evidence_support_score
        + 0.15 * avg_confidence
        + 0.15 * max(0.0, margin)
    )
    if minority_warning:
        reliability_score -= 0.04
    reliability_score = max(0.0, min(1.0, reliability_score))

    if not unique_majority and margin < 0.08:
        risk_level = "high"
        note = "学习型 Meta-Judge 未发现稳定领先答案，建议人工复核"
    elif reliability_score >= 0.72 and not minority_warning:
        risk_level = "low"
        note = "学习型 Meta-Judge 基于历史可靠性、证据和置信度低风险采纳"
    elif reliability_score >= 0.48:
        risk_level = "medium"
        note = "学习型 Meta-Judge 采纳领先答案，但保留中风险复核提示"
    else:
        risk_level = "high"
        note = "学习型 Meta-Judge 认为可靠性不足，建议人工复核"
    if minority_warning:
        note = "学习型 Meta-Judge 覆盖多数投票：历史可靠性、证据或置信度支持少数答案"

    return {
        "sample_id": sample_id,
        "method": "learned_meta_judge",
        "final_answer": final_answer,
        "reliability_score": round(reliability_score, 6),
        "risk_level": risk_level,
        "agreement_rate": round(agreement_rate, 6),
        "avg_confidence": round(avg_confidence, 6),
        "evidence_support_score": round(evidence_support_score, 6),
        "answer_diversity": round(answer_diversity, 6),
        "minority_warning": minority_warning,
        "decision_note": note,
        "weighted_agreement": round(weighted_agreement, 6),
        "majority_answer": majority_answer,
        "meta_weights": json_dumps_safe(answer_details.get(final_answer, [])),
    }


def json_dumps_safe(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)
