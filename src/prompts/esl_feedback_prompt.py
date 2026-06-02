from __future__ import annotations

from typing import Iterable


DEFAULT_RUBRIC = [
    "task_response",
    "organization",
    "coherence",
    "grammar",
    "vocabulary",
    "tone_register",
]


def build_esl_feedback_prompt(
    essay_text: str,
    assignment_prompt: str = "",
    rubric: Iterable[str] | None = None,
) -> str:
    """Build a structured prompt for ESL writing feedback candidates."""
    rubric_items = list(rubric or DEFAULT_RUBRIC)
    rubric_text = "\n".join(f"- {item}" for item in rubric_items)
    assignment = assignment_prompt.strip() or "No assignment prompt was provided."
    essay = essay_text.strip() or "[empty essay]"

    return f"""You are helping a teacher review AI-generated feedback for an ESL writing draft.

Assignment prompt:
{assignment}

Rubric dimensions:
{rubric_text}

Student essay draft:
{essay}

Return exactly one JSON object with a key named "feedback".
"feedback" must be a list of 1 to 6 objects. Each object must use this schema:
target_span, issue_type, suggestion, rationale, confidence, meaning_preservation_risk, student_facing, teacher_review_needed

Allowed issue_type values:
grammar, vocabulary, sentence_structure, coherence, organization, task_response, argument_clarity, tone_register, meaning_change, overcorrection, other

Allowed meaning_preservation_risk values:
low, medium, high, unclear

Rules:
- Focus on concrete, inspectable feedback.
- Do not rewrite the whole essay.
- Do not add claims, facts, or arguments that are not present in the draft or assignment.
- Do not change the student's intended meaning.
- Mark local grammar, punctuation, and wording edits as low risk when they preserve meaning.
- Mark suggestions that may change thesis, argument, task response, stance, or student intent as high risk.
- Set teacher_review_needed to true for medium, high, or unclear meaning-preservation risk.
- Keep student_facing concise, supportive, and non-punitive.
- confidence must be a number from 0 to 1.
- Do not include Markdown.
"""

