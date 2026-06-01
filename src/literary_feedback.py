from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List

import pandas as pd
import requests

from src.llm.clients import format_http_error, parse_json_from_text


DEFAULT_LITERARY_ESSAY = """Mary Shelley write Frankenstein in 1847, and Jane Austen wrote Jane Eyre. Both novels shows how women are trapped by society, but Frankenstein is only about science and Jane Eyre is only about love. The monster is Victor Frankenstein, so the novel proves that people should never study knowledge. In comparison, the two books are same because both main characters want freedom."""


EXAMPLE_ESSAYS = {
    "Frankenstein vs Jane Eyre · error-rich demo": DEFAULT_LITERARY_ESSAY,
    "Frankenstein vs Jane Eyre · argument-risk demo": """In Frankenstein and Jane Eyre, the protagonists search for freedom, but the essay should not treat both novels as the same story. Mary Shelley write about ambition and responsibility, while Jane Eyre focuses on moral independence. The monster is Victor Frankenstein, so the comparison shows that freedom always destroys society.""",
    "Blank workspace": "",
}


ISSUE_ORDER = {
    "grammar": 0,
    "word_choice": 1,
    "academic_style": 2,
    "literary_fact": 3,
    "argument": 4,
}


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", _safe_text(value).lower()).strip(" .,:;!?")


def _safe_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, parsed))


def load_literary_kg(path: str) -> pd.DataFrame:
    try:
        kg = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["entity", "relation", "value", "work", "evidence", "source"])
    expected = ["entity", "relation", "value", "work", "evidence", "source"]
    for col in expected:
        if col not in kg.columns:
            kg[col] = ""
    return kg[expected].fillna("")


def retrieve_literary_knowledge(essay: str, kg: pd.DataFrame, limit: int = 12) -> List[Dict[str, str]]:
    text = _norm(essay)
    rows: List[Dict[str, str]] = []
    if kg.empty:
        return rows
    for _, row in kg.iterrows():
        entity = _safe_text(row.get("entity"))
        work = _safe_text(row.get("work"))
        value = _safe_text(row.get("value"))
        candidates = [entity, work, value]
        matched = [candidate for candidate in candidates if candidate and _norm(candidate) in text]
        if matched:
            out = {key: _safe_text(row.get(key)) for key in kg.columns}
            out["match"] = matched[0]
            out["match_score"] = str(round(min(1.0, 0.55 + 0.15 * len(matched)), 3))
            rows.append(out)
        if len(rows) >= limit:
            break
    return rows


def _kg_evidence(kg_rows: Iterable[Dict[str, str]], entity: str, relation: str = "") -> List[str]:
    evidence: List[str] = []
    entity_norm = _norm(entity)
    relation_norm = _norm(relation)
    for row in kg_rows:
        if entity_norm and entity_norm not in {_norm(row.get("entity")), _norm(row.get("work"))}:
            continue
        if relation_norm and relation_norm != _norm(row.get("relation")):
            continue
        text = _safe_text(row.get("evidence"))
        if text:
            evidence.append(text)
    return evidence


def _suggestion(
    reviewer: str,
    span: str,
    issue_type: str,
    suggestion: str,
    rationale: str,
    confidence: float,
    risk: str,
    evidence: Iterable[str] = (),
) -> Dict[str, Any]:
    return {
        "reviewer": reviewer,
        "span": span,
        "issue_type": issue_type,
        "suggestion": suggestion,
        "rationale": rationale,
        "confidence": round(float(confidence), 3),
        "knowledge_evidence": list(evidence),
        "meaning_change_risk": risk,
    }


def build_literary_feedback_prompt(essay: str, kg_rows: List[Dict[str, str]], reviewer_role: str) -> str:
    kg_text = "\n".join(
        f"- {row.get('entity')} | {row.get('relation')} | {row.get('value')}: {row.get('evidence')}"
        for row in kg_rows[:12]
    )
    return f"""You are an ESL writing feedback reviewer for comparative literature essays.

Reviewer role: {reviewer_role}

Student essay excerpt:
{essay}

Retrieved literary knowledge:
{kg_text or "No retrieved knowledge."}

Return exactly one JSON object with a key named "feedback".
"feedback" must be a list of 1 to 5 objects. Each object must use this schema:
span, issue_type, suggestion, rationale, confidence, knowledge_evidence, meaning_change_risk

Allowed issue_type values:
grammar, word_choice, academic_style, literary_fact, argument

Allowed meaning_change_risk values:
low, medium, high

Rules:
- Focus on concrete, inspectable feedback.
- Do not rewrite the whole essay.
- Mark grammar-only local edits as low risk.
- Mark literary facts and interpretation-changing suggestions as medium or high risk.
- Use knowledge_evidence only when the retrieved knowledge supports the suggestion.
- confidence must be a number from 0 to 1.
- Do not include Markdown.
"""


def normalize_feedback_items(raw_items: Any, reviewer: str) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized: List[Dict[str, Any]] = []
    allowed_types = set(ISSUE_ORDER)
    allowed_risks = {"low", "medium", "high"}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        issue_type = _norm(item.get("issue_type"))
        risk = _norm(item.get("meaning_change_risk"))
        evidence = item.get("knowledge_evidence", [])
        if isinstance(evidence, str):
            evidence = [evidence] if evidence.strip() else []
        if not isinstance(evidence, list):
            evidence = []
        normalized.append(
            _suggestion(
                reviewer=_safe_text(item.get("reviewer")) or reviewer,
                span=_safe_text(item.get("span")),
                issue_type=issue_type if issue_type in allowed_types else "academic_style",
                suggestion=_safe_text(item.get("suggestion")),
                rationale=_safe_text(item.get("rationale")),
                confidence=_safe_confidence(item.get("confidence", 0.0)),
                risk=risk if risk in allowed_risks else "medium",
                evidence=[_safe_text(value) for value in evidence if _safe_text(value)],
            )
        )
    return [item for item in normalized if item["span"] and item["suggestion"]]


def call_literary_reviewer(
    config: Any,
    essay: str,
    kg_rows: List[Dict[str, str]],
    reviewer_role: str,
    temperature: float = 0.1,
    max_tokens: int = 1200,
    timeout: int = 60,
) -> Dict[str, Any]:
    started = time.time()
    base = {
        "provider": getattr(config, "provider", ""),
        "model": getattr(config, "model", ""),
        "reviewer_role": reviewer_role,
        "feedback": [],
        "raw_output": "",
        "request_error": "",
        "parse_error": "",
        "latency_sec": 0.0,
    }
    if not getattr(config, "enabled", True):
        return {**base, "request_error": "Model is disabled"}
    if not getattr(config, "api_key", ""):
        return {**base, "request_error": "Missing API key"}

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": "You must output valid JSON only."},
            {"role": "user", "content": build_literary_feedback_prompt(essay, kg_rows, reviewer_role)},
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
        if not response.ok:
            raise RuntimeError(format_http_error(response))
        raw = str(response.json()["choices"][0]["message"]["content"])
        parsed = parse_json_from_text(raw)
        parse_error = _safe_text(parsed.get("parse_error"))
        feedback = normalize_feedback_items(parsed.get("feedback", []), f"{config.provider}_{reviewer_role}")
        return {
            **base,
            "feedback": feedback,
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


def run_live_literary_reviewers(
    configs: Iterable[Any],
    essay: str,
    kg_rows: List[Dict[str, str]],
    max_workers: int = 4,
) -> Dict[str, Any]:
    roles = ["grammar", "literary_fact", "argument"]
    tasks = []
    for idx, config in enumerate([cfg for cfg in configs if getattr(cfg, "enabled", True)]):
        role = roles[idx % len(roles)]
        tasks.append((config, role))
    if not tasks:
        return {"feedback": [], "reviewer_results": []}

    results: List[Dict[str, Any]] = []
    workers = max(1, min(max_workers, len(tasks)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(call_literary_reviewer, config, essay, kg_rows, role)
            for config, role in tasks
        ]
        for future in as_completed(futures):
            results.append(future.result())

    feedback = [item for result in results for item in result.get("feedback", [])]
    return {
        "feedback": feedback,
        "reviewer_results": sorted(results, key=lambda item: str(item.get("provider", ""))),
    }


def generate_demo_literary_feedback(essay: str, kg: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generate deterministic multi-reviewer feedback for a no-API demo.

    The output mirrors the schema expected from live LLM reviewers, so API-based
    generation can later replace this fallback without changing the UI.
    """

    kg_rows = retrieve_literary_knowledge(essay, kg, limit=30)
    lowered = essay.lower()
    feedback: List[Dict[str, Any]] = []

    if re.search(r"\bMary Shelley write\b", essay, flags=re.I):
        feedback.extend(
            [
                _suggestion(
                    "grammar_reviewer",
                    "Mary Shelley write",
                    "grammar",
                    "Mary Shelley wrote",
                    "Use past-tense subject-verb agreement when discussing publication history.",
                    0.94,
                    "low",
                ),
                _suggestion(
                    "style_reviewer",
                    "Mary Shelley write",
                    "grammar",
                    "Mary Shelley wrote",
                    "The sentence needs a finite past-tense verb.",
                    0.9,
                    "low",
                ),
            ]
        )

    if re.search(r"\bnovels shows\b", essay, flags=re.I):
        feedback.extend(
            [
                _suggestion(
                    "grammar_reviewer",
                    "Both novels shows",
                    "grammar",
                    "Both novels show",
                    "Plural subject 'novels' takes the base verb 'show'.",
                    0.96,
                    "low",
                ),
                _suggestion(
                    "academic_reviewer",
                    "Both novels shows",
                    "grammar",
                    "Both novels show",
                    "This is a local grammar correction that preserves meaning.",
                    0.91,
                    "low",
                ),
                _suggestion(
                    "kg_reviewer",
                    "Both novels shows",
                    "grammar",
                    "Both novels show",
                    "The change does not alter the literary claim.",
                    0.86,
                    "low",
                ),
            ]
        )

    if "frankenstein in 1847" in lowered:
        feedback.extend(
            [
                _suggestion(
                    "kg_reviewer",
                    "Frankenstein in 1847",
                    "literary_fact",
                    "Frankenstein was first published in 1818",
                    "The knowledge base contradicts the stated publication year.",
                    0.88,
                    "medium",
                    _kg_evidence(kg_rows, "Frankenstein", "publication_year"),
                ),
                _suggestion(
                    "fact_reviewer",
                    "Frankenstein in 1847",
                    "literary_fact",
                    "Frankenstein was first published in 1818",
                    "Correct the factual date before using the comparison as evidence.",
                    0.82,
                    "medium",
                    _kg_evidence(kg_rows, "Frankenstein", "publication_year"),
                ),
            ]
        )

    if "jane austen wrote jane eyre" in lowered:
        evidence = _kg_evidence(kg_rows, "Jane Eyre", "author")
        feedback.extend(
            [
                _suggestion(
                    "kg_reviewer",
                    "Jane Austen wrote Jane Eyre",
                    "literary_fact",
                    "Charlotte Bronte wrote Jane Eyre",
                    "The knowledge base attributes Jane Eyre to Charlotte Bronte, not Jane Austen.",
                    0.92,
                    "medium",
                    evidence,
                ),
                _suggestion(
                    "fact_reviewer",
                    "Jane Austen wrote Jane Eyre",
                    "literary_fact",
                    "Jane Eyre is by Charlotte Bronte",
                    "This is a factual correction supported by the literary knowledge base.",
                    0.86,
                    "medium",
                    evidence,
                ),
            ]
        )

    if "monster is victor frankenstein" in lowered:
        evidence = _kg_evidence(kg_rows, "Frankenstein", "central_character")
        feedback.extend(
            [
                _suggestion(
                    "kg_reviewer",
                    "The monster is Victor Frankenstein",
                    "literary_fact",
                    "Victor Frankenstein is the scientist; the created being is the creature",
                    "The statement conflates Victor Frankenstein with the creature.",
                    0.84,
                    "medium",
                    evidence,
                ),
                _suggestion(
                    "argument_reviewer",
                    "The monster is Victor Frankenstein",
                    "argument",
                    "Clarify whether you mean Victor Frankenstein or the creature he creates",
                    "The ambiguity affects the interpretation and should be reviewed.",
                    0.76,
                    "high",
                    evidence,
                ),
            ]
        )

    if "only about science" in lowered or "only about love" in lowered:
        feedback.append(
            _suggestion(
                "argument_reviewer",
                "only about science / only about love",
                "argument",
                "Use a more qualified claim about dominant themes instead of reducing each novel to one topic",
                "The absolute wording is interpretive and may oversimplify the literary comparison.",
                0.74,
                "high",
            )
        )

    if "are same" in lowered:
        feedback.extend(
            [
                _suggestion(
                    "academic_reviewer",
                    "the two books are same",
                    "academic_style",
                    "the two novels share important concerns, but they develop freedom differently",
                    "The revision improves academic precision while preserving the student's comparative intent.",
                    0.8,
                    "medium",
                ),
                _suggestion(
                    "style_reviewer",
                    "the two books are same",
                    "academic_style",
                    "the two novels are similar in their concern with freedom",
                    "This wording is more idiomatic and less absolute.",
                    0.78,
                    "medium",
                ),
            ]
        )

    if not feedback:
        feedback.append(
            _suggestion(
                "academic_reviewer",
                essay[:90] + ("..." if len(essay) > 90 else ""),
                "academic_style",
                "Add a clearer comparative thesis that names the two works, the shared theme, and the key contrast.",
                "The system found no high-confidence local error, so it routes a thesis-level suggestion for review.",
                0.62,
                "medium",
            )
        )

    return feedback


def feedback_issue_key(item: Dict[str, Any]) -> str:
    return f"{_norm(item.get('issue_type'))}::{_norm(item.get('span'))}"


def adjudicate_literary_feedback(feedback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in feedback:
        groups[feedback_issue_key(item)].append(item)

    decisions: List[Dict[str, Any]] = []
    for items in groups.values():
        issue_type = _safe_text(items[0].get("issue_type"))
        span = _safe_text(items[0].get("span"))
        suggestion_counts = Counter(_norm(item.get("suggestion")) for item in items)
        selected_norm, selected_count = suggestion_counts.most_common(1)[0]
        selected = next(item for item in items if _norm(item.get("suggestion")) == selected_norm)
        evidence = [e for item in items for e in item.get("knowledge_evidence", []) if _safe_text(e)]
        avg_conf = sum(float(item.get("confidence", 0.0) or 0.0) for item in items) / len(items)
        max_risk = "high" if any(item.get("meaning_change_risk") == "high" for item in items) else "medium" if any(item.get("meaning_change_risk") == "medium" for item in items) else "low"
        agreement = selected_count / len(items)
        kg_supported = bool(evidence)

        if issue_type in {"grammar", "word_choice"} and agreement >= 0.5 and max_risk == "low":
            risk_level = "low"
            decision = "auto_accept"
            teacher_action = "Optional skim"
            priority = 3
            rationale = "Low-risk local language edit with reviewer agreement."
        elif issue_type == "literary_fact" and kg_supported and agreement >= 0.5:
            risk_level = "medium"
            decision = "teacher_review"
            teacher_action = "Verify factual correction"
            priority = 2
            rationale = "Knowledge-supported factual correction; route to teacher review before changing the essay."
        elif issue_type in {"argument", "academic_style"} or max_risk == "high":
            risk_level = "high" if max_risk == "high" else "medium"
            decision = "teacher_review"
            teacher_action = "Review meaning change"
            priority = 1 if risk_level == "high" else 2
            rationale = "The suggestion may change interpretation, thesis framing, or student intent."
        else:
            risk_level = "medium"
            decision = "teacher_review"
            teacher_action = "Check manually"
            priority = 2
            rationale = "Insufficient agreement or evidence for automatic adoption."

        decisions.append(
            {
                "span": span,
                "issue_type": issue_type,
                "selected_suggestion": _safe_text(selected.get("suggestion")),
                "decision": decision,
                "risk_level": risk_level,
                "teacher_action": teacher_action,
                "priority": priority,
                "agreement": round(agreement, 3),
                "avg_confidence": round(avg_conf, 3),
                "kg_supported": kg_supported,
                "evidence_count": len(evidence),
                "knowledge_evidence": " | ".join(dict.fromkeys(evidence[:3])),
                "rationale": rationale,
            }
        )

    return sorted(decisions, key=lambda row: (row["priority"], ISSUE_ORDER.get(row["issue_type"], 99), row["span"]))


def apply_auto_accepted_edits(essay: str, decisions: List[Dict[str, Any]]) -> str:
    revised = essay
    for item in decisions:
        if item.get("decision") != "auto_accept":
            continue
        span = _safe_text(item.get("span"))
        suggestion = _safe_text(item.get("selected_suggestion"))
        if not span or not suggestion:
            continue
        revised = re.sub(re.escape(span), suggestion, revised, count=1, flags=re.I)
    return revised


def review_queue(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [item for item in decisions if item.get("decision") == "teacher_review"]


def decision_summary_by_type(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in decisions:
        grouped[_safe_text(item.get("issue_type"))].append(item)
    rows = []
    for issue_type, items in grouped.items():
        rows.append(
            {
                "issue_type": issue_type,
                "total": len(items),
                "auto_accept": sum(1 for item in items if item.get("decision") == "auto_accept"),
                "teacher_review": sum(1 for item in items if item.get("decision") == "teacher_review"),
                "kg_supported": sum(1 for item in items if item.get("kg_supported")),
            }
        )
    return sorted(rows, key=lambda row: ISSUE_ORDER.get(row["issue_type"], 99))


def literary_routing_summary(decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(decisions)
    auto = sum(1 for item in decisions if item.get("decision") == "auto_accept")
    review = total - auto
    return {
        "total_suggestions": total,
        "auto_accept": auto,
        "teacher_review": review,
        "auto_share": round(auto / total, 3) if total else 0.0,
        "review_share": round(review / total, 3) if total else 0.0,
        "high_risk": sum(1 for item in decisions if item.get("risk_level") == "high"),
        "kg_supported": sum(1 for item in decisions if item.get("kg_supported")),
    }


def build_literary_feedback_report(
    essay: str,
    kg_rows: List[Dict[str, str]],
    feedback: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
) -> str:
    summary = literary_routing_summary(decisions)
    revised = apply_auto_accepted_edits(essay, decisions)
    queue = review_queue(decisions)
    lines = [
        "# ConsensusScope ESL Literary Feedback Report",
        "",
        "## Essay",
        "",
        essay,
        "",
        "## Routing Summary",
        "",
        f"- Total suggestions: {summary['total_suggestions']}",
        f"- Auto-accepted low-risk edits: {summary['auto_accept']} ({summary['auto_share']})",
        f"- Teacher-review suggestions: {summary['teacher_review']} ({summary['review_share']})",
        f"- KG-supported suggestions: {summary['kg_supported']}",
        f"- High-risk suggestions: {summary['high_risk']}",
        "",
        "## Auto-Accepted Preview",
        "",
        revised,
        "",
        "## Teacher Review Queue",
        "",
    ]
    for item in queue:
        lines.extend(
            [
                f"- [{item['risk_level']}] {item['span']} -> {item['selected_suggestion']}",
                f"  - Action: {item['teacher_action']}",
                f"  - Rationale: {item['rationale']}",
            ]
        )
    lines.extend(
        [
        "",
        "## Retrieved Literary Knowledge",
        "",
        ]
    )
    for row in kg_rows:
        lines.append(f"- {row.get('entity')} / {row.get('relation')} / {row.get('value')}: {row.get('evidence')}")
    lines.extend(["", "## Adjudicated Feedback", ""])
    for item in decisions:
        lines.extend(
            [
                f"### {item['issue_type']} · {item['risk_level']}",
                "",
                f"- Span: {item['span']}",
                f"- Decision: {item['decision']}",
                f"- Selected suggestion: {item['selected_suggestion']}",
                f"- Agreement: {item['agreement']}",
                f"- Knowledge evidence: {item['knowledge_evidence'] or 'N/A'}",
                f"- Rationale: {item['rationale']}",
                "",
            ]
        )
    lines.extend(["## Raw Reviewer Suggestions", "", "```json", json.dumps(feedback, ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines)
