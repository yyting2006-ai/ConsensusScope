from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = ROOT / "profiles" / "esl_writing.yaml"

LOW_RISK_ISSUES = {"grammar", "spelling", "punctuation", "vocabulary", "word_choice"}
MEDIUM_RISK_ISSUES = {"sentence_structure", "coherence", "organization", "argument_clarity", "tone_register"}
HIGH_RISK_ISSUES = {"meaning_change", "overcorrection", "task_response", "unsupported_claim", "wrong_correction"}
LOCAL_EDIT_HINTS = {
    "change",
    "correct",
    "replace",
    "more natural",
    "more concise",
    "subject-verb",
    "punctuation",
    "wording",
    "vocabulary",
}
MEANING_CHANGE_HINTS = {
    "end online learning",
    "always harmful",
    "should be banned",
    "exam scores",
    "closed immediately",
    "stronger position",
    "more decisive",
    "new argument",
    "rewrite the thesis",
    "reverses",
}
UNSUPPORTED_HINTS = {"add a claim", "not present", "unsupported", "new argument", "factories should be closed"}
VAGUE_HINTS = {"improve", "add evidence", "add a short explanation", "add a transition", "clearer", "more persuasive"}
WHOLE_REWRITE_HINTS = {
    "rewrite the whole essay",
    "rewrite the entire essay",
    "replace the whole draft",
    "write a new essay",
    "change the whole paragraph",
}
HARSH_FEEDBACK_HINTS = {
    "terrible",
    "nonsense",
    "lazy",
    "weak student",
    "bad writer",
    "unacceptable",
    "obviously wrong",
}
EXTERNAL_CLAIM_HINTS = {
    "add a statistic",
    "add statistics",
    "research shows",
    "studies show",
    "according to experts",
    "exam scores",
    "survey data",
    "citation",
    "source",
}
ABSOLUTE_REVISION_HINTS = {"always", "never", "must be banned", "should be banned", "completely wrong"}
BROAD_TARGET_HINTS = {"overall draft", "whole essay", "entire essay", "supporting evidence", "overall paragraph structure"}
DEFAULT_ASSIGNMENT = "Write a clear ESL essay that responds to the prompt with organized reasons and examples."

SAFETY_GRAPH_DIMENSIONS = {
    "local_edit": {
        "label": "Local language edit",
        "reasons": {"local_language_edit"},
        "severity": "low",
    },
    "meaning_preservation": {
        "label": "Meaning preservation",
        "reasons": {"meaning_change", "overcorrection", "introduces_new_argument"},
        "severity": "high",
    },
    "content_grounding": {
        "label": "Content grounding",
        "reasons": {"unsupported_claim", "task_mismatch"},
        "severity": "high",
    },
    "pedagogical_tone": {
        "label": "Pedagogical tone",
        "reasons": {"too_harsh"},
        "severity": "high",
    },
    "specificity": {
        "label": "Feedback specificity",
        "reasons": {"too_vague", "parse_error"},
        "severity": "medium",
    },
    "model_agreement": {
        "label": "Reviewer agreement",
        "reasons": {"low_model_agreement"},
        "severity": "medium",
    },
}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value).lower()).strip(" .,:;!?")


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = _norm(text)
    for phrase in phrases:
        normalized_phrase = _norm(phrase)
        if normalized_phrase and re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", lowered):
            return True
    return False


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return max(0.0, min(1.0, parsed))


def load_esl_writing_profile(path: str | Path | None = None) -> Dict[str, Any]:
    """Load the ESL writing feedback profile used by the demo pipeline."""
    profile_path = Path(path) if path else DEFAULT_PROFILE_PATH
    with profile_path.open("r", encoding="utf-8") as handle:
        profile = yaml.safe_load(handle) or {}
    return dict(profile)


def _evidence_rows(review_evidence: Any) -> List[Mapping[str, Any]]:
    if review_evidence is None:
        return []
    if isinstance(review_evidence, pd.DataFrame):
        return [row.to_dict() for _, row in review_evidence.iterrows()]
    if isinstance(review_evidence, Mapping):
        return [review_evidence]
    if isinstance(review_evidence, Sequence) and not isinstance(review_evidence, str):
        return [row for row in review_evidence if isinstance(row, Mapping)]
    return []


def _evidence_statuses(review_evidence: Any) -> set[str]:
    statuses: set[str] = set()
    for row in _evidence_rows(review_evidence):
        status = _norm(row.get("match_status"))
        if status:
            statuses.add(status)
    return statuses


def _evidence_text(review_evidence: Any) -> str:
    texts: List[str] = []
    for row in _evidence_rows(review_evidence):
        texts.append(_safe_text(row.get("evidence_text")))
        texts.append(_safe_text(row.get("criterion")))
        texts.append(_safe_text(row.get("match_status")))
    return " ".join(text for text in texts if text)


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _status_for_action(action: str) -> str:
    return "auto_accepted" if action == "auto_accept" else "needs_teacher_review"


def extract_review_signals(
    issue_type_predicted: str,
    ai_suggestion: str = "",
    target_span: str = "",
    surrounding_context: str = "",
    model_agreement: float | None = None,
    review_evidence: Any = None,
) -> Dict[str, Any]:
    """Extract deploy-time review signals for one AI feedback item.

    These signals are intentionally observable at review time. They do not use
    gold labels, hidden teacher decisions, or post-hoc classroom outcomes.
    """
    issue = _norm(issue_type_predicted).replace("-", "_").replace(" ", "_")
    suggestion_blob = " ".join([ai_suggestion, target_span, surrounding_context, _evidence_text(review_evidence)])
    statuses = _evidence_statuses(review_evidence)
    agreement = _as_float(model_agreement)
    target_norm = _norm(target_span)

    low_issue = issue in LOW_RISK_ISSUES
    medium_issue = issue in MEDIUM_RISK_ISSUES
    high_issue = issue in HIGH_RISK_ISSUES
    parse_error = not issue or issue in {"other", "unknown", "parse_error"}
    conflict_evidence = "conflict" in statuses
    missing_evidence = "missing" in statuses
    supported_evidence = "supported" in statuses
    meaning_hint = _contains_any(suggestion_blob, MEANING_CHANGE_HINTS)
    unsupported_hint = _contains_any(suggestion_blob, UNSUPPORTED_HINTS) or _contains_any(
        suggestion_blob, EXTERNAL_CLAIM_HINTS
    )
    whole_rewrite = _contains_any(suggestion_blob, WHOLE_REWRITE_HINTS)
    harsh_feedback = _contains_any(suggestion_blob, HARSH_FEEDBACK_HINTS)
    vague_feedback = _contains_any(suggestion_blob, VAGUE_HINTS) or (
        len(_safe_text(ai_suggestion).split()) <= 4 and not low_issue
    )
    absolute_revision = _contains_any(suggestion_blob, ABSOLUTE_REVISION_HINTS)
    broad_target = target_norm in BROAD_TARGET_HINTS or _contains_any(target_span, BROAD_TARGET_HINTS)
    low_agreement = agreement is not None and agreement < 0.5
    introduces_new_argument = _contains_any(
        suggestion_blob,
        {
            "new argument",
            "rewrite the thesis",
            "opposite position",
            "exam scores",
            "closed immediately",
            "make the essay stronger",
        },
    )

    score = 0.08
    if low_issue:
        score += 0.02
    if medium_issue:
        score += 0.24
    if high_issue:
        score += 0.44
    if parse_error:
        score += 0.34
    if conflict_evidence:
        score += 0.34
    if missing_evidence:
        score += 0.24
    if meaning_hint:
        score += 0.26
    if unsupported_hint:
        score += 0.25
    if whole_rewrite:
        score += 0.32
    if harsh_feedback:
        score += 0.28
    if absolute_revision:
        score += 0.22
    if introduces_new_argument:
        score += 0.18
    if vague_feedback:
        score += 0.12
    if broad_target:
        score += 0.10
    if low_agreement:
        score += 0.22
    if low_issue and supported_evidence and not low_agreement:
        score -= 0.08

    evidence_signal = "none"
    if conflict_evidence:
        evidence_signal = "conflict"
    elif missing_evidence:
        evidence_signal = "missing"
    elif supported_evidence:
        evidence_signal = "supported"

    return {
        "issue": issue,
        "agreement": agreement,
        "evidence_signal": evidence_signal,
        "low_issue": low_issue,
        "medium_issue": medium_issue,
        "high_issue": high_issue,
        "parse_error": parse_error,
        "conflict_evidence": conflict_evidence,
        "missing_evidence": missing_evidence,
        "supported_evidence": supported_evidence,
        "meaning_hint": meaning_hint,
        "unsupported_hint": unsupported_hint,
        "whole_rewrite": whole_rewrite,
        "harsh_feedback": harsh_feedback,
        "vague_feedback": vague_feedback,
        "absolute_revision": absolute_revision,
        "broad_target": broad_target,
        "low_agreement": low_agreement,
        "introduces_new_argument": introduces_new_argument,
        "risk_score": round(_clamp(score), 3),
    }


def _risk_reasons_from_signals(signals: Mapping[str, Any]) -> List[str]:
    reasons: List[str] = []
    issue = _safe_text(signals.get("issue"))
    if signals.get("parse_error"):
        reasons.append("parse_error" if issue == "parse_error" else "too_vague")
    if signals.get("low_agreement"):
        reasons.append("low_model_agreement")
    if signals.get("low_issue"):
        reasons.append("local_language_edit")
    if signals.get("meaning_hint") or signals.get("conflict_evidence") or issue in {"meaning_change", "wrong_correction"}:
        reasons.append("meaning_change")
    if signals.get("absolute_revision") or issue == "overcorrection":
        reasons.append("overcorrection")
    if signals.get("whole_rewrite"):
        reasons.append("overcorrection")
        reasons.append("meaning_change")
    if signals.get("unsupported_hint") or signals.get("missing_evidence") or issue in {"task_response", "unsupported_claim"}:
        reasons.append("unsupported_claim")
    if signals.get("introduces_new_argument"):
        reasons.append("introduces_new_argument")
    if signals.get("harsh_feedback"):
        reasons.append("too_harsh")
    if signals.get("vague_feedback") or signals.get("broad_target") or signals.get("medium_issue"):
        reasons.append("too_vague")
    if issue in {"task_response", "organization", "tone_register"} and not signals.get("low_issue"):
        reasons.append("task_mismatch")
    return _dedupe(reasons)


def _json_for_csv(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _active_safety_dimensions(reasons: Sequence[str], signals: Mapping[str, Any]) -> List[Dict[str, str]]:
    reason_set = set(reasons)
    active: List[Dict[str, str]] = []
    for dimension, spec in SAFETY_GRAPH_DIMENSIONS.items():
        matched = sorted(reason_set.intersection(spec["reasons"]))
        if matched:
            active.append(
                {
                    "dimension": dimension,
                    "label": str(spec["label"]),
                    "severity": str(spec["severity"]),
                    "signals": ",".join(matched),
                }
            )
    if not active and signals.get("low_issue"):
        spec = SAFETY_GRAPH_DIMENSIONS["local_edit"]
        active.append(
            {
                "dimension": "local_edit",
                "label": str(spec["label"]),
                "severity": str(spec["severity"]),
                "signals": "local_language_edit",
            }
        )
    return active


def build_feedback_safety_graph(
    *,
    feedback_item_id: str = "",
    issue_type_predicted: str = "",
    ai_suggestion: str = "",
    ai_rationale: str = "",
    target_span: str = "",
    surrounding_context: str = "",
    signals: Mapping[str, Any],
    reasons: Sequence[str],
    risk_level: str,
    recommended_action: str,
    meaning_preservation_predicted: str,
    evidence_signal: str,
    risk_score: float,
) -> Dict[str, Any]:
    """Build an item-level Feedback Safety Graph for audit and UI display.

    The graph is deliberately small and deploy-time only. Nodes represent the
    observed feedback item, rubric/safety dimensions, evidence status, and the
    route. Edges show which observed signals activated the route. No gold label
    or teacher annotation is used to construct the graph.
    """
    item_id = _safe_text(feedback_item_id) or "feedback_item"
    active_dimensions = _active_safety_dimensions(reasons, signals)
    dimension_names = [item["dimension"] for item in active_dimensions]
    active_signal_text = ";".join(_dedupe(reason for reason in reasons if reason != "local_language_edit"))
    if not active_signal_text and "local_language_edit" in reasons:
        active_signal_text = "local_language_edit"

    nodes: List[Dict[str, Any]] = [
        {
            "id": f"{item_id}:target_span",
            "type": "student_text",
            "label": "Target span",
            "value": _safe_text(target_span),
        },
        {
            "id": f"{item_id}:context",
            "type": "student_text",
            "label": "Surrounding context",
            "value": _safe_text(surrounding_context)[:260],
        },
        {
            "id": f"{item_id}:suggestion",
            "type": "ai_feedback",
            "label": "AI suggestion",
            "value": _safe_text(ai_suggestion),
        },
        {
            "id": f"{item_id}:issue",
            "type": "rubric",
            "label": "Predicted issue type",
            "value": _safe_text(issue_type_predicted),
        },
        {
            "id": f"{item_id}:evidence",
            "type": "evidence_status",
            "label": "Evidence signal",
            "value": evidence_signal or "none",
        },
        {
            "id": f"{item_id}:route",
            "type": "routing_decision",
            "label": "Routing decision",
            "value": recommended_action,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "meaning_preservation_predicted": meaning_preservation_predicted,
        },
    ]
    if _safe_text(ai_rationale):
        nodes.insert(
            3,
            {
                "id": f"{item_id}:rationale",
                "type": "ai_feedback",
                "label": "AI rationale",
                "value": _safe_text(ai_rationale),
            },
        )

    for dimension in active_dimensions:
        nodes.append(
            {
                "id": f"{item_id}:dimension:{dimension['dimension']}",
                "type": "safety_dimension",
                "label": dimension["label"],
                "severity": dimension["severity"],
                "active_signals": dimension["signals"],
            }
        )

    edges: List[Dict[str, str]] = [
        {"source": f"{item_id}:context", "target": f"{item_id}:target_span", "relation": "contains"},
        {"source": f"{item_id}:target_span", "target": f"{item_id}:suggestion", "relation": "is_revised_by"},
        {"source": f"{item_id}:issue", "target": f"{item_id}:route", "relation": "informs_route"},
        {"source": f"{item_id}:evidence", "target": f"{item_id}:route", "relation": "informs_route"},
    ]
    if _safe_text(ai_rationale):
        edges.append({"source": f"{item_id}:rationale", "target": f"{item_id}:suggestion", "relation": "explains"})
    for dimension in active_dimensions:
        dimension_id = f"{item_id}:dimension:{dimension['dimension']}"
        edges.append({"source": f"{item_id}:suggestion", "target": dimension_id, "relation": "activates"})
        edges.append({"source": dimension_id, "target": f"{item_id}:route", "relation": "justifies_route"})

    if active_dimensions:
        primary_dimension = sorted(
            active_dimensions,
            key=lambda item: {"high": 3, "medium": 2, "low": 1}.get(item["severity"], 0),
            reverse=True,
        )[0]["dimension"]
    else:
        primary_dimension = "no_active_risk"
    path = f"target_span -> ai_suggestion -> {primary_dimension} -> {recommended_action}"
    summary = (
        f"Feedback Safety Graph activates {', '.join(dimension_names) if dimension_names else 'no active safety dimension'}; "
        f"meaning={meaning_preservation_predicted}; evidence={evidence_signal}; route={recommended_action}."
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "active_dimensions": dimension_names,
        "active_signals": active_signal_text,
        "path": path,
        "summary": summary,
    }


def _confidence_from_signals(signals: Mapping[str, Any], risk_level: str) -> float:
    score = float(signals.get("risk_score") or 0.0)
    confidence = 0.62
    if signals.get("low_issue") or signals.get("medium_issue") or signals.get("high_issue"):
        confidence += 0.08
    if signals.get("conflict_evidence") or signals.get("missing_evidence") or signals.get("supported_evidence"):
        confidence += 0.08
    if signals.get("agreement") is not None and float(signals.get("agreement") or 0.0) >= 0.7:
        confidence += 0.05
    if signals.get("low_agreement") or signals.get("parse_error"):
        confidence -= 0.10
    if risk_level == "high" and score >= 0.85:
        confidence += 0.08
    if risk_level == "low" and score <= 0.18:
        confidence += 0.07
    return round(_clamp(confidence, 0.42, 0.95), 3)


def _priority_from_score(risk_level: str, risk_score: float, recommended_action: str) -> str:
    if recommended_action == "auto_accept":
        return "low"
    if risk_level == "high" and risk_score >= 0.85:
        return "urgent"
    if risk_level == "high":
        return "high"
    return "normal"


def _explanation_from_route(
    risk_level: str,
    recommended_action: str,
    reasons: Sequence[str],
    evidence_signal: str,
    risk_score: float,
) -> str:
    reason_text = ", ".join(reasons)
    if recommended_action == "auto_accept":
        return f"Low-risk local edit; evidence={evidence_signal}; risk_score={risk_score:.3f}; reasons={reason_text}."
    if recommended_action == "needs_more_evidence":
        return f"More evidence is required before student-facing use; evidence={evidence_signal}; risk_score={risk_score:.3f}; reasons={reason_text}."
    return f"{risk_level.title()}-risk feedback is routed to teacher review; evidence={evidence_signal}; risk_score={risk_score:.3f}; reasons={reason_text}."


def rule_based_route(
    issue_type_predicted: str,
    ai_suggestion: str = "",
    ai_rationale: str = "",
    target_span: str = "",
    surrounding_context: str = "",
    model_agreement: float | None = None,
    review_evidence: Any = None,
    feedback_item_id: str = "",
) -> Dict[str, Any]:
    """Route an AI feedback item with a deploy-time Feedback Safety Graph.

    The function uses deploy-time signals only: issue type, suggestion text,
    local context, model agreement, parse/evidence status, and rubric/safety
    evidence. It does not use gold labels or teacher decisions. The returned
    safety graph makes the route auditable by linking the target span,
    suggestion, active safety dimensions, evidence signal, and final route.
    """
    signals = extract_review_signals(
        issue_type_predicted=issue_type_predicted,
        ai_suggestion=ai_suggestion,
        target_span=target_span,
        surrounding_context=surrounding_context,
        model_agreement=model_agreement,
        review_evidence=review_evidence,
    )
    risk_score = float(signals["risk_score"])
    reasons = _risk_reasons_from_signals(signals)
    evidence_signal = _safe_text(signals.get("evidence_signal"))

    if signals.get("parse_error"):
        risk_level = "medium"
        recommended_action = "needs_more_evidence"
        meaning = "unclear"
    elif risk_score >= 0.72:
        risk_level = "high"
        recommended_action = "teacher_review"
        meaning = "changes_meaning" if any(
            reason in reasons
            for reason in ["meaning_change", "overcorrection", "introduces_new_argument", "unsupported_claim"]
        ) else "unclear"
    elif risk_score >= 0.32:
        risk_level = "medium"
        recommended_action = "teacher_review"
        meaning = "unclear"
    else:
        risk_level = "low"
        recommended_action = "auto_accept"
        meaning = "preserves_meaning"

    status = _status_for_action(recommended_action)
    review_confidence = _confidence_from_signals(signals, risk_level)
    review_priority = _priority_from_score(risk_level, risk_score, recommended_action)
    explanation = _explanation_from_route(risk_level, recommended_action, reasons, evidence_signal, risk_score)
    graph = build_feedback_safety_graph(
        feedback_item_id=feedback_item_id,
        issue_type_predicted=issue_type_predicted,
        ai_suggestion=ai_suggestion,
        ai_rationale=ai_rationale,
        target_span=target_span,
        surrounding_context=surrounding_context,
        signals=signals,
        reasons=reasons,
        risk_level=risk_level,
        recommended_action=recommended_action,
        meaning_preservation_predicted=meaning,
        evidence_signal=evidence_signal,
        risk_score=risk_score,
    )

    return {
        "risk_level": risk_level,
        "recommended_action": recommended_action,
        "risk_reasons": reasons,
        "meaning_preservation_predicted": meaning,
        "status": status,
        "risk_score": risk_score,
        "review_confidence": review_confidence,
        "evidence_signal": evidence_signal,
        "review_priority": review_priority,
        "review_explanation": explanation,
        "safety_graph_active_dimensions": ";".join(graph["active_dimensions"]),
        "safety_graph_active_signals": graph["active_signals"],
        "safety_graph_path": graph["path"],
        "safety_graph_summary": graph["summary"],
        "safety_graph_nodes": _json_for_csv(graph["nodes"]),
        "safety_graph_edges": _json_for_csv(graph["edges"]),
    }


def _dedupe(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out or ["too_vague"]


def route_feedback_item(item: Mapping[str, Any], evidence_rows: Any = None) -> Dict[str, Any]:
    route = rule_based_route(
        issue_type_predicted=_safe_text(item.get("issue_type_predicted") or item.get("issue_type")),
        ai_suggestion=_safe_text(item.get("ai_suggestion") or item.get("suggestion")),
        ai_rationale=_safe_text(item.get("ai_rationale") or item.get("rationale")),
        target_span=_safe_text(item.get("target_span")),
        surrounding_context=_safe_text(item.get("surrounding_context")),
        model_agreement=_as_float(item.get("model_agreement")),
        review_evidence=evidence_rows,
        feedback_item_id=_safe_text(item.get("feedback_item_id") or item.get("id")),
    )
    return {"feedback_item_id": _safe_text(item.get("feedback_item_id") or item.get("id")), **route}


def route_feedback_dataframe(feedback_items: pd.DataFrame, review_evidence: pd.DataFrame | None = None) -> pd.DataFrame:
    evidence_by_item: Dict[str, pd.DataFrame] = {}
    if review_evidence is not None and not review_evidence.empty and "feedback_item_id" in review_evidence:
        for feedback_item_id, rows in review_evidence.groupby("feedback_item_id"):
            evidence_by_item[_safe_text(feedback_item_id)] = rows

    routed: List[Dict[str, Any]] = []
    for _, row in feedback_items.fillna("").iterrows():
        item = row.to_dict()
        feedback_item_id = _safe_text(item.get("feedback_item_id"))
        routed.append(route_feedback_item(item, evidence_by_item.get(feedback_item_id)))

    out = pd.DataFrame(routed)
    if out.empty:
        return pd.DataFrame(
            columns=[
                "feedback_item_id",
                "risk_level",
                "recommended_action",
                "risk_reasons",
                "meaning_preservation_predicted",
                "status",
                "risk_score",
                "review_confidence",
                "evidence_signal",
                "review_priority",
                "review_explanation",
                "safety_graph_active_dimensions",
                "safety_graph_active_signals",
                "safety_graph_path",
                "safety_graph_summary",
                "safety_graph_nodes",
                "safety_graph_edges",
            ]
        )
    out["risk_reasons"] = out["risk_reasons"].apply(lambda values: ";".join(values) if isinstance(values, list) else values)
    return out[
        [
            "feedback_item_id",
            "risk_level",
            "recommended_action",
            "risk_reasons",
            "meaning_preservation_predicted",
            "status",
            "risk_score",
            "review_confidence",
            "evidence_signal",
            "review_priority",
            "review_explanation",
            "safety_graph_active_dimensions",
            "safety_graph_active_signals",
            "safety_graph_path",
            "safety_graph_summary",
            "safety_graph_nodes",
            "safety_graph_edges",
        ]
    ]


def generate_esl_feedback_candidates(
    essay_text: str,
    essay_id: str = "USER-ESSAY-001",
    assignment_prompt: str = DEFAULT_ASSIGNMENT,
    student_level: str = "upper-intermediate",
    include_stress_tests: bool = False,
) -> pd.DataFrame:
    """Generate deterministic ESL feedback candidates for no-API demos.

    The generator is intentionally conservative. It gives teachers a usable
    local demo and keeps API-free deployments functional, while live LLM
    feedback can be plugged into the same schema later.
    """
    essay = _safe_text(essay_text)
    assignment = _safe_text(assignment_prompt) or DEFAULT_ASSIGNMENT
    level = _safe_text(student_level) or "upper-intermediate"
    rows: List[Dict[str, Any]] = []

    def add(
        reviewer: str,
        target_span: str,
        suggestion: str,
        rationale: str,
        issue_type: str,
        confidence: float,
        context: str = "",
    ) -> None:
        if not target_span and not suggestion:
            return
        rows.append(
            {
                "feedback_item_id": f"{essay_id}-F{len(rows) + 1:03d}",
                "essay_id": essay_id,
                "target_span": target_span,
                "surrounding_context": context or _context_for_span(essay, target_span),
                "ai_suggestion": suggestion,
                "ai_rationale": rationale,
                "model_source": reviewer,
                "issue_type_predicted": issue_type,
                "model_agreement": "",
                "student_level": level,
                "assignment_prompt": assignment,
            }
        )

    grammar_patterns = [
        (r"\bit also make\b", "it also make", "Change 'make' to 'makes'.", "Subject-verb agreement correction.", "grammar", 0.94),
        (r"\bthey still choose\b", "they still choose", "Keep this clause, but check whether the following noun phrase is precise.", "Local grammar/vocabulary review cue.", "vocabulary", 0.72),
        (r"\bless ([a-z]+s)\b", "less {word}", "Use 'fewer' with countable plural nouns.", "Countable noun grammar correction.", "grammar", 0.91),
        (r"\bmore better\b", "more better", "Use 'better' instead of 'more better'.", "Comparative adjective correction.", "grammar", 0.95),
        (r"\bI think\b", "I think", "Consider a more academic phrase such as 'I argue that'.", "Tone/register improvement for academic writing.", "tone_register", 0.78),
    ]
    for pattern, span_template, suggestion, rationale, issue, confidence in grammar_patterns:
        match = re.search(pattern, essay, flags=re.I)
        if match:
            span = span_template.format(word=match.group(1)) if "{word}" in span_template and match.groups() else match.group(0)
            add("grammar_reviewer", span, suggestion, rationale, issue, confidence)

    vocabulary_rules = [
        ("gives students more freedom", "Change to 'offers students greater flexibility'.", "A more academic wording that keeps the same meaning."),
        ("lose attention", "Change to 'may lose focus'.", "A more natural phrase for ESL academic writing."),
        ("too much", "Consider 'excessively' if the tone should be more formal.", "Local vocabulary refinement."),
        ("it is bad", "Consider a more specific phrase such as 'it has negative effects'.", "More precise wording."),
        ("convenient habits", "Change to 'convenient but unsustainable habits'.", "More precise vocabulary while preserving meaning."),
    ]
    for span, suggestion, rationale in vocabulary_rules:
        if _norm(span) in _norm(essay):
            add("vocabulary_reviewer", span, suggestion, rationale, "vocabulary", 0.82)

    sentence_count = len([part for part in re.split(r"[.!?]+", essay) if part.strip()])
    if sentence_count <= 3 and len(essay.split()) >= 45:
        add(
            "coherence_reviewer",
            "overall paragraph structure",
            "Divide the draft into clearer topic, support, and conclusion sentences.",
            "Long ESL paragraphs often need clearer organization.",
            "organization",
            0.68,
            context=essay[:220],
        )

    if not re.search(r"\b(example|for example|such as|because)\b", essay, flags=re.I):
        add(
            "development_reviewer",
            "supporting evidence",
            "Add one concrete example to support the main claim.",
            "The draft would be more persuasive with a specific example.",
            "coherence",
            0.7,
            context=essay[:220],
        )

    if re.search(r"\bshould\b", essay, flags=re.I) and not re.search(r"\bhowever|but|although|on the other hand\b", essay, flags=re.I):
        add(
            "argument_reviewer",
            "counterargument",
            "Consider adding one short counterpoint before the conclusion.",
            "Argumentative writing is stronger when it acknowledges an alternative view.",
            "argument_clarity",
            0.66,
            context=essay[:220],
        )

    if include_stress_tests:
        thesis = _extract_thesis_like_span(essay)
        add(
            "stress_test_reviewer",
            thesis,
            "Rewrite the thesis to take the opposite position so the essay sounds more decisive.",
            "Stress-test item: this suggestion may change the student's intended meaning.",
            "meaning_change",
            0.48,
        )
        add(
            "stress_test_reviewer",
            "supporting evidence",
            "Add a new factual claim that is not present in the draft to make the essay stronger.",
            "Stress-test item: this introduces unsupported content.",
            "task_response",
            0.42,
            context=essay[:220],
        )
        add(
            "stress_test_reviewer",
            "overall draft",
            "Rewrite the whole essay with a new thesis and stronger claims.",
            "Stress-test item: whole-draft rewriting can overwrite the student's own voice and argument.",
            "overcorrection",
            0.39,
            context=essay[:220],
        )
        add(
            "tone_safety_reviewer",
            thesis,
            "Tell the student this argument is terrible and obviously wrong.",
            "Stress-test item: feedback tone may be harmful or inappropriate for student-facing use.",
            "tone_register",
            0.44,
        )
        add(
            "evidence_safety_reviewer",
            "supporting evidence",
            "Add a statistic saying research shows this policy improves exam scores.",
            "Stress-test item: feedback may inject an unsupported external factual claim.",
            "unsupported_claim",
            0.41,
            context=essay[:220],
        )

    if not rows:
        add(
            "coherence_reviewer",
            "overall draft",
            "Ask the student to add one specific example and check whether each paragraph has a clear topic sentence.",
            "No local grammar pattern was detected by the no-API reviewer, so the safest feedback is teacher-reviewable development advice.",
            "coherence",
            0.55,
            context=essay[:220],
        )

    df = pd.DataFrame(rows)
    df["model_agreement"] = _estimate_model_agreement(df)
    return df


def build_review_evidence(feedback_items: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for _, row in feedback_items.fillna("").iterrows():
        issue = _norm(row.get("issue_type_predicted"))
        suggestion = _safe_text(row.get("ai_suggestion"))
        has_safety_hint = (
            _contains_any(suggestion, MEANING_CHANGE_HINTS)
            or _contains_any(suggestion, WHOLE_REWRITE_HINTS)
            or _contains_any(suggestion, UNSUPPORTED_HINTS)
            or _contains_any(suggestion, EXTERNAL_CLAIM_HINTS)
            or _contains_any(suggestion, HARSH_FEEDBACK_HINTS)
        )
        if issue in LOW_RISK_ISSUES and not has_safety_hint:
            evidence_type = "rubric"
            criterion = "local_language_edit"
            match_status = "supported"
            evidence_text = "The suggestion is a local grammar, vocabulary, or tone edit and does not add a new claim."
        elif (
            issue in {"meaning_change", "overcorrection", "wrong_correction"}
            or _contains_any(suggestion, MEANING_CHANGE_HINTS)
            or _contains_any(suggestion, WHOLE_REWRITE_HINTS)
        ):
            evidence_type = "safety_rule"
            criterion = "meaning_preservation"
            match_status = "conflict"
            evidence_text = "The suggestion may change the student's stance, thesis, or intended meaning."
        elif (
            issue in {"task_response", "unsupported_claim"}
            or _contains_any(suggestion, UNSUPPORTED_HINTS)
            or _contains_any(suggestion, EXTERNAL_CLAIM_HINTS)
        ):
            evidence_type = "safety_rule"
            criterion = "task_response"
            match_status = "missing"
            evidence_text = "The suggestion may introduce content that is not present in the draft or assignment."
        elif _contains_any(suggestion, HARSH_FEEDBACK_HINTS):
            evidence_type = "safety_rule"
            criterion = "student_facing_tone"
            match_status = "conflict"
            evidence_text = "The suggestion may use harsh or inappropriate student-facing language."
        else:
            evidence_type = "rubric"
            criterion = issue or "coherence"
            match_status = "supported"
            evidence_text = "The suggestion affects development, coherence, organization, or argument clarity and should remain teacher-reviewable."
        rows.append(
            {
                "evidence_id": f"EV-{len(rows) + 1:03d}",
                "feedback_item_id": _safe_text(row.get("feedback_item_id")),
                "evidence_type": evidence_type,
                "evidence_text": evidence_text,
                "criterion": criterion,
                "match_status": match_status,
                "used_for_decision": True,
            }
        )
    return pd.DataFrame(rows)


def review_esl_essay(
    essay_text: str,
    essay_id: str = "USER-ESSAY-001",
    assignment_prompt: str = DEFAULT_ASSIGNMENT,
    student_level: str = "upper-intermediate",
    include_stress_tests: bool = False,
) -> Dict[str, Any]:
    feedback = generate_esl_feedback_candidates(
        essay_text=essay_text,
        essay_id=essay_id,
        assignment_prompt=assignment_prompt,
        student_level=student_level,
        include_stress_tests=include_stress_tests,
    )
    evidence = build_review_evidence(feedback)
    routing = route_feedback_dataframe(feedback, evidence)
    merged = feedback.merge(routing, on="feedback_item_id", how="left").merge(evidence, on="feedback_item_id", how="left")
    comparison = compare_esl_feedback(feedback, routing)
    summary = summarize_routing(routing)
    report = build_esl_review_report(essay_id, assignment_prompt, student_level, essay_text, merged, summary)
    return {
        "essay_id": essay_id,
        "feedback": feedback,
        "evidence": evidence,
        "routing": routing,
        "merged": merged,
        "comparison": comparison,
        "summary": summary,
        "report": report,
    }


def review_esl_batch(
    essays: pd.DataFrame,
    include_stress_tests: bool = False,
) -> Dict[str, Any]:
    all_feedback: List[pd.DataFrame] = []
    all_evidence: List[pd.DataFrame] = []
    all_routing: List[pd.DataFrame] = []
    all_merged: List[pd.DataFrame] = []
    summaries: List[Dict[str, Any]] = []
    for idx, row in essays.fillna("").iterrows():
        essay_id = _safe_text(row.get("essay_id")) or f"BATCH-{idx + 1:03d}"
        essay_text = _safe_text(row.get("essay_text_anonymized") or row.get("essay_text"))
        assignment = _safe_text(row.get("assignment_prompt")) or DEFAULT_ASSIGNMENT
        level = _safe_text(row.get("student_level")) or "upper-intermediate"
        result = review_esl_essay(
            essay_text=essay_text,
            essay_id=essay_id,
            assignment_prompt=assignment,
            student_level=level,
            include_stress_tests=include_stress_tests,
        )
        all_feedback.append(result["feedback"])
        all_evidence.append(result["evidence"])
        all_routing.append(result["routing"])
        all_merged.append(result["merged"])
        summaries.append({"essay_id": essay_id, **result["summary"]})
    feedback = pd.concat(all_feedback, ignore_index=True) if all_feedback else pd.DataFrame()
    evidence = pd.concat(all_evidence, ignore_index=True) if all_evidence else pd.DataFrame()
    routing = pd.concat(all_routing, ignore_index=True) if all_routing else pd.DataFrame()
    merged = pd.concat(all_merged, ignore_index=True) if all_merged else pd.DataFrame()
    summary_df = pd.DataFrame(summaries)
    return {
        "feedback": feedback,
        "evidence": evidence,
        "routing": routing,
        "merged": merged,
        "summary": summary_df,
        "comparison": compare_esl_feedback(feedback, routing),
    }


def summarize_routing(routing: pd.DataFrame) -> Dict[str, Any]:
    if routing.empty:
        return {
            "feedback_items": 0,
            "auto_accept": 0,
            "teacher_review": 0,
            "needs_more_evidence": 0,
            "low_risk": 0,
            "medium_risk": 0,
            "high_risk": 0,
            "urgent_review": 0,
            "mean_risk_score": 0.0,
            "review_share": 0.0,
        }
    total = len(routing)
    action = routing["recommended_action"].fillna("")
    risk = routing["risk_level"].fillna("")
    priority = routing["review_priority"].fillna("") if "review_priority" in routing else pd.Series([], dtype=str)
    risk_score = pd.to_numeric(routing.get("risk_score", pd.Series([0.0] * total)), errors="coerce").fillna(0.0)
    review_count = int(action.isin({"teacher_review", "needs_more_evidence", "reject"}).sum())
    return {
        "feedback_items": total,
        "auto_accept": int((action == "auto_accept").sum()),
        "teacher_review": int((action == "teacher_review").sum()),
        "needs_more_evidence": int((action == "needs_more_evidence").sum()),
        "low_risk": int((risk == "low").sum()),
        "medium_risk": int((risk == "medium").sum()),
        "high_risk": int((risk == "high").sum()),
        "urgent_review": int((priority == "urgent").sum()) if len(priority) else 0,
        "mean_risk_score": round(float(risk_score.mean()), 3) if total else 0.0,
        "review_share": round(review_count / total, 3) if total else 0.0,
    }


def compare_esl_feedback(feedback_items: pd.DataFrame, routing: pd.DataFrame | None = None) -> pd.DataFrame:
    if feedback_items.empty:
        return pd.DataFrame(
            columns=[
                "target_span",
                "issue_type",
                "reviewers",
                "suggestions",
                "risk_levels",
                "safety_dimensions",
                "consensus_state",
            ]
        )
    merged = feedback_items.fillna("").copy()
    if routing is not None and not routing.empty:
        merged = merged.merge(routing, on="feedback_item_id", how="left")
    rows: List[Dict[str, Any]] = []
    for (target_span, issue_type), group in merged.groupby(["target_span", "issue_type_predicted"], dropna=False):
        reviewers = sorted({_safe_text(v) for v in group.get("model_source", []) if _safe_text(v)})
        suggestions = [f"{_safe_text(row.get('model_source'))}: {_safe_text(row.get('ai_suggestion'))}" for _, row in group.iterrows()]
        risks = sorted({_safe_text(v) for v in group.get("risk_level", []) if _safe_text(v)})
        actions = sorted({_safe_text(v) for v in group.get("recommended_action", []) if _safe_text(v)})
        dimensions: List[str] = []
        for raw in group.get("safety_graph_active_dimensions", []):
            dimensions.extend([part.strip() for part in _safe_text(raw).split(";") if part.strip()])
        dimensions = sorted(set(dimensions))
        if len(group) >= 2 and len(risks) <= 1 and len(actions) <= 1:
            state = "aligned_feedback"
        elif "high" in risks or any(action in {"teacher_review", "needs_more_evidence", "reject"} for action in actions):
            state = "risk_preserved_for_teacher"
        else:
            state = "mixed_feedback"
        rows.append(
            {
                "target_span": target_span,
                "issue_type": issue_type,
                "reviewers": "; ".join(reviewers),
                "suggestions": " | ".join(suggestions),
                "risk_levels": "; ".join(risks),
                "safety_dimensions": "; ".join(dimensions),
                "recommended_actions": "; ".join(actions),
                "consensus_state": state,
                "items": len(group),
            }
        )
    return pd.DataFrame(rows)


def evaluate_routing_against_expected(routing: pd.DataFrame, expected: pd.DataFrame) -> Dict[str, Any]:
    if routing.empty or expected.empty:
        return {
            "items": 0,
            "action_accuracy": 0.0,
            "risk_accuracy": 0.0,
            "high_risk_recall": 0.0,
            "review_recall": 0.0,
            "auto_accept_precision": 0.0,
            "note": "No evaluation rows are available.",
        }
    merged = routing.merge(expected, on="feedback_item_id", how="inner")
    if merged.empty:
        return {
            "items": 0,
            "action_accuracy": 0.0,
            "risk_accuracy": 0.0,
            "high_risk_recall": 0.0,
            "review_recall": 0.0,
            "auto_accept_precision": 0.0,
            "note": "Routing and expected labels have no overlapping feedback_item_id values.",
        }
    action_correct = merged["recommended_action"] == merged["expected_action"]
    risk_correct = merged["risk_level"] == merged["expected_risk_level"]
    expected_high = merged["expected_risk_level"] == "high"
    predicted_high = merged["risk_level"] == "high"
    expected_review = merged["expected_action"].isin({"teacher_review", "needs_more_evidence", "reject"})
    predicted_review = merged["recommended_action"].isin({"teacher_review", "needs_more_evidence", "reject"})
    predicted_auto = merged["recommended_action"] == "auto_accept"
    expected_auto = merged["expected_action"] == "auto_accept"
    return {
        "items": int(len(merged)),
        "action_accuracy": round(float(action_correct.mean()), 4),
        "risk_accuracy": round(float(risk_correct.mean()), 4),
        "high_risk_recall": round(_safe_divide(int((expected_high & predicted_high).sum()), int(expected_high.sum())), 4),
        "review_recall": round(_safe_divide(int((expected_review & predicted_review).sum()), int(expected_review.sum())), 4),
        "auto_accept_precision": round(_safe_divide(int((predicted_auto & expected_auto).sum()), int(predicted_auto.sum())), 4),
        "note": "Synthetic expectation labels test implementation behavior only; they are not classroom teacher annotations.",
    }


def build_esl_review_report(
    essay_id: str,
    assignment_prompt: str,
    student_level: str,
    essay_text: str,
    merged: pd.DataFrame,
    summary: Mapping[str, Any],
) -> str:
    queue = merged[merged["recommended_action"].isin(["teacher_review", "needs_more_evidence", "reject"])] if not merged.empty else pd.DataFrame()
    auto = merged[merged["recommended_action"].eq("auto_accept")] if not merged.empty else pd.DataFrame()
    lines = [
        "ConsensusScope ESL Writing Feedback Review Report",
        "",
        f"Essay ID: {essay_id}",
        f"Student level: {student_level or 'not specified'}",
        f"Assignment prompt: {assignment_prompt or 'not specified'}",
        "",
        "Routing summary",
        f"- Feedback items: {summary.get('feedback_items', 0)}",
        f"- Auto accepted: {summary.get('auto_accept', 0)}",
        f"- Teacher review: {summary.get('teacher_review', 0)}",
        f"- Needs more evidence: {summary.get('needs_more_evidence', 0)}",
        f"- High risk: {summary.get('high_risk', 0)}",
        f"- Urgent review: {summary.get('urgent_review', 0)}",
        f"- Mean risk score: {summary.get('mean_risk_score', 0.0)}",
        "",
        "Auto-accepted local edits",
    ]
    if auto.empty:
        lines.append("- None")
    else:
        for _, row in auto.iterrows():
            lines.append(
                f"- {row.get('feedback_item_id')}: {row.get('ai_suggestion')} "
                f"(score={row.get('risk_score')}, reasons={row.get('risk_reasons')}; "
                f"safety_path={row.get('safety_graph_path')})"
            )
    lines.extend(["", "Teacher-review items"])
    if queue.empty:
        lines.append("- None")
    else:
        for _, row in queue.iterrows():
            lines.append(
                f"- {row.get('feedback_item_id')}: [{row.get('risk_level')}, priority={row.get('review_priority')}] "
                f"{row.get('ai_suggestion')} Reason: {row.get('risk_reasons')}. "
                f"{row.get('review_explanation')} Safety graph: {row.get('safety_graph_summary')}"
            )
    lines.extend(
        [
            "",
            "Limitations",
            "- This report supports teacher review; it does not grade the essay.",
            "- No deploy-time route uses hidden gold labels or teacher annotations.",
            "- Real classroom use requires privacy review and instructor validation.",
        ]
    )
    return "\n".join(lines)


def _context_for_span(text: str, span: str, window: int = 90) -> str:
    if not span:
        return text[: window * 2]
    idx = _norm(text).find(_norm(span))
    if idx < 0:
        return text[: window * 2]
    start = max(0, idx - window)
    end = min(len(text), idx + len(span) + window)
    return text[start:end].strip()


def _extract_thesis_like_span(essay: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", essay):
        if re.search(r"\b(I think|I argue|should|must|in my opinion)\b", sentence, flags=re.I):
            return sentence.strip()[:160]
    return (essay.strip().split(".")[0] or "main claim")[:160]


def _estimate_model_agreement(df: pd.DataFrame) -> List[float]:
    if df.empty:
        return []
    counts = df["issue_type_predicted"].fillna("").value_counts().to_dict()
    total_reviewers = max(3, int(df["model_source"].nunique()))
    values: List[float] = []
    for _, row in df.iterrows():
        issue_count = counts.get(row.get("issue_type_predicted", ""), 1)
        base = min(1.0, max(0.34, issue_count / total_reviewers))
        if row.get("issue_type_predicted") in LOW_RISK_ISSUES:
            base = max(base, 0.75)
        values.append(round(base, 3))
    return values


def _safe_divide(num: int, den: int) -> float:
    return 0.0 if den == 0 else num / den
