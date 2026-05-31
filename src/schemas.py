from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AnswerType = Literal["choice", "boolean", "text"]


class QuestionSample(BaseModel):
    id: str
    dataset: str
    question: str
    gold_answer: str
    answer_type: AnswerType = "text"
    choices: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModelAnswer(BaseModel):
    sample_id: str
    model_name: str
    provider: str
    answer: str
    reason: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = ""
    raw_output: str = ""
    parse_ok: bool = True
    error: str = ""


class AdjudicationResult(BaseModel):
    sample_id: str
    strategy: str
    final_answer: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    risk_type: str = "unknown"
    reliability_score: float = Field(default=0.0, ge=0.0, le=100.0)
    recommendation: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
