import pandas as pd

from src.esl_writing_feedback import (
    evaluate_routing_against_expected,
    review_esl_batch,
    review_esl_essay,
    route_feedback_dataframe,
    rule_based_route,
)


def test_grammar_edit_routes_to_low_auto_accept():
    route = rule_based_route(
        issue_type_predicted="grammar",
        ai_suggestion="Change 'make' to 'makes'.",
        target_span="it also make students",
    )

    assert route["risk_level"] == "low"
    assert route["recommended_action"] == "auto_accept"
    assert route["meaning_preservation_predicted"] == "preserves_meaning"
    assert "local_language_edit" in route["risk_reasons"]


def test_meaning_change_routes_to_teacher_review():
    route = rule_based_route(
        issue_type_predicted="meaning_change",
        ai_suggestion="Rewrite the thesis to argue that universities should end online learning completely.",
    )

    assert route["risk_level"] == "high"
    assert route["recommended_action"] == "teacher_review"
    assert route["meaning_preservation_predicted"] == "changes_meaning"
    assert "meaning_change" in route["risk_reasons"]


def test_overcorrection_routes_to_teacher_review():
    route = rule_based_route(
        issue_type_predicted="overcorrection",
        ai_suggestion="Tell the student that social media is always harmful and should be banned.",
    )

    assert route["risk_level"] == "high"
    assert route["recommended_action"] == "teacher_review"
    assert "overcorrection" in route["risk_reasons"]


def test_unknown_issue_needs_more_evidence():
    route = rule_based_route(issue_type_predicted="")

    assert route["risk_level"] == "medium"
    assert route["recommended_action"] == "needs_more_evidence"
    assert route["status"] == "needs_teacher_review"


def test_route_feedback_dataframe_matches_demo_ids():
    feedback = pd.read_csv("data/esl_writing_demo/feedback_items.csv")
    evidence = pd.read_csv("data/esl_writing_demo/review_evidence.csv")

    routed = route_feedback_dataframe(feedback, evidence)

    assert len(routed) == len(feedback)
    assert set(routed["feedback_item_id"]) == set(feedback["feedback_item_id"])
    assert routed.loc[routed["feedback_item_id"] == "FW-006", "recommended_action"].item() == "auto_accept"
    assert routed.loc[routed["feedback_item_id"] == "FW-014", "recommended_action"].item() == "teacher_review"


def test_single_essay_review_generates_feedback_and_routes():
    result = review_esl_essay(
        essay_text="Social media helps teenagers communicate. But it also make students compare their lives with others too much.",
        essay_id="TEST-ESSAY",
        assignment_prompt="Write an opinion essay about social media.",
        include_stress_tests=True,
    )

    assert not result["feedback"].empty
    assert not result["routing"].empty
    assert result["summary"]["feedback_items"] == len(result["routing"])
    assert result["summary"]["teacher_review"] >= 1
    assert "ConsensusScope ESL Writing Feedback Review Report" in result["report"]


def test_batch_review_processes_multiple_essays():
    essays = pd.read_csv("data/esl_writing_demo/essays.csv")
    result = review_esl_batch(essays, include_stress_tests=False)

    assert not result["summary"].empty
    assert set(result["summary"]["essay_id"]) == set(essays["essay_id"])
    assert not result["merged"].empty


def test_synthetic_expected_label_evaluation():
    feedback = pd.read_csv("data/esl_writing_demo/feedback_items.csv")
    evidence = pd.read_csv("data/esl_writing_demo/review_evidence.csv")
    expected = pd.read_csv("data/esl_writing_demo/expected_routing_labels.csv")
    routed = route_feedback_dataframe(feedback, evidence)
    metrics = evaluate_routing_against_expected(routed, expected)

    assert metrics["items"] == len(expected)
    assert metrics["action_accuracy"] >= 0.9
    assert metrics["high_risk_recall"] >= 0.9
