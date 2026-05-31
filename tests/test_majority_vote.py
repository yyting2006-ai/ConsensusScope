from src.adjudication.majority_vote import majority_vote
from src.schemas import ModelAnswer, QuestionSample


def test_majority_vote_returns_majority_choice() -> None:
    sample = QuestionSample(id="s1", dataset="d", question="q", gold_answer="B", answer_type="choice")
    answers = [
        ModelAnswer(sample_id="s1", provider="a", model_name="m1", answer="B", confidence=0.8),
        ModelAnswer(sample_id="s1", provider="b", model_name="m2", answer="B", confidence=0.7),
        ModelAnswer(sample_id="s1", provider="c", model_name="m3", answer="A", confidence=0.6),
    ]
    result = majority_vote(sample, answers)
    assert result.final_answer == "B"
    assert result.confidence == 2 / 3
