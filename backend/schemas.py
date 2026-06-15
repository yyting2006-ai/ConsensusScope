from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EssayReviewRequest(BaseModel):
    essay_id: str = Field(default="USER-ESSAY-001", min_length=1)
    essay_text: str = Field(min_length=1)
    assignment_prompt: str = Field(
        default="Write an opinion essay for an ESL writing class.",
        min_length=1,
    )
    student_level: str = Field(default="upper-intermediate", min_length=1)
    include_stress_tests: bool = False


class BatchReviewRequest(BaseModel):
    essays: List[EssayReviewRequest] = Field(min_length=1)
    include_stress_tests: bool = False


class TeacherDecisionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    feedback_item_id: str = Field(min_length=1)
    teacher_action: str = Field(
        description="accept, edit, reject, needs_more_evidence, or uncertain"
    )
    teacher_corrected_feedback: Optional[str] = None
    teacher_reason: Optional[str] = None
    teacher_id: str = Field(default="anonymous_teacher", min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

