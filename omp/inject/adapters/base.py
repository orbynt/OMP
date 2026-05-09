from __future__ import annotations

from abc import ABC, abstractmethod

from omp.proto import adapter_pb2, passport_pb2


class BaseAdapter(ABC):
    TARGET_SYSTEM = "base"
    SUPPORTED_FEATURES: list[int] = []

    @abstractmethod
    def to_system_prompt(self, passport: passport_pb2.OrbPassport) -> str:
        raise NotImplementedError

    def from_system_prompt(self, text: str) -> passport_pb2.OrbPassport:
        raise NotImplementedError("best-effort prompt parsing is not implemented yet")

    def get_degradation_notices(self) -> list[adapter_pb2.DegradationNotice]:
        notices: list[adapter_pb2.DegradationNotice] = []
        if adapter_pb2.ADAPTER_EMBEDDINGS not in self.SUPPORTED_FEATURES:
            notice = adapter_pb2.DegradationNotice()
            notice.feature = adapter_pb2.ADAPTER_EMBEDDINGS
            notice.severity = adapter_pb2.DEGRADATION_LOSSY
            notice.message = "Embedding vectors are not represented in text prompts."
            notices.append(notice)
        return notices

    def get_capabilities(self) -> list[adapter_pb2.AdapterCapability]:
        capabilities: list[adapter_pb2.AdapterCapability] = []
        for feature in (
            adapter_pb2.ADAPTER_MEMORY_TEXT,
            adapter_pb2.ADAPTER_PREFERENCES,
            adapter_pb2.ADAPTER_SKILLS,
            adapter_pb2.ADAPTER_GRAPH_SUMMARY,
            adapter_pb2.ADAPTER_EMBEDDINGS,
        ):
            capability = adapter_pb2.AdapterCapability()
            capability.feature = feature
            capability.supported = feature in self.SUPPORTED_FEATURES
            capabilities.append(capability)
        return capabilities

