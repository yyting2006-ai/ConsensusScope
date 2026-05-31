from src.parsing.answer_normalizer import normalize_answer
from src.schemas import QuestionSample


def test_choice_answer_normalization() -> None:
    sample = QuestionSample(id="x", dataset="d", question="q", gold_answer="B", answer_type="choice")
    assert normalize_answer("B. scissors", sample) == "B"


def test_boolean_answer_normalization() -> None:
    sample = QuestionSample(id="x", dataset="d", question="q", gold_answer="false", answer_type="boolean")
    assert normalize_answer("No, this is false.", sample) == "false"
