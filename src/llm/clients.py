from __future__ import annotations

import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from src.config import PROJECT_ROOT


logger = logging.getLogger(__name__)


DEFAULT_TIMEOUT_SEC = 60
DEFAULT_RETRIES = 2


PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "deepseek": {
        "api_key": "DEEPSEEK_API_KEY",
        "base_url": "DEEPSEEK_BASE_URL",
        "model": "DEEPSEEK_MODEL",
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
    },
    "qwen": {
        "api_key": "QWEN_API_KEY",
        "base_url": "QWEN_BASE_URL",
        "model": "QWEN_MODEL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "glm": {
        "api_key": "GLM_API_KEY",
        "base_url": "GLM_BASE_URL",
        "model": "GLM_MODEL",
        "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
    },
    "kimi": {
        "api_key": "KIMI_API_KEY",
        "base_url": "KIMI_BASE_URL",
        "model": "KIMI_MODEL",
        "default_base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
    },
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "base_url": "OPENAI_BASE_URL",
        "model": "OPENAI_MODEL",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
    "judge": {
        "api_key": "JUDGE_API_KEY",
        "base_url": "JUDGE_BASE_URL",
        "model": "JUDGE_MODEL",
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
    },
}


@dataclass(frozen=True)
class ClientConfig:
    provider: str
    api_key: str
    base_url: str
    model: str
    timeout: int = DEFAULT_TIMEOUT_SEC


class BaseLLMClient(ABC):
    """Abstract client used by experiment runners."""

    provider: str
    model: str

    @abstractmethod
    def call_json(self, prompt: str, temperature: float = 0.2, max_tokens: int = 800) -> Dict[str, Any]:
        """Call a model and return parsed JSON or an error dictionary."""


class OpenAICompatibleClient(BaseLLMClient):
    """Client for OpenAI-compatible `/chat/completions` APIs."""

    def __init__(self, config: ClientConfig, session: Optional[requests.Session] = None) -> None:
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.session = session or requests.Session()

    @property
    def is_available(self) -> bool:
        return bool(self.config.api_key)

    def call_json(self, prompt: str, temperature: float = 0.2, max_tokens: int = 800) -> Dict[str, Any]:
        if not self.config.api_key:
            message = f"Missing API key for provider={self.provider}"
            logger.warning(message)
            return {
                "raw_output": "",
                "parse_error": "",
                "request_error": message,
                "provider": self.provider,
                "model": self.model,
            }

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "You must output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"

        last_error = ""
        for attempt in range(1, DEFAULT_RETRIES + 2):
            try:
                response = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                raw_output = _extract_message_content(response.json())
                parsed = parse_json_from_text(raw_output)
                parsed.setdefault("raw_output", raw_output)
                parsed.setdefault("provider", self.provider)
                parsed.setdefault("model", self.model)
                return parsed
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "LLM call failed provider=%s model=%s attempt=%s error=%s",
                    self.provider,
                    self.model,
                    attempt,
                    last_error,
                )
                if attempt <= DEFAULT_RETRIES:
                    time.sleep(0.8 * attempt)

        return {
            "raw_output": "",
            "parse_error": last_error,
            "request_error": last_error,
            "provider": self.provider,
            "model": self.model,
        }


def _extract_message_content(response_json: Dict[str, Any]) -> str:
    try:
        return str(response_json["choices"][0]["message"]["content"])
    except Exception as exc:
        raise ValueError(f"Unexpected chat completion response shape: {exc}") from exc


def parse_json_from_text(text: str) -> Dict[str, Any]:
    """Parse JSON from raw model text, including fenced ```json blocks."""

    raw = text or ""
    candidates = []

    fenced = re.findall(r"```(?:json|JSON)?\s*(.*?)```", raw, flags=re.S)
    candidates.extend(block.strip() for block in fenced if block.strip())
    candidates.append(raw.strip())

    object_match = re.search(r"\{.*\}", raw, flags=re.S)
    if object_match:
        candidates.append(object_match.group(0))

    last_error = ""
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("Parsed JSON is not an object")
        except Exception as exc:
            last_error = str(exc)

    return {"raw_output": raw, "parse_error": last_error or "No JSON object found"}


def _load_client_config(model_name: str) -> ClientConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    key = model_name.lower().strip()
    if key not in PROVIDER_CONFIG:
        supported = ", ".join(sorted(PROVIDER_CONFIG))
        raise ValueError(f"Unsupported model_name={model_name!r}. Supported: {supported}")

    cfg = PROVIDER_CONFIG[key]
    return ClientConfig(
        provider=key,
        api_key=os.getenv(cfg["api_key"], ""),
        base_url=os.getenv(cfg["base_url"], cfg["default_base_url"]).rstrip("/"),
        model=os.getenv(cfg["model"], cfg["default_model"]),
    )


def get_client(model_name: str) -> OpenAICompatibleClient:
    """Create a configured client for deepseek/qwen/glm/kimi/openai/judge."""

    return OpenAICompatibleClient(_load_client_config(model_name))
