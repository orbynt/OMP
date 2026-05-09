from __future__ import annotations

from pathlib import Path

from google.protobuf.message import DecodeError

from omp.core import compressor
from omp.core.framer import ChunkFlag, ChunkType, FramedOrb, read_framed_file
from omp.exceptions import InvalidOrbFile
from omp.proto import (
    adapter_pb2,
    common_pb2,
    embedding_pb2,
    graph_pb2,
    identity_pb2,
    memory_pb2,
    passport_pb2,
)


def read(path: str | Path) -> passport_pb2.OrbPassport:
    frame = read_framed_file(path)
    return passport_from_frame(frame)


def passport_from_frame(frame: FramedOrb) -> passport_pb2.OrbPassport:
    passport = passport_pb2.OrbPassport()

    for chunk in frame.chunks:
        payload = chunk.data
        if chunk.flags & ChunkFlag.COMPRESSED:
            payload = compressor.decompress(payload)

        try:
            if chunk.chunk_type == ChunkType.PROTOCOL_METADATA:
                metadata = passport_pb2.PassportMetadata()
                metadata.ParseFromString(payload)
                passport.protocol_metadata.CopyFrom(metadata)
            elif chunk.chunk_type == ChunkType.IDENTITY:
                identity = identity_pb2.IdentityProfile()
                identity.ParseFromString(payload)
                passport.identity.CopyFrom(identity)
            elif chunk.chunk_type == ChunkType.PROFILE:
                profile = passport_pb2.Profile()
                profile.ParseFromString(payload)
                passport.profile.CopyFrom(profile)
            elif chunk.chunk_type == ChunkType.PREFERENCES:
                preferences = identity_pb2.PreferenceBundle()
                preferences.ParseFromString(payload)
                passport.preferences.extend(preferences.preferences)
            elif chunk.chunk_type == ChunkType.GOALS:
                goals = passport_pb2.GoalBundle()
                goals.ParseFromString(payload)
                passport.goals.extend(goals.goals)
            elif chunk.chunk_type == ChunkType.VALUES:
                values = passport_pb2.ValueBundle()
                values.ParseFromString(payload)
                passport.values.extend(values.values)
            elif chunk.chunk_type == ChunkType.SKILLS:
                skills = identity_pb2.SkillBundle()
                skills.ParseFromString(payload)
                passport.skills.extend(skills.skills)
            elif chunk.chunk_type == ChunkType.INTERESTS:
                interests = identity_pb2.InterestBundle()
                interests.ParseFromString(payload)
                passport.interests.extend(interests.interests)
            elif chunk.chunk_type == ChunkType.RELATIONSHIPS:
                relationships = passport_pb2.RelationshipBundle()
                relationships.ParseFromString(payload)
                passport.relationships.extend(relationships.relationships)
            elif chunk.chunk_type == ChunkType.MEMORY_BUNDLE:
                bundle = memory_pb2.MemoryBundle()
                bundle.ParseFromString(payload)
                passport.memories.extend(bundle.memories)
            elif chunk.chunk_type == ChunkType.MEMORY_GRAPH:
                graph = graph_pb2.MemoryGraph()
                graph.ParseFromString(payload)
                passport.graph.CopyFrom(graph)
            elif chunk.chunk_type == ChunkType.EMBEDDING_INDEX:
                embeddings = embedding_pb2.EmbeddingIndexMetadata()
                embeddings.ParseFromString(payload)
                passport.embeddings.CopyFrom(embeddings)
            elif chunk.chunk_type == ChunkType.ADAPTER_METADATA:
                adapters = adapter_pb2.AdapterMetadataBundle()
                adapters.ParseFromString(payload)
                passport.adapters.extend(adapters.adapters)
            elif chunk.chunk_type == ChunkType.PROVENANCE:
                provenance = passport_pb2.ProvenanceBundle()
                provenance.ParseFromString(payload)
                passport.provenance.extend(provenance.provenance)
            elif chunk.chunk_type == ChunkType.EXPORT_POLICY:
                policy = common_pb2.ExportPolicy()
                policy.ParseFromString(payload)
                passport.export_policy.CopyFrom(policy)
            elif chunk.chunk_type == ChunkType.INTEGRITY_METADATA:
                integrity = passport_pb2.IntegrityMetadata()
                integrity.ParseFromString(payload)
                passport.integrity.CopyFrom(integrity)
        except DecodeError as exc:
            raise InvalidOrbFile(f"failed to decode chunk {chunk.chunk_type}") from exc

    passport.verified = False
    passport.tier = "open"
    return passport
