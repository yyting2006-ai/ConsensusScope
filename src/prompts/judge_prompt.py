from __future__ import annotations

from src.schemas import ModelAnswer, QuestionSample


def build_judge_prompt(sample: QuestionSample, answers: list[ModelAnswer]) -> str:
    answer_lines = "\n".join(
        f"- {a.provider}/{a.model_name}: answer={a.answer}; confidence={a.confidence}; evidence={a.evidence}; reason={a.reason}"
        for a in answers
    )
    return f"""You are a fixed adjudicator. Decide the final answer from model outputs.
Return JSON with answer, reason, confidence, evidence.

Question: {sample.question}
Gold answer is hidden.

Model outputs:
{answer_lines}
"""
