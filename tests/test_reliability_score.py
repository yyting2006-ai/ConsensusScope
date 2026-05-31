from src.evaluation.reliability_score import compute_reliability_score
from src.schemas import ModelAnswer, QuestionSample


def test_reliability_score_range() -> None:
    sample = QuestionSample(id="s1", dataset="d", question="q", gold_answer="B", answer_type="choice")
    answers = [
        ModelAnswer(sample_id="s1", provider="a", model_name="m1", answer="B", confidence=0.8, evidence="scissors cut paper"),
        ModelAnswer(sample_id="s1", provider="b", model_name="m2", answer="B", confidence=0.7, evidence="common use"),
    ]
    score = compute_reliability_score(sample, answers, "B")
    assert 0 <= score <= 100
