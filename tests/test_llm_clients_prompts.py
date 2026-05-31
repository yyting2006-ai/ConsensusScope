from src.llm.clients import get_client, parse_json_from_text
from src.llm.prompts import build_answer_prompt, build_judge_prompt


def test_parse_plain_json() -> None:
    parsed = parse_json_from_text('{"answer": "A", "confidence": 0.8}')
    assert parsed["answer"] == "A"
    assert parsed["confidence"] == 0.8


def test_parse_fenced_json() -> None:
    parsed = parse_json_from_text('```json\n{"answer": "B", "reason": "ok"}\n```')
    assert parsed["answer"] == "B"


def test_parse_failure_returns_error_dict() -> None:
    parsed = parse_json_from_text("not json")
    assert "raw_output" in parsed
    assert "parse_error" in parsed


def test_build_answer_prompt_contains_required_keys() -> None:
    prompt = build_answer_prompt({"id": "x", "question": "Q?", "options": ""})
    for key in ["answer", "reason", "confidence", "evidence"]:
        assert key in prompt


def test_build_judge_prompt_contains_outputs() -> None:
    prompt = build_judge_prompt(
        {"id": "x", "question": "Q?"},
        [{"provider": "deepseek", "answer": "A", "confidence": 0.7}],
    )
    assert "final_answer" in prompt
    assert "deepseek" in prompt


def test_get_openai_compatible_client_without_key() -> None:
    client = get_client("openai")
    assert client.provider == "openai"
    result = client.call_json('{"answer":"A"}', max_tokens=10)
    assert result["provider"] == "openai"
    assert "request_error" in result
