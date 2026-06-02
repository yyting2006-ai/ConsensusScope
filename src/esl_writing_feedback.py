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
DEFAULT_ASSIGNMENT = "Write a clear ESL essay that responds to the prompt with organized reasons and examples."


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
        if issue in LOW_RISK_ISSUES:
            evidence_type = "rubric"
            criterion = "local_language_edit"
            match_status = "supported"
            evidence_text = "The suggestion is a local grammar, vocabulary, or tone edit and does not add a new claim."
        elif issue in {"meaning_change", "overcorrection"} or _contains_any(suggestion, MEANING_CHANGE_HINTS):
            evidence_type = "safety_rule"
            criterion = "meaning_preservation"
            match_status = "conflict"
            evidence_text = "The suggestion may change the student's stance, thesis, or intended meaning."
        elif issue in {"task_response", "unsupported_claim"} or _contains_any(suggestion, UNSUPPORTED_HINTS):
            evidence_type = "safety_rule"
            criterion = "task_response"
            match_status = "missing"
            evidence_text = "The suggestion may introduce content that is not present in the draft or assignment."
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
            "review_share": 0.0,
        }
    total = len(routing)
    action = routing["recommended_action"].fillna("")
    risk = routing["risk_level"].fillna("")
    review_count = int(action.isin({"teacher_review", "needs_more_evidence", "reject"}).sum())
    return {
        "feedback_items": total,
        "auto_accept": int((action == "auto_accept").sum()),
        "teacher_review": int((action == "teacher_review").sum()),
        "needs_more_evidence": int((action == "needs_more_evidence").sum()),
        "low_risk": int((risk == "low").sum()),
        "medium_risk": int((risk == "medium").sum()),
        "high_risk": int((risk == "high").sum()),
        "review_share": round(review_count / total, 3) if total else 0.0,
    }


def compare_esl_feedback(feedback_items: pd.DataFrame, routing: pd.DataFrame | None = None) -> pd.DataFrame:
    if feedback_items.empty:
        return pd.DataFrame(columns=["target_span", "issue_type", "reviewers", "suggestions", "risk_levels", "consensus_state"])
    merged = feedback_items.fillna("").copy()
    if routing is not None and not routing.empty:
        merged = merged.merge(routing, on="feedback_item_id", how="left")
    rows: List[Dict[str, Any]] = []
    for (target_span, issue_type), group in merged.groupby(["target_span", "issue_type_predicted"], dropna=False):
        reviewers = sorted({_safe_text(v) for v in group.get("model_source", []) if _safe_text(v)})
        suggestions = [f"{_safe_text(row.get('model_source'))}: {_safe_text(row.get('ai_suggestion'))}" for _, row in group.iterrows()]
        risks = sorted({_safe_text(v) for v in group.get("risk_level", []) if _safe_text(v)})
        actions = sorted({_safe_text(v) for v in group.get("recommended_action", []) if _safe_text(v)})
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
        "",
        "Auto-accepted local edits",
    ]
    if auto.empty:
        lines.append("- None")
    else:
        for _, row in auto.iterrows():
            lines.append(f"- {row.get('feedback_item_id')}: {row.get('ai_suggestion')} ({row.get('risk_reasons')})")
    lines.extend(["", "Teacher-review items"])
    if queue.empty:
        lines.append("- None")
    else:
        for _, row in queue.iterrows():
            lines.append(
                f"- {row.get('feedback_item_id')}: [{row.get('risk_level')}] {row.get('ai_suggestion')} "
                f"Reason: {row.get('risk_reasons')}"
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
