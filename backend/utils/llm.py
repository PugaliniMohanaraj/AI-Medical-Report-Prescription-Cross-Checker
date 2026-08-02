"""LLM provider interface — OpenAI and local Llama (Ollama) behind one contract."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from backend.utils.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM provider call fails."""


class LLMClient(ABC):
    """Common interface for chat completions used by extraction / RAG."""

    provider_name: str

    @abstractmethod
    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Return the assistant message content as a string."""


class OpenAIClient(LLMClient):
    """OpenAI Chat Completions API client."""

    provider_name = "openai"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        self.settings = settings
        self.model = settings.openai_model
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.default_temperature = settings.llm_temperature
        self.default_max_tokens = settings.llm_max_tokens

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.default_temperature if temperature is None else temperature,
            "max_tokens": self.default_max_tokens if max_tokens is None else max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LLMError(f"OpenAI request failed ({exc.response.status_code}): {detail}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenAI request failed: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected OpenAI response shape") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError("OpenAI returned an empty completion")
        return content


class OllamaClient(LLMClient):
    """Local Llama (and other models) via the Ollama HTTP API."""

    provider_name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.ollama_model
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.default_temperature = settings.llm_temperature
        self.default_max_tokens = settings.llm_max_tokens

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": self.default_temperature if temperature is None else temperature,
                "num_predict": self.default_max_tokens if max_tokens is None else max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise LLMError(f"Ollama request failed ({exc.response.status_code}): {detail}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc

        content = (data.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMError("Ollama returned an empty completion")
        return content


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    """
    Factory returning the configured LLM client.

    Switch providers with ``LLM_PROVIDER=openai|ollama``.
    """
    settings = settings or get_settings()

    if settings.llm_provider == "openai":
        return OpenAIClient(settings)
    if settings.llm_provider == "ollama":
        return OllamaClient(settings)

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


# Backwards-compatible alias used by earlier scaffold code.
def get_llm(settings: Settings | None = None) -> LLMClient:
    return get_llm_client(settings)
