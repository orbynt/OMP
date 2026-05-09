from __future__ import annotations

from omp.inject.adapters.base import BaseAdapter
from omp.inject.prompt import render_prompt
from omp.proto import adapter_pb2, passport_pb2


class AnthropicAdapter(BaseAdapter):
    TARGET_SYSTEM = "anthropic"
    SUPPORTED_FEATURES = [
        adapter_pb2.ADAPTER_MEMORY_TEXT,
        adapter_pb2.ADAPTER_PREFERENCES,
        adapter_pb2.ADAPTER_SKILLS,
        adapter_pb2.ADAPTER_GRAPH_SUMMARY,
    ]

    def to_system_prompt(self, passport: passport_pb2.OrbPassport) -> str:
        return render_prompt(passport, include_graph=True)

