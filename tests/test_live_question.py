from __future__ import annotations

from src.live_question import (
    TASK_CHOICE,
    TASK_CLAIM,
    TASK_FACT_QA,
    build_live_report,
    dynamic_adjudicate_live,
    evidence_quality_score,
    majority_vote_live,
    normalize_live_answer,
)


def test_normalize_live_answer_for_supported_task_types() -> None:
    assert normalize_live_answer("The answer is B.", TASK_CHOICE) == "B"
    assert normalize_live_answer("supported", TASK_CLAIM) == "TRUE"
    assert normalize_live_answer("not enough info", TASK_CLAIM) == "UNKNOWN"
    assert normalize_live_answer("  Rome. ", TASK_FACT_QA) == "rome"


def test_evidence_quality_scores_unknown_as_zero() -> None:
    assert evidence_quality_score("unknown") == 0.0
    assert evidence_quality_score("According to Wikipedia in 1992, the policy changed.") > 0.5


def test_dynamic_adjudication_can_override_plain_majority() -> None:
    outputs = [
        {
            "provider": "weak_a",
            "model": "weak-a",
            "answer": "A",
            "normalized_answer": "A",
            "confidence": 0.55,
            "evidence_quality": 0.2,
        },
        {
            "provider": "weak_b",
            "model": "weak-b",
            "answer": "A",
            "normalized_answer": "A",
            "confidence": 0.55,
            "evidence_quality": 0.2,
        },
        {
            "provider": "strong_c",
            "model": "strong-c",
            "answer": "B",
            "normalized_answer": "B",
            "confidence": 0.95,
            "evidence_quality": 1.0,
        },
    ]
    history = {"weak_a": 0.25, "weak_b": 0.25, "strong_c": 0.95}
    majority = majority_vote_live(outputs)
    dynamic = dynamic_adjudicate_live(TASK_CHOICE, outputs, history)

    assert majority["final_answer"] == "A"
    assert dynamic["final_answer"] == "B"
    assert dynamic["risk_level"] in {"medium", "high"}


def test_build_live_report_contains_decision_and_outputs() -> None:
    outputs = [
        {
            "provider": "qwen",
            "model": "qwen-plus",
            "answer": "FALSE",
            "normalized_answer": "FALSE",
            "confidence": 0.8,
            "evidence_quality": 0.7,
            "evidence": "known policy source",
            "reason": "The claim is contradicted.",
        }
    ]
    majority = majority_vote_live(outputs)
    dynamic = dynamic_adjudicate_live(TASK_CLAIM, outputs, {"qwen": 0.7})
    report = build_live_report(TASK_CLAIM, "The claim.", None, outputs, majority, dynamic)

    assert "ConsensusScope Live Question Report" in report
    assert "Dynamic answer" in report
    assert "qwen" in report

