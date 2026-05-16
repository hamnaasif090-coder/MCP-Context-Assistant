"""
api/llm.py
LLM provider abstraction.
Supports:
  - Anthropic Claude (user provides API key)
  - Ollama (fully free, local models like llama3, mistral)
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, AsyncGenerator

import httpx

from config import get_settings
from logger import logger
from prompts.templates import SYSTEM_PROMPT, GUARDRAIL_SYSTEM_NOTE

settings = get_settings()


# ══════════════════════════════════════════════════════════════════════════════
# Base
# ══════════════════════════════════════════════════════════════════════════════

class BaseLLMProvider:
    async def complete(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        raise NotImplementedError

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        # Default: non-streaming fallback
        result = await self.complete(messages, system, max_tokens)
        yield result


# ══════════════════════════════════════════════════════════════════════════════
# Anthropic Provider
# ══════════════════════════════════════════════════════════════════════════════

class AnthropicProvider(BaseLLMProvider):
    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. "
                "Set it in .env or switch LLM_PROVIDER=ollama for a free local model."
            )
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.llm_model

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        system_full = f"{system}\n\n{GUARDRAIL_SYSTEM_NOTE}" if system else GUARDRAIL_SYSTEM_NOTE
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_full,
            messages=messages,
        )
        return response.content[0].text

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        system_full = f"{system}\n\n{GUARDRAIL_SYSTEM_NOTE}" if system else GUARDRAIL_SYSTEM_NOTE
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system_full,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text


# ══════════════════════════════════════════════════════════════════════════════
# Ollama Provider (fully free local)
# ══════════════════════════════════════════════════════════════════════════════

class OllamaProvider(BaseLLMProvider):
    """
    Calls a locally running Ollama instance.
    Install: https://ollama.com  then  `ollama pull llama3`
    """

    def __init__(self):
        self._base_url = settings.ollama_base_url
        self._model = settings.llm_model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120)

    def _build_prompt(self, messages: List[Dict[str, str]], system: str) -> str:
        parts = []
        if system:
            parts.append(f"<|system|>\n{system}")
        for m in messages:
            role = m["role"]
            content = m["content"]
            parts.append(f"<|{role}|>\n{content}")
        parts.append("<|assistant|>")
        return "\n".join(parts)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": ([{"role": "system", "content": system}] if system else []) + messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        try:
            resp = await self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except httpx.ConnectError:
            return (
                "⚠️ Ollama is not running. "
                "Start it with `ollama serve` and ensure you've pulled a model with `ollama pull llama3`."
            )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: str = "",
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self._model,
            "messages": ([{"role": "system", "content": system}] if system else []) + messages,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }
        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if content := data.get("message", {}).get("content"):
                            yield content
                        if data.get("done"):
                            break
        except httpx.ConnectError:
            yield "⚠️ Ollama is not running. Start it with `ollama serve`."


# ══════════════════════════════════════════════════════════════════════════════
# Mock Provider (for testing without any API)
# ══════════════════════════════════════════════════════════════════════════════

class MockProvider(BaseLLMProvider):
    """Returns a canned response; useful for CI/testing."""

    async def complete(self, messages, system="", max_tokens=1024, temperature=0.3) -> str:
        last = messages[-1]["content"] if messages else ""
        return (
            f"[MOCK LLM] Received query: '{last[:80]}'. "
            "Configure ANTHROPIC_API_KEY or LLM_PROVIDER=ollama for real responses."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Factory
# ══════════════════════════════════════════════════════════════════════════════

_llm: Optional[BaseLLMProvider] = None


def get_llm() -> BaseLLMProvider:
    global _llm
    if _llm is not None:
        return _llm

    provider = settings.llm_provider.lower()
    try:
        if provider == "anthropic":
            _llm = AnthropicProvider()
            logger.info(f"LLM: Anthropic ({settings.llm_model})")
        elif provider == "ollama":
            _llm = OllamaProvider()
            logger.info(f"LLM: Ollama ({settings.llm_model}) @ {settings.ollama_base_url}")
        else:
            logger.warning(f"Unknown LLM_PROVIDER '{provider}', using mock")
            _llm = MockProvider()
    except Exception as e:
        logger.warning(f"LLM init failed ({e}), using mock provider")
        _llm = MockProvider()

    return _llm
