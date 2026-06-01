from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests

from src.llm.base_client import BaseLLMClient
from src.llm.clients import format_http_error
from src.parsing.json_parser import parse_model_json
from src.prompts.answer_prompt import build_answer_messages
from src.schemas import ModelAnswer, QuestionSample


class OpenAICompatibleClient(BaseLLMClient):
    def __init__(
        self,
        provider: str,
        api_key_env: str,
        base_url_env: str,
        model_env: str,
        default_base_url: str,
        default_model: str,
        temperature: float = 0.2,
        max_tokens: int = 800,
        timeout: int = 60,
    ) -> None:
        self.provider = provider
        self.api_key = os.getenv(api_key_env, "")
        self.base_url = os.getenv(base_url_env, default_base_url).rstrip("/")
        self.model_name = os.getenv(model_env, default_model)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def answer(self, sample: QuestionSample) -> ModelAnswer:
        if not self.api_key:
            return ModelAnswer(
                sample_id=sample.id,
                model_name=self.model_name,
                provider=self.provider,
                answer="",
                parse_ok=False,
                error=f"Missing API key for {self.provider}",
            )

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": build_answer_messages(sample),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            if not response.ok:
                raise RuntimeError(format_http_error(response))
            raw = response.json()["choices"][0]["message"]["content"]
            parsed = parse_model_json(raw)
            return ModelAnswer(
                sample_id=sample.id,
                model_name=self.model_name,
                provider=self.provider,
                answer=str(parsed.get("answer", "")),
                reason=str(parsed.get("reason", "")),
                confidence=float(parsed.get("confidence", 0.0)),
                evidence=str(parsed.get("evidence", "")),
                raw_output=raw,
                parse_ok=True,
            )
        except Exception as exc:
            return ModelAnswer(
                sample_id=sample.id,
                model_name=self.model_name,
                provider=self.provider,
                answer="",
                raw_output=json.dumps(payload, ensure_ascii=False),
                parse_ok=False,
                error=str(exc),
            )
