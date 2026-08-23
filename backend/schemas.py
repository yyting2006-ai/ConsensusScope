from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,32}$"


def normalize_optional_email(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not separator or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("enter a valid email address")
    return normalized


class RegisterRequest(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)
    email: Optional[str] = Field(default=None, max_length=254)
    privacy_acknowledged: bool

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        return normalize_optional_email(value)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class ProfileUpdateRequest(BaseModel):
    display_name: str = Field(default="", max_length=80)
    email: Optional[str] = Field(default=None, max_length=254)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        return normalize_optional_email(value)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProductFeedbackRequest(BaseModel):
    category: str = Field(pattern=r"^(bug|feature|usability|output_quality|other)$")
    rating: int = Field(ge=1, le=5)
    message: str = Field(min_length=5, max_length=4000)
    page: Optional[str] = Field(default=None, max_length=120)
    allow_contact: bool = False

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        return value.strip()


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
