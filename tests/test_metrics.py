from src.evaluation.metrics import answer_consistency_rate
from src.schemas import ModelAnswer, QuestionSample


def test_answer_consistency_rate() -> None:
    sample = QuestionSample(id="s1", dataset="d", question="q", gold_answer="A", answer_type="choice")
    answers = [
        ModelAnswer(sample_id="s1", provider="a", model_name="m1", answer="A"),
        ModelAnswer(sample_id="s1", provider="b", model_name="m2", answer="A"),
        ModelAnswer(sample_id="s1", provider="c", model_name="m3", answer="B"),
    ]
    assert answer_consistency_rate(sample, answers) == 2 / 3
