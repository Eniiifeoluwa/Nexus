"""
Reusable Groq LLM wrapper with retry logic, token tracking, and structured outputs.
Abstracts over the Groq API so agents remain provider-agnostic.
"""

import time
import logging
from typing import Any, Optional
from functools import wraps

from groq import Groq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


def _log_usage(model: str, usage: Any, start: float) -> dict:
    latency = round(time.time() - start, 3)
    stats = {
        "model": model,
        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
        "completion_tokens": getattr(usage, "completion_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
        "latency_s": latency,
    }
    logger.debug("LLM usage: %s", stats)
    return stats


class GroqLLMWrapper:
    """
    Production-grade wrapper around the Groq inference API.

    Supports:
      - Multiple model aliases (primary / fast / code)
      - Automatic retries with exponential back-off
      - Token-usage tracking returned alongside every response
      - JSON-mode structured outputs
      - System-prompt injection
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama3-70b-8192",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self.client = Groq(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._total_tokens: int = 0

    # ── Core call ─────────────────────────────────────────────────────────────

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        model_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Send a completion request to Groq.

        Returns
        -------
        {
            "content": str,
            "usage": {prompt_tokens, completion_tokens, total_tokens, latency_s},
        }
        """
        model = model_override or self.model
        temperature = temperature_override if temperature_override is not None else self.temperature

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.time()
        response = self.client.chat.completions.create(**kwargs)
        usage = _log_usage(model, response.usage, start)

        self._total_tokens += usage["total_tokens"]
        content = response.choices[0].message.content or ""

        return {"content": content, "usage": usage}

    # ── Convenience helpers ───────────────────────────────────────────────────

    def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> dict[str, Any]:
        """Wrapper that enables json_mode automatically."""
        return self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            model_override=model_override,
        )

    @property
    def total_tokens_used(self) -> int:
        return self._total_tokens

    def reset_token_counter(self) -> None:
        self._total_tokens = 0


def build_llm(role: str = "primary") -> GroqLLMWrapper:
    """
    Factory that returns a GroqLLMWrapper configured for the requested role.

    Roles
    -----
    primary  → llama3-70b  (general reasoning)
    fast     → mixtral-8x7b  (speed-optimised subtasks)
    code     → llama3-70b  (code generation)
    """
    from config.settings import settings

    model_map = {
        "primary": settings.GROQ_MODEL_PRIMARY,
        "fast": settings.GROQ_MODEL_FAST,
        "code": settings.GROQ_MODEL_CODE,
    }
    model = model_map.get(role, settings.GROQ_MODEL_PRIMARY)
    return GroqLLMWrapper(
        api_key=settings.GROQ_API_KEY,
        model=model,
        temperature=settings.GROQ_TEMPERATURE,
        max_tokens=settings.GROQ_MAX_TOKENS,
    )
