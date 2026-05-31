from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests

from src.evaluation.metrics import is_correct
from src.llm.clients import PROVIDER_CONFIG, parse_json_from_text


TASK_FACT_QA = "fact_qa"
TASK_CLAIM = "claim_verification"
TASK_CHOICE = "multiple_choice"


TASK_LABELS = {
    TASK_FACT_QA: "Open factual QA",
    TASK_CLAIM: "Claim true / false",
    TASK_CHOICE: "A/B/C/D multiple choice",
}


@dataclass(frozen=True)
class LiveModelConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    enabled: bool = True


def default_live_model_configs() -> Dict[str, Dict[str, str]]:
    configs: Dict[str, Dict[str, str]] = {}
    for provider, cfg in PROVIDER_CONFIG.items():
        if provider == "judge":
            continue
        configs[provider] = {
            "base_url": cfg["default_base_url"],
            "model": cfg["default_model"],
            "api_key": "",
        }
    return configs


def build_live_prompt(task_type: str, question: str, choices: Optional[Dict[str, str]] = None) -> str:
    choices = choices or {}
    choice_text = "\n".join(f"{key}. {value}" for key, value in choices.items() if value.strip())
    if task_type == TASK_CLAIM:
        answer_rule = "Return answer as exactly one of: TRUE, FALSE, UNKNOWN."
    elif task_type == TASK_CHOICE:
        answer_rule = "Return answer as exactly one option letter: A, B, C, or D."
    else:
        answer_rule = "Return the shortest factual answer phrase."

    return f"""You are one independent model in a multi-LLM decision audit.

Task type: {TASK_LABELS.get(task_type, task_type)}

Question or claim:
{question}

Choices, if any:
{choice_text or "N/A"}

Return exactly one JSON object with these keys:
answer, reason, confidence, evidence

Rules:
- {answer_rule}
- confidence must be a number from 0 to 1.
- reason must be concise.
- evidence should be a concrete source cue, quotation cue, known fact, or "unknown".
- Do not include Markdown.
"""


def normalize_live_answer(answer: Any, task_type: str) -> str:
    text = str(answer or "").strip()
    if not text:
        return ""

    if task_type == TASK_CHOICE:
        match = re.search(r"\b([A-D])\b", text.upper())
        return match.group(1) if match else text[:1].upper()

    if task_type == TASK_CLAIM:
        upper = text.upper()
        if upper in {"TRUE", "YES", "SUPPORTED", "SUPPORTS", "CORRECT"}:
            return "TRUE"
        if upper in {"FALSE", "NO", "REFUTED", "REFUTES", "INCORRECT"}:
            return "FALSE"
        if upper in {"UNKNOWN", "UNCERTAIN", "NOT ENOUGH INFO", "NEI", "INSUFFICIENT INFO"}:
            return "UNKNOWN"
        if "NOT ENOUGH" in upper or "INSUFFICIENT" in upper:
            return "UNKNOWN"
        if "FALSE" in upper or "REFUT" in upper:
            return "FALSE"
        if "TRUE" in upper or "SUPPORT" in upper:
            return "TRUE"
        return upper

    normalized = re.sub(r"\s+", " ", text.lower()).strip()
    normalized = normalized.strip(" .。!！?？,，;；:")
    return normalized


def evidence_quality_score(evidence: Any) -> float:
    text = str(evidence or "").strip()
    lowered = text.lower()
    if not text or lowered in {"unknown", "none", "n/a", "na", "null", "无"}:
        return 0.0
    score = 0.35
    if len(text) >= 30:
        score += 0.2
    if re.search(r"https?://|doi\.org|wikipedia|news|journal|paper|dataset|source|according", lowered):
        score += 0.25
    if re.search(r"\d{4}|[A-Z][a-z]+ [A-Z][a-z]+|\".+\"", text):
        score += 0.1
    if lowered in {"common knowledge", "known fact", "public information"}:
        score = min(score, 0.45)
    return round(min(score, 1.0), 3)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, parsed))


def call_live_model(
    config: LiveModelConfig,
    task_type: str,
    question: str,
    choices: Optional[Dict[str, str]] = None,
    temperature: float = 0.2,
    max_tokens: int = 700,
    timeout: int = 60,
) -> Dict[str, Any]:
    started = time.time()
    base = {
        "provider": config.provider,
        "model": config.model,
        "answer": "",
        "normalized_answer": "",
        "reason": "",
        "confidence": 0.0,
        "evidence": "",
        "evidence_quality": 0.0,
        "raw_output": "",
        "parse_error": "",
        "request_error": "",
        "latency_sec": 0.0,
    }
    if not config.enabled:
        return {**base, "request_error": "Model is disabled"}
    if not config.api_key:
        return {**base, "request_error": "Missing API key"}

    prompt = build_live_prompt(task_type, question, choices)
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "You must output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            f"{config.base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        raw = str(response.json()["choices"][0]["message"]["content"])
        parsed = parse_json_from_text(raw)
        parse_error = str(parsed.get("parse_error", "") or "")
        answer = str(parsed.get("answer", "") or "")
        evidence = str(parsed.get("evidence", "") or "")
        return {
            **base,
            "answer": answer,
            "final_answer": str(parsed.get("final_answer", "") or ""),
            "selected_provider": str(parsed.get("selected_provider", "") or ""),
            "risk_level": str(parsed.get("risk_level", "") or ""),
            "decision_reason": str(parsed.get("decision_reason", "") or ""),
            "normalized_answer": normalize_live_answer(answer, task_type),
            "reason": str(parsed.get("reason", "") or ""),
            "confidence": safe_float(parsed.get("confidence", 0.0)),
            "evidence": evidence,
            "evidence_quality": evidence_quality_score(evidence),
            "raw_output": raw,
            "parse_error": parse_error,
            "latency_sec": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            **base,
            "request_error": str(exc),
            "latency_sec": round(time.time() - started, 3),
        }


def run_live_models(
    configs: Iterable[LiveModelConfig],
    task_type: str,
    question: str,
    choices: Optional[Dict[str, str]] = None,
    temperature: float = 0.2,
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    enabled = [cfg for cfg in configs if cfg.enabled]
    if not enabled:
        return []
    workers = max(1, min(max_workers, len(enabled)))
    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(call_live_model, cfg, task_type, question, choices, temperature)
            for cfg in enabled
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: str(item.get("provider", "")))


def majority_vote_live(outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid = [item for item in outputs if item.get("normalized_answer") and not item.get("request_error") and not item.get("parse_error")]
    counts = Counter(str(item.get("normalized_answer", "")) for item in valid)
    if not counts:
        return {
            "method": "majority_vote",
            "final_answer": "",
            "agreement_rate": 0.0,
            "risk_level": "high",
            "vote_distribution": {},
            "decision_note": "No valid model answer.",
        }
    top_answer, top_count = counts.most_common(1)[0]
    tied = sum(1 for count in counts.values() if count == top_count) > 1
    agreement_rate = top_count / len(valid)
    return {
        "method": "majority_vote",
        "final_answer": "" if tied else top_answer,
        "agreement_rate": round(agreement_rate, 3),
        "risk_level": "high" if tied else "low" if agreement_rate >= 0.75 else "medium" if agreement_rate >= 0.5 else "high",
        "vote_distribution": dict(counts),
        "decision_note": "Tie among top answers; route to human review." if tied else "Adopt the unique top-voted answer.",
    }


def fixed_judge_live(
    outputs: List[Dict[str, Any]],
    judge_config: Optional[LiveModelConfig] = None,
    task_type: str = TASK_FACT_QA,
    question: str = "",
    choices: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Fixed judge for live comparison.

    If a judge configuration with an API key is supplied, call that fixed
    model. Otherwise fall back to a deterministic fixed baseline: first valid
    model in provider order. This keeps the live demo usable without embedding
    secrets in code.
    """

    valid = [item for item in outputs if item.get("normalized_answer") and not item.get("request_error") and not item.get("parse_error")]
    if not valid:
        return {
            "method": "fixed_judge",
            "final_answer": "",
            "risk_level": "high",
            "confidence": 0.0,
            "selected_provider": "",
            "explanation": "No valid model answer was available.",
        }

    if judge_config and judge_config.enabled and judge_config.api_key:
        candidates = [
            {
                "provider": item.get("provider", ""),
                "model": item.get("model", ""),
                "answer": item.get("normalized_answer", item.get("answer", "")),
                "reason": item.get("reason", ""),
                "confidence": item.get("confidence", 0.0),
                "evidence": item.get("evidence", ""),
                "evidence_quality": item.get("evidence_quality", 0.0),
            }
            for item in valid
        ]
        prompt = f"""You are the fixed judge model in a multi-LLM audit.

Task type: {TASK_LABELS.get(task_type, task_type)}
Question: {question}
Choices: {json.dumps(choices or {}, ensure_ascii=False)}

Candidate model answers:
{json.dumps(candidates, ensure_ascii=False, indent=2)}

Return exactly one JSON object:
final_answer, selected_provider, confidence, risk_level, decision_reason

The final_answer must match one candidate answer exactly.
risk_level must be low, medium, or high.
"""
        result = call_live_model(
            judge_config,
            task_type=task_type,
            question=prompt,
            choices=None,
            temperature=0.0,
            max_tokens=800,
        )
        final_answer = normalize_live_answer(result.get("answer", ""), task_type)
        if not final_answer:
            final_answer = normalize_live_answer(result.get("final_answer", ""), task_type)
        if final_answer:
            return {
                "method": "fixed_judge",
                "final_answer": final_answer,
                "risk_level": str(result.get("risk_level", "medium") or "medium").lower(),
                "confidence": safe_float(result.get("confidence", 0.0)),
                "selected_provider": str(result.get("selected_provider", judge_config.provider) or judge_config.provider),
                "explanation": str(result.get("decision_reason", "") or "Fixed judge model selected this answer."),
            }

    provider_order = {name: idx for idx, name in enumerate(PROVIDER_CONFIG.keys())}
    selected = sorted(valid, key=lambda item: provider_order.get(str(item.get("provider", "")), 999))[0]
    return {
        "method": "fixed_judge",
        "final_answer": str(selected.get("normalized_answer", "")),
        "risk_level": "medium",
        "confidence": safe_float(selected.get("confidence", 0.0)),
        "selected_provider": str(selected.get("provider", "")),
        "explanation": "Fixed baseline selected the first valid configured model; enable a judge API key for a true fixed judge call.",
    }


def load_historical_reliability(samples_path: str, outputs_path: str) -> Dict[str, float]:
    try:
        samples = pd.read_csv(samples_path)
        outputs = pd.read_csv(outputs_path)
    except Exception:
        return {}
    if samples.empty or outputs.empty:
        return {}

    sample_map = samples.set_index("id").to_dict(orient="index")
    stats: Dict[str, List[int]] = defaultdict(list)
    for _, row in outputs.iterrows():
        sample = sample_map.get(str(row.get("sample_id", "")))
        if not sample:
            continue
        provider = str(row.get("model", row.get("provider", "")) or "").strip()
        if not provider:
            continue
        correct = is_correct(row.get("answer", ""), sample.get("gold_answer", ""), sample.get("gold_label", ""))
        stats[provider].append(1 if correct else 0)
    reliabilities: Dict[str, float] = {}
    for provider, values in stats.items():
        if values:
            # Mild smoothing prevents over-trusting tiny samples.
            reliabilities[provider] = round((sum(values) + 1) / (len(values) + 2), 3)
    return reliabilities


def dynamic_adjudicate_live(
    task_type: str,
    outputs: List[Dict[str, Any]],
    historical_reliability: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    historical_reliability = historical_reliability or {}
    valid = [item for item in outputs if item.get("normalized_answer") and not item.get("request_error") and not item.get("parse_error")]
    if not valid:
        return {
            "method": "dynamic_adjudication",
            "final_answer": "",
            "risk_level": "high",
            "reliability_score": 0.0,
            "agreement_rate": 0.0,
            "evidence_quality": 0.0,
            "minority_signal": False,
            "weighted_distribution": {},
            "explanation": "No valid model answer was available.",
        }

    majority = majority_vote_live(valid)
    total = len(valid)
    vote_counts = Counter(str(item["normalized_answer"]) for item in valid)
    majority_answer = vote_counts.most_common(1)[0][0]
    agreement_rate = vote_counts[majority_answer] / total

    weighted: Dict[str, float] = defaultdict(float)
    details = []
    for item in valid:
        answer = str(item["normalized_answer"])
        provider = str(item.get("provider", ""))
        model = str(item.get("model", ""))
        history = historical_reliability.get(provider)
        if history is None:
            history = historical_reliability.get(model, 0.55)
        confidence = safe_float(item.get("confidence", 0.0))
        evidence = safe_float(item.get("evidence_quality", 0.0))
        weight = 0.45 * history + 0.30 * confidence + 0.25 * evidence
        weighted[answer] += weight
        details.append(
            {
                "provider": provider,
                "answer": answer,
                "history": round(history, 3),
                "confidence": round(confidence, 3),
                "evidence": round(evidence, 3),
                "weight": round(weight, 3),
            }
        )

    ranked = sorted(weighted.items(), key=lambda pair: pair[1], reverse=True)
    final_answer, top_weight = ranked[0]
    second_weight = ranked[1][1] if len(ranked) > 1 else 0.0
    total_weight = sum(weighted.values()) or 1.0
    weighted_agreement = top_weight / total_weight
    margin = (top_weight - second_weight) / total_weight

    top_group = [item for item in valid if item.get("normalized_answer") == final_answer]
    minority_group = [item for item in valid if item.get("normalized_answer") != final_answer]
    evidence_avg = sum(safe_float(item.get("evidence_quality", 0.0)) for item in top_group) / len(top_group)
    confidence_avg = sum(safe_float(item.get("confidence", 0.0)) for item in top_group) / len(top_group)
    minority_signal = any(
        safe_float(item.get("confidence", 0.0)) >= max(0.7, confidence_avg - 0.05)
        and safe_float(item.get("evidence_quality", 0.0)) >= max(0.45, evidence_avg - 0.05)
        for item in minority_group
    )

    reliability_score = (
        0.30 * weighted_agreement
        + 0.22 * agreement_rate
        + 0.18 * evidence_avg
        + 0.15 * confidence_avg
        + 0.15 * margin
    )
    if minority_signal:
        reliability_score -= 0.12
    if task_type == TASK_FACT_QA and agreement_rate < 0.5:
        reliability_score -= 0.08
    reliability_score = round(max(0.0, min(1.0, reliability_score)), 3)

    if reliability_score >= 0.72 and not minority_signal:
        risk_level = "low"
    elif reliability_score >= 0.48:
        risk_level = "medium"
    else:
        risk_level = "high"

    if majority.get("final_answer") and majority.get("final_answer") != final_answer:
        explanation = (
            "Dynamic adjudication overrode plain majority vote because weighted reliability, "
            "confidence, and evidence favored a different answer."
        )
    elif minority_signal:
        explanation = (
            "Dynamic adjudication selected the leading answer but raised a minority warning "
            "because a dissenting answer has strong confidence/evidence signals."
        )
    else:
        explanation = (
            "Dynamic adjudication selected the leading answer using agreement, confidence, "
            "evidence quality, and historical model reliability."
        )

    return {
        "method": "dynamic_adjudication",
        "final_answer": final_answer,
        "risk_level": risk_level,
        "reliability_score": reliability_score,
        "agreement_rate": round(agreement_rate, 3),
        "weighted_agreement": round(weighted_agreement, 3),
        "evidence_quality": round(evidence_avg, 3),
        "confidence": round(confidence_avg, 3),
        "minority_signal": minority_signal,
        "majority_answer": majority.get("final_answer", ""),
        "weighted_distribution": {key: round(value, 3) for key, value in ranked},
        "model_weight_details": details,
        "explanation": explanation,
    }


def learned_meta_judge_live(
    task_type: str,
    outputs: List[Dict[str, Any]],
    historical_reliability: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Learned Meta-Judge for live mode."""

    historical_reliability = historical_reliability or {}
    valid = [item for item in outputs if item.get("normalized_answer") and not item.get("request_error") and not item.get("parse_error")]
    if not valid:
        return {
            "method": "learned_meta_judge",
            "final_answer": "",
            "risk_level": "high",
            "reliability_score": 0.0,
            "agreement_rate": 0.0,
            "weighted_distribution": {},
            "explanation": "No valid model answer was available.",
        }

    majority = majority_vote_live(valid)
    counts = Counter(str(item["normalized_answer"]) for item in valid)
    total = len(valid)
    weighted: Dict[str, float] = defaultdict(float)
    details: List[Dict[str, Any]] = []
    for item in valid:
        answer = str(item["normalized_answer"])
        provider = str(item.get("provider", ""))
        model = str(item.get("model", ""))
        history = historical_reliability.get(provider, historical_reliability.get(model, 0.50))
        confidence = safe_float(item.get("confidence", 0.0))
        evidence = safe_float(item.get("evidence_quality", 0.0))
        support = counts[answer] / total
        weight = 0.62 * history + 0.16 * confidence + 0.14 * evidence + 0.08 * support
        weighted[answer] += weight
        details.append(
            {
                "provider": provider,
                "answer": answer,
                "history": round(history, 3),
                "confidence": round(confidence, 3),
                "evidence": round(evidence, 3),
                "support": round(support, 3),
                "weight": round(weight, 3),
            }
        )

    ranked = sorted(weighted.items(), key=lambda pair: pair[1], reverse=True)
    final_answer, top_weight = ranked[0]
    second_weight = ranked[1][1] if len(ranked) > 1 else 0.0
    total_weight = sum(weighted.values()) or 1.0
    weighted_agreement = top_weight / total_weight
    margin = (top_weight - second_weight) / total_weight
    agreement_rate = counts[final_answer] / total
    top_group = [item for item in valid if item["normalized_answer"] == final_answer]
    evidence_avg = sum(safe_float(item.get("evidence_quality", 0.0)) for item in top_group) / len(top_group)
    confidence_avg = sum(safe_float(item.get("confidence", 0.0)) for item in top_group) / len(top_group)
    majority_answer = majority.get("final_answer", "")

    reliability_score = (
        0.34 * weighted_agreement
        + 0.18 * agreement_rate
        + 0.18 * evidence_avg
        + 0.15 * confidence_avg
        + 0.15 * max(0.0, margin)
    )
    if majority_answer and majority_answer != final_answer:
        reliability_score -= 0.04
    if task_type == TASK_FACT_QA and agreement_rate < 0.5:
        reliability_score -= 0.05
    reliability_score = round(max(0.0, min(1.0, reliability_score)), 3)

    if reliability_score >= 0.72 and majority_answer == final_answer:
        risk_level = "low"
    elif reliability_score >= 0.48:
        risk_level = "medium"
    else:
        risk_level = "high"

    if majority_answer and majority_answer != final_answer:
        explanation = "Learned Meta-Judge overrode majority/fixed style selection because calibrated model reliability and evidence favored another answer."
    else:
        explanation = "Learned Meta-Judge selected the answer using calibrated model reliability, evidence quality, confidence, and support."

    return {
        "method": "learned_meta_judge",
        "final_answer": final_answer,
        "risk_level": risk_level,
        "reliability_score": reliability_score,
        "agreement_rate": round(agreement_rate, 3),
        "weighted_agreement": round(weighted_agreement, 3),
        "evidence_quality": round(evidence_avg, 3),
        "confidence": round(confidence_avg, 3),
        "majority_answer": majority_answer,
        "weighted_distribution": {key: round(value, 3) for key, value in ranked},
        "model_weight_details": details,
        "explanation": explanation,
    }


def adjudication_comparison_live(
    task_type: str,
    question: str,
    choices: Optional[Dict[str, str]],
    outputs: List[Dict[str, Any]],
    historical_reliability: Optional[Dict[str, float]] = None,
    fixed_judge_config: Optional[LiveModelConfig] = None,
) -> Dict[str, Any]:
    majority = majority_vote_live(outputs)
    fixed = fixed_judge_live(outputs, fixed_judge_config, task_type, question, choices)
    rule_based = dynamic_adjudicate_live(task_type, outputs, historical_reliability)
    methods = [
        {**majority, "label": "Majority Vote"},
        {**fixed, "label": "Fixed Judge"},
        {**rule_based, "label": "Dynamic Rule-Based Judge"},
    ]
    return {
        "methods": methods,
        "final": rule_based,
        "comparison": [
            {
                "method": item.get("label", item.get("method", "")),
                "final_answer": item.get("final_answer", ""),
                "risk_level": item.get("risk_level", ""),
                "score": item.get("reliability_score", item.get("confidence", item.get("agreement_rate", 0.0))),
            }
            for item in methods
        ],
    }


def build_live_report(
    task_type: str,
    question: str,
    choices: Optional[Dict[str, str]],
    outputs: List[Dict[str, Any]],
    majority: Dict[str, Any],
    dynamic: Dict[str, Any],
    fixed: Optional[Dict[str, Any]] = None,
    learned: Optional[Dict[str, Any]] = None,
) -> str:
    lines = [
        "# ConsensusScope Live Question Report",
        "",
        f"- Task type: {TASK_LABELS.get(task_type, task_type)}",
        f"- Question: {question}",
    ]
    if choices:
        lines.append("- Choices:")
        for key, value in choices.items():
            if value.strip():
                lines.append(f"  - {key}. {value}")
    lines.extend(
        [
            "",
            "## Final Decision",
            "",
            f"- Dynamic rule-based answer: {dynamic.get('final_answer', '')}",
            f"- Risk level: {dynamic.get('risk_level', '')}",
            f"- Reliability score: {dynamic.get('reliability_score', '')}",
            f"- Explanation: {dynamic.get('explanation', '')}",
            "",
            "## Baseline Comparison",
            "",
            f"- Majority vote answer: {majority.get('final_answer', '')}",
            f"- Majority agreement: {majority.get('agreement_rate', '')}",
            f"- Vote distribution: `{json.dumps(majority.get('vote_distribution', {}), ensure_ascii=False)}`",
            f"- Fixed judge answer: {(fixed or {}).get('final_answer', '')}",
            f"- Dynamic answer: {dynamic.get('final_answer', '')}",
            f"- Dynamic rule-based answer: {dynamic.get('final_answer', '')}",
            "",
            "## Model Outputs",
            "",
        ]
    )
    for item in outputs:
        lines.extend(
            [
                f"### {item.get('provider', '')} / {item.get('model', '')}",
                "",
                f"- Answer: {item.get('answer', '')}",
                f"- Normalized answer: {item.get('normalized_answer', '')}",
                f"- Confidence: {item.get('confidence', '')}",
                f"- Evidence quality: {item.get('evidence_quality', '')}",
                f"- Evidence: {item.get('evidence', '')}",
                f"- Reason: {item.get('reason', '')}",
                f"- Request error: {item.get('request_error', '')}",
                f"- Parse error: {item.get('parse_error', '')}",
                "",
            ]
        )
    return "\n".join(lines)
