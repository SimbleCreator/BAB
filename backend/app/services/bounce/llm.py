"""Chat client for any OpenAI-compatible endpoint (default: OpenRouter)."""

import json
import re
from typing import Protocol

import httpx

from app.core.config import get_settings


class LLMError(Exception):
    def __init__(self, message: str, code: str = "model_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class LLMClient(Protocol):
    model: str
    last_model: str | None  # the model that actually answered, when the endpoint says

    async def complete(self, messages: list[dict[str, str]], max_tokens: int) -> str: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float,
        *,
        fallbacks: list[str] | None = None,
        json_mode: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.fallbacks = fallbacks or []
        self.json_mode = json_mode
        self.last_model: str | None = None

    @property
    def is_openrouter(self) -> bool:
        return "openrouter.ai" in self.base_url

    def body(self, messages: list[dict[str, str]], max_tokens: int) -> dict:
        body: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        if self.json_mode:
            body["response_format"] = {"type": "json_object"}
        if self.is_openrouter:
            # Thinking models can spend the whole token budget reasoning and return nothing.
            body["reasoning"] = {"enabled": False}
            if self.fallbacks:
                body["models"] = [self.model, *self.fallbacks]
        return body

    async def complete(self, messages: list[dict[str, str]], max_tokens: int) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=self.body(messages, max_tokens),
                )
        except httpx.TimeoutException as exc:
            raise LLMError("Bounce took too long to answer. Try again.", "model_timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMError("Bounce could not reach the AI service.", "model_unreachable") from exc
        if r.status_code in (401, 403):
            raise LLMError("The AI service rejected the access token.", "model_auth")
        if r.status_code == 402:
            raise LLMError(
                "The AI service has run out of credits for now. Try again later.", "model_credits"
            )
        if r.status_code == 429:
            raise LLMError("The AI service is busy. Try again in a minute.", "model_busy")
        if r.status_code >= 400:
            raise LLMError(f"The AI service returned an error ({r.status_code}).")
        try:
            data = r.json()
            content = data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("The AI service sent an unexpected reply.") from exc
        self.last_model = data.get("model") or self.model
        return content


def get_llm() -> LLMClient | None:
    """The configured client, or None when Bounce is switched off."""
    s = get_settings()
    if not s.ai_enabled:
        return None
    return OpenAICompatibleClient(
        s.ai_base_url,
        s.ai_api_key,
        s.ai_model,
        s.ai_timeout_s,
        fallbacks=s.ai_fallback_list,
        json_mode=s.ai_json_mode,
    )


def extract_json(text: str) -> dict:
    """The first JSON object in the reply (models sometimes add prose or code fences)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start : end + 1])
