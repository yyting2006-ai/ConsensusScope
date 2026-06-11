import pandas as pd

from src.esl_writing_feedback import (
    build_review_evidence,
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
    assert route["safety_graph_active_dimensions"] == "local_edit"
    assert route["safety_graph_path"].endswith("local_edit -> auto_accept")


def test_meaning_change_routes_to_teacher_review():
    route = rule_based_route(
        issue_type_predicted="meaning_change",
        ai_suggestion="Rewrite the thesis to argue that universities should end online learning completely.",
    )

    assert route["risk_level"] == "high"
    assert route["recommended_action"] == "teacher_review"
    assert route["meaning_preservation_predicted"] == "changes_meaning"
    assert "meaning_change" in route["risk_reasons"]
    assert "meaning_preservation" in route["safety_graph_active_dimensions"]
    assert route["safety_graph_path"].endswith("meaning_preservation -> teacher_review")


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
    assert route["review_priority"] == "normal"


def test_harsh_student_facing_feedback_routes_high():
    route = rule_based_route(
        issue_type_predicted="tone_register",
        ai_suggestion="Tell the student this argument is terrible and obviously wrong.",
        review_evidence={"match_status": "conflict", "criterion": "student_facing_tone"},
    )

    assert route["risk_level"] == "high"
    assert route["recommended_action"] == "teacher_review"
    assert "too_harsh" in route["risk_reasons"]
    assert route["risk_score"] >= 0.72


def test_whole_essay_rewrite_routes_high():
    route = rule_based_route(
        issue_type_predicted="overcorrection",
        ai_suggestion="Rewrite the whole essay with a new thesis and stronger claims.",
        target_span="overall draft",
    )

    assert route["risk_level"] == "high"
    assert route["review_priority"] in {"high", "urgent"}
    assert "meaning_change" in route["risk_reasons"]


def test_unsupported_external_statistic_routes_high():
    route = rule_based_route(
        issue_type_predicted="unsupported_claim",
        ai_suggestion="Add a statistic saying research shows social media improves teenagers' exam scores.",
        review_evidence={"match_status": "missing", "criterion": "task_response"},
    )

    assert route["risk_level"] == "high"
    assert "unsupported_claim" in route["risk_reasons"]
    assert route["meaning_preservation_predicted"] == "changes_meaning"


def test_low_agreement_blocks_auto_release():
    route = rule_based_route(
        issue_type_predicted="vocabulary",
        ai_suggestion="Change to 'compare themselves with others excessively'.",
        model_agreement=0.31,
        review_evidence={"match_status": "supported", "criterion": "local_language_edit"},
    )

    assert route["risk_level"] == "medium"
    assert route["recommended_action"] == "teacher_review"
    assert "low_model_agreement" in route["risk_reasons"]


def test_teacher_dependent_feedback_routes_to_review():
    route = rule_based_route(
        issue_type_predicted="grammar",
        ai_suggestion="Add commas consistently in the list if the teacher wants a clearer series.",
        target_span="air pollution, plastic waste, and traffic problems",
        review_evidence={"match_status": "supported", "criterion": "local_language_edit"},
    )

    assert route["risk_level"] == "medium"
    assert route["recommended_action"] == "teacher_review"
    assert "teacher_dependent" in route["risk_reasons"]


def test_route_feedback_dataframe_matches_demo_ids():
    feedback = pd.read_csv("data/esl_writing_demo/feedback_items.csv")
    evidence = pd.read_csv("data/esl_writing_demo/review_evidence.csv")

    routed = route_feedback_dataframe(feedback, evidence)

    assert len(routed) == len(feedback)
    assert set(routed["feedback_item_id"]) == set(feedback["feedback_item_id"])
    assert {"safety_graph_summary", "safety_graph_nodes", "safety_graph_edges"}.issubset(routed.columns)
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


def test_ai_review_stress_case_evaluation():
    stress = pd.read_csv("data/esl_writing_demo/ai_review_stress_cases.csv")
    expected = stress[["feedback_item_id", "expected_risk_level", "expected_action", "expected_reason"]]
    feedback = stress.drop(columns=["expected_risk_level", "expected_action", "expected_reason"])
    evidence = build_review_evidence(feedback)
    routed = route_feedback_dataframe(feedback, evidence)
    metrics = evaluate_routing_against_expected(routed, expected)

    assert metrics["items"] == len(stress)
    assert metrics["action_accuracy"] >= 0.9
    assert metrics["risk_accuracy"] >= 0.9
    assert metrics["high_risk_recall"] >= 0.95
