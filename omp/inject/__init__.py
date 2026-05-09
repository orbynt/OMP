from __future__ import annotations

from omp.inject.adapters import AnthropicAdapter, GeminiAdapter, GenericAdapter, OpenAIAdapter
from omp.proto import passport_pb2

_ADAPTERS = {
    "generic": GenericAdapter,
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "claude": AnthropicAdapter,
    "gemini": GeminiAdapter,
}


def inject(passport: passport_pb2.OrbPassport, target: str = "generic") -> str:
    adapter_type = _ADAPTERS.get((target or "generic").lower())
    if adapter_type is None:
        adapter_type = GenericAdapter
    return adapter_type().to_system_prompt(passport)


__all__ = ["inject"]

