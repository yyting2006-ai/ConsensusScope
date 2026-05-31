from __future__ import annotations

from abc import ABC, abstractmethod

from src.schemas import ModelAnswer, QuestionSample


class BaseLLMClient(ABC):
    provider: str
    model_name: str

    @abstractmethod
    def answer(self, sample: QuestionSample) -> ModelAnswer:
        """Return one structured model answer for one sample."""
