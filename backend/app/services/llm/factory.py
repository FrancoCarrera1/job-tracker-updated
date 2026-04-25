from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.services.llm.base import LLMProvider


@lru_cache
def get_llm() -> LLMProvider:
    s = get_settings()
    if s.llm_provider == "anthropic":
        from app.services.llm.anthropic_provider import AnthropicProvider

        if not s.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return AnthropicProvider(api_key=s.anthropic_api_key, model=s.llm_model)

    if s.llm_provider == "openai":
        from app.services.llm.openai_provider import OpenAIProvider

        if not s.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        return OpenAIProvider(api_key=s.openai_api_key, model=s.llm_model)

    if s.llm_provider == "ollama":
        from app.services.llm.ollama_provider import OllamaProvider

        return OllamaProvider(base_url=s.ollama_base_url, model=s.llm_model)

    raise ValueError(f"Unknown LLM provider: {s.llm_provider}")
