from __future__ import annotations

from pathlib import Path

from omp.core import compressor
from omp.core.framer import Chunk, ChunkFlag, ChunkType, write_framed_file
from omp.proto import adapter_pb2, identity_pb2, memory_pb2, passport_pb2
from omp.schema.builder import build_passport
from omp.schema.validator import validate_passport
from omp.schema.version import PROTOCOL_MAJOR, PROTOCOL_MINOR, PROTOCOL_PATCH


def write(
    path: str | Path,
    *,
    passport: passport_pb2.OrbPassport | None = None,
    identity: dict | None = None,
    profile: dict | None = None,
    memories: list[dict] | None = None,
    preferences: dict | list[dict] | None = None,
    goals: list[dict] | None = None,
    values: list[dict] | None = None,
    skills: list[dict] | None = None,
    interests: list[dict] | None = None,
    relationships: list[dict] | None = None,
    adapters: list[dict] | None = None,
    provenance: list[dict] | None = None,
    export_policy: dict | None = None,
    compress: bool = False,
    version: tuple[int, int, int] = (PROTOCOL_MAJOR, PROTOCOL_MINOR, PROTOCOL_PATCH),
) -> passport_pb2.OrbPassport:
    if passport is None:
        passport = build_passport(
            identity=identity,
            profile=profile,
            memories=memories,
            preferences=preferences,
            goals=goals,
            values=values,
            skills=skills,
            interests=interests,
            relationships=relationships,
            adapters=adapters,
            provenance=provenance,
            export_policy=export_policy,
            version=version,
        )
    passport.verified = False
    passport.tier = "open"
    passport.protocol_metadata.compression_algorithm = "zstd" if compress else "none"
    validate_passport(passport)

    chunks = _passport_to_chunks(passport, compress_chunks=compress)
    write_framed_file(path, chunks, version=version)
    return passport


def _passport_to_chunks(
    passport: passport_pb2.OrbPassport,
    *,
    compress_chunks: bool,
) -> list[Chunk]:
    preference_bundle = identity_pb2.PreferenceBundle()
    preference_bundle.preferences.extend(passport.preferences)

    goal_bundle = passport_pb2.GoalBundle()
    goal_bundle.goals.extend(passport.goals)

    value_bundle = passport_pb2.ValueBundle()
    value_bundle.values.extend(passport.values)

    skill_bundle = identity_pb2.SkillBundle()
    skill_bundle.skills.extend(passport.skills)

    interest_bundle = identity_pb2.InterestBundle()
    interest_bundle.interests.extend(passport.interests)

    relationship_bundle = passport_pb2.RelationshipBundle()
    relationship_bundle.relationships.extend(passport.relationships)

    memory_bundle = memory_pb2.MemoryBundle()
    memory_bundle.memories.extend(passport.memories)

    adapter_bundle = adapter_pb2.AdapterMetadataBundle()
    adapter_bundle.adapters.extend(passport.adapters)

    provenance_bundle = passport_pb2.ProvenanceBundle()
    provenance_bundle.provenance.extend(passport.provenance)

    ordered_messages = [
        (ChunkType.PROTOCOL_METADATA, passport.protocol_metadata),
        (ChunkType.IDENTITY, passport.identity),
        (ChunkType.PROFILE, passport.profile),
        (ChunkType.PREFERENCES, preference_bundle),
        (ChunkType.GOALS, goal_bundle),
        (ChunkType.VALUES, value_bundle),
        (ChunkType.SKILLS, skill_bundle),
        (ChunkType.INTERESTS, interest_bundle),
        (ChunkType.RELATIONSHIPS, relationship_bundle),
        (ChunkType.MEMORY_BUNDLE, memory_bundle),
        (ChunkType.MEMORY_GRAPH, passport.graph),
    ]
    if passport.embeddings.models or passport.embeddings.vectors:
        ordered_messages.append((ChunkType.EMBEDDING_INDEX, passport.embeddings))
    ordered_messages.extend(
        [
            (ChunkType.ADAPTER_METADATA, adapter_bundle),
            (ChunkType.PROVENANCE, provenance_bundle),
            (ChunkType.EXPORT_POLICY, passport.export_policy),
            (ChunkType.INTEGRITY_METADATA, passport.integrity),
        ]
    )

    output: list[Chunk] = []
    for chunk_type, message in ordered_messages:
        payload = message.SerializeToString(deterministic=True)
        flags = 0
        if compress_chunks:
            payload = compressor.compress(payload)
            flags |= ChunkFlag.COMPRESSED
        output.append(Chunk(int(chunk_type), payload, int(flags)))
    return output


def write_memory_bundle(
    path: str | Path,
    memories: list[dict],
    *,
    display_name: str = "",
) -> passport_pb2.OrbPassport:
    return write(path, identity={"display_name": display_name}, memories=memories)
