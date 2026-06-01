from __future__ import annotations

import pandas as pd

from src.literary_feedback import (
    DEFAULT_LITERARY_ESSAY,
    adjudicate_literary_feedback,
    generate_demo_literary_feedback,
    literary_routing_summary,
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

    assert feedback
    assert any(item["decision"] == "auto_accept" for item in decisions)
    assert any(item["decision"] == "teacher_review" for item in decisions)
    assert summary["teacher_review"] >= 1
    assert any(item["kg_supported"] for item in decisions)
