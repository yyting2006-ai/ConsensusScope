from src.adjudication.risk_classifier import classify_risk
from src.schemas import ModelAnswer, QuestionSample


def test_true_consensus() -> None:
    sample = QuestionSample(id="s1", dataset="d", question="q", gold_answer="true", answer_type="boolean")
    answers = [
        ModelAnswer(sample_id="s1", provider="a", model_name="m1", answer="true", confidence=0.9),
        ModelAnswer(sample_id="s1", provider="b", model_name="m2", answer="yes", confidence=0.8),
        ModelAnswer(sample_id="s1", provider="c", model_name="m3", answer="true", confidence=0.7),
    ]
    assert classify_risk(sample, answers, "true") == "真实共识"
