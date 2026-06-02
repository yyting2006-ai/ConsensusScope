import pandas as pd

from src.esl_writing_feedback import route_feedback_dataframe, rule_based_route


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

