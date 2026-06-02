from __future__ import annotations

import re
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


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value).lower()).strip(" .,:;!?")


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = _norm(text)
    return any(phrase in lowered for phrase in phrases)


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


def _status_for_action(action: str) -> str:
    return "auto_accepted" if action == "auto_accept" else "needs_teacher_review"


def rule_based_route(
    issue_type_predicted: str,
    ai_suggestion: str = "",
    target_span: str = "",
    surrounding_context: str = "",
    model_agreement: float | None = None,
    review_evidence: Any = None,
) -> Dict[str, Any]:
    """Route an AI feedback item to auto-accept or teacher review.

    The function uses deploy-time signals only: issue type, suggestion text,
    local context, model agreement, parse/evidence status, and rubric/safety
    evidence. It does not use gold labels or teacher decisions.
    """
    issue = _norm(issue_type_predicted).replace("-", "_").replace(" ", "_")
    suggestion_blob = " ".join([ai_suggestion, target_span, surrounding_context, _evidence_text(review_evidence)])
    statuses = _evidence_statuses(review_evidence)
    agreement = _as_float(model_agreement)

    reasons: List[str] = []
    meaning = "unclear"

    if not issue or issue in {"other", "unknown", "parse_error"}:
        reasons.append("parse_error" if issue == "parse_error" else "too_vague")
        return {
            "risk_level": "medium",
            "recommended_action": "needs_more_evidence",
            "risk_reasons": reasons,
            "meaning_preservation_predicted": "unclear",
            "status": "needs_teacher_review",
        }

    if agreement is not None and agreement < 0.5:
        reasons.append("low_model_agreement")

    high_signal = (
        issue in HIGH_RISK_ISSUES
        or _contains_any(suggestion_blob, MEANING_CHANGE_HINTS)
        or "conflict" in statuses
    )
    unsupported_signal = (
        "missing" in statuses
        or _contains_any(suggestion_blob, UNSUPPORTED_HINTS)
        or issue in {"task_response", "unsupported_claim"}
    )

    if high_signal or unsupported_signal:
        if issue == "overcorrection" or _contains_any(suggestion_blob, {"always harmful", "should be banned"}):
            reasons.append("overcorrection")
        if issue in {"meaning_change", "wrong_correction"} or high_signal:
            reasons.append("meaning_change")
        if unsupported_signal:
            reasons.append("unsupported_claim")
        if _contains_any(suggestion_blob, {"new argument", "rewrite the thesis", "exam scores", "closed immediately"}):
            reasons.append("introduces_new_argument")
        meaning = "changes_meaning"
        return {
            "risk_level": "high",
            "recommended_action": "teacher_review",
            "risk_reasons": _dedupe(reasons),
            "meaning_preservation_predicted": meaning,
            "status": "needs_teacher_review",
        }

    if issue in LOW_RISK_ISSUES and not reasons:
        reasons.append("local_language_edit")
        return {
            "risk_level": "low",
            "recommended_action": "auto_accept",
            "risk_reasons": reasons,
            "meaning_preservation_predicted": "preserves_meaning",
            "status": "auto_accepted",
        }

    if issue in LOW_RISK_ISSUES:
        reasons.append("local_language_edit")
    elif issue in {"task_response"}:
        reasons.append("task_mismatch")
    elif issue in MEDIUM_RISK_ISSUES or _contains_any(suggestion_blob, VAGUE_HINTS):
        if issue in {"organization", "tone_register"}:
            reasons.append("task_mismatch")
        else:
            reasons.append("too_vague")
    else:
        reasons.append("too_vague")

    return {
        "risk_level": "medium",
        "recommended_action": "teacher_review",
        "risk_reasons": _dedupe(reasons),
        "meaning_preservation_predicted": meaning,
        "status": "needs_teacher_review",
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
        target_span=_safe_text(item.get("target_span")),
        surrounding_context=_safe_text(item.get("surrounding_context")),
        model_agreement=_as_float(item.get("model_agreement")),
        review_evidence=evidence_rows,
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
        ]
    ]

