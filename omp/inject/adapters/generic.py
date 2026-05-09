from __future__ import annotations

from omp.inject.adapters.base import BaseAdapter
from omp.inject.prompt import render_prompt
from omp.proto import adapter_pb2, passport_pb2


class GenericAdapter(BaseAdapter):
    TARGET_SYSTEM = "generic"
    SUPPORTED_FEATURES = [adapter_pb2.ADAPTER_MEMORY_TEXT]

    def to_system_prompt(self, passport: passport_pb2.OrbPassport) -> str:
        return render_prompt(passport)

