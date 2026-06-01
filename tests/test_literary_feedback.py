from __future__ import annotations

import pandas as pd

from src.literary_feedback import (
    DEFAULT_LITERARY_ESSAY,
    adjudicate_literary_feedback,
    apply_auto_accepted_edits,
    build_literary_feedback_prompt,
    decision_summary_by_type,
    generate_demo_literary_feedback,
    literary_routing_summary,
    normalize_feedback_items,
    review_queue,
    retrieve_literary_knowledge,
)


def _kg() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "entity": "Frankenstein",
                "relation": "author",
                "value": "Mary Shelley",
                "work": "Frankenstein",
                "evidence": "Frankenstein is attributed to Mary Shelley.",
                "source": "test",
            },
            {
                "entity": "Frankenstein",
                "relation": "publication_year",
                "value": "1818",
                "work": "Frankenstein",
                "evidence": "Frankenstein was first published in 1818.",
                "source": "test",
            },
            {
                "entity": "Jane Eyre",
                "relation": "author",
                "value": "Charlotte Bronte",
                "work": "Jane Eyre",
                "evidence": "Jane Eyre is a novel by Charlotte Bronte.",
                "source": "test",
            },
        ]
    )


def test_retrieve_literary_knowledge_matches_works() -> None:
    rows = retrieve_literary_knowledge("Compare Frankenstein and Jane Eyre.", _kg())

    assert any(row["entity"] == "Frankenstein" for row in rows)
    assert any(row["entity"] == "Jane Eyre" for row in rows)


def test_literary_feedback_routes_low_risk_and_review_items() -> None:
    feedback = generate_demo_literary_feedback(DEFAULT_LITERARY_ESSAY, _kg())
    decisions = adjudicate_literary_feedback(feedback)
    summary = literary_routing_summary(decisions)
    revised = apply_auto_accepted_edits(DEFAULT_LITERARY_ESSAY, decisions)
    queue = review_queue(decisions)
    by_type = decision_summary_by_type(decisions)

    assert feedback
    assert any(item["decision"] == "auto_accept" for item in decisions)
    assert any(item["decision"] == "teacher_review" for item in decisions)
    assert summary["teacher_review"] >= 1
    assert any(item["kg_supported"] for item in decisions)
    assert "Both novels show" in revised
    assert queue and all(item["decision"] == "teacher_review" for item in queue)
    assert any(item["issue_type"] == "grammar" for item in by_type)


def test_live_reviewer_prompt_and_normalization() -> None:
    rows = retrieve_literary_knowledge("Compare Frankenstein and Jane Eyre.", _kg())
    prompt = build_literary_feedback_prompt("Essay", rows, "grammar")
    items = normalize_feedback_items(
        [
            {
                "span": "novels shows",
                "issue_type": "grammar",
                "suggestion": "novels show",
                "rationale": "Plural agreement.",
                "confidence": "0.91",
                "knowledge_evidence": "",
                "meaning_change_risk": "low",
            }
        ],
        "test_reviewer",
    )

    assert '"feedback"' in prompt
    assert items[0]["reviewer"] == "test_reviewer"
    assert items[0]["confidence"] == 0.91
    assert items[0]["meaning_change_risk"] == "low"
