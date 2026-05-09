from __future__ import annotations

from omp.inject.adapters.base import BaseAdapter
from omp.inject.prompt import render_prompt
from omp.proto import adapter_pb2, passport_pb2


class OpenAIAdapter(BaseAdapter):
    TARGET_SYSTEM = "openai"
    SUPPORTED_FEATURES = [
        adapter_pb2.ADAPTER_MEMORY_TEXT,
        adapter_pb2.ADAPTER_PREFERENCES,
        adapter_pb2.ADAPTER_SKILLS,
    ]

    def to_system_prompt(self, passport: passport_pb2.OrbPassport) -> str:
        return render_prompt(passport)

