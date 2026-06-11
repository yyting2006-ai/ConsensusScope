import pandas as pd
import pytest

from scripts.analyze_teacher_likert_pilot import SCORE_FIELDS, _read_ratings, analyze


def _rating_row(expert_id, item_id, essay_id, scores):
    row = {
        "expert_id": str(expert_id),
        "batch_id": "1",
        "feedback_item_id": item_id,
        "essay_id": essay_id,
        "created_at": "2026-06-11T10:00:00",
        "updated_at": "2026-06-11T10:00:10",
        "duration_seconds": 10,
    }
    row.update(dict(zip(SCORE_FIELDS, scores)))
    return row


def test_two_teacher_likert_analysis_merges_with_routing():
    ratings = pd.DataFrame(
        [
            _rating_row(1, "A", "E1", [5, 5, 5, 4, 5, 5]),
            _rating_row(2, "A", "E1", [5, 5, 4, 4, 5, 4]),
            _rating_row(1, "B", "E1", [1, 1, 1, 2, 2, 1]),
            _rating_row(2, "B", "E1", [1, 1, 1, 1, 2, 1]),
            _rating_row(1, "C", "E2", [4, 4, 3, 4, 3, 3]),
            _rating_row(2, "C", "E2", [4, 4, 3, 4, 3, 3]),
        ]
    )
    routing = pd.DataFrame(
        [
            {"feedback_item_id": "A", "recommended_action": "auto_accept"},
            {"feedback_item_id": "B", "recommended_action": "teacher_review"},
            {"feedback_item_id": "C", "recommended_action": "teacher_review"},
        ]
    )

    result = analyze(ratings, routing)
    summary = result["summary"]

    assert summary["rated_items"] == 3
    assert summary["teacher_count"] == 2
    assert summary["review_needed_recall"] == 1.0
    assert summary["unsafe_reviewed_recall"] == 1.0
    assert summary["auto_accept_precision_against_teacher_safe"] == 1.0
    assert summary["any_teacher_review_needed_recall"] == 1.0
    assert summary["any_teacher_unsafe_reviewed_recall"] == 1.0
    assert summary["agreement"]["items_with_two_ratings"] == 3
    assert "mean_correctness_score" in result["item_aggregates"].columns
    assert "any_teacher_unsafe" in result["item_aggregates"].columns
    assert not result["disagreement_hotspots"].empty


def test_likert_reader_rejects_more_than_two_teachers(tmp_path):
    ratings = pd.DataFrame(
        [
            _rating_row(1, "A", "E1", [5, 5, 5, 5, 5, 5]),
            _rating_row(2, "A", "E1", [5, 5, 5, 5, 5, 5]),
            _rating_row(3, "A", "E1", [5, 5, 5, 5, 5, 5]),
        ]
    )
    path = tmp_path / "likert_feedback_ratings.csv"
    ratings.to_csv(path, index=False)

    with pytest.raises(ValueError, match="at most two teachers"):
        _read_ratings(path)
