from __future__ import annotations

from src.schemas import ModelAnswer, QuestionSample


def build_discussion_prompt(sample: QuestionSample, peer_answers: list[ModelAnswer]) -> str:
    peers = "\n".join(f"- {a.provider}: {a.answer} ({a.reason})" for a in peer_answers)
    return f"""Reconsider your answer after seeing other models' answers.
Return JSON with answer, reason, confidence, evidence.

Question: {sample.question}
Other model answers:
{peers}
"""
