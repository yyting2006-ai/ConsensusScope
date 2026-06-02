from pathlib import Path

from src.esl_writing_feedback import load_esl_writing_profile


def test_esl_writing_profile_exists_and_loads():
    profile_path = Path("profiles/esl_writing.yaml")
    assert profile_path.exists()

    profile = load_esl_writing_profile(profile_path)

    assert profile["domain_name"] == "ESL Writing Feedback"
    assert "grammar" in profile["issue_types"]
    assert "meaning_change" in profile["issue_types"]
    assert "safe_to_show_student" in profile["teacher_safety_labels"]
    assert "teacher_review" in profile["recommended_actions"]
    assert "meaning_change" in profile["risk_reasons"]

