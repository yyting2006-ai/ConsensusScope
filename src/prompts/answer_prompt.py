from __future__ import annotations

from typing import Dict, List

from src.schemas import QuestionSample


SYSTEM_PROMPT = (
    "You are an independent model in a reliability evaluation experiment. "
    "Return only one valid JSON object."
)


def build_answer_messages(sample: QuestionSample) -> List[Dict[str, str]]:
    choices = "\n".join(sample.choices or [])
    user_prompt = f"""Answer the question independently.

Return JSON with exactly these keys:
answer, reason, confidence, evidence

Rules:
- answer: shortest final answer. For multiple-choice questions, return only the option letter.
- reason: one concise reason.
- confidence: number from 0 to 1.
- evidence: short evidence phrase or "unknown".

Dataset: {sample.dataset}
Answer type: {sample.answer_type}
Question:
{sample.question}

Choices:
{choices}
"""
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]
