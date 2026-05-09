from __future__ import annotations

from google.protobuf.message import Message

from omp.core.checksum import sha256_hex
from omp.proto import passport_pb2


def merge(
    passport_a: passport_pb2.OrbPassport,
    passport_b: passport_pb2.OrbPassport,
    *,
    strategy: str = "latest",
) -> passport_pb2.OrbPassport:
    merged = passport_pb2.OrbPassport()
    merged.CopyFrom(passport_a)
    del merged.preferences[:]
    del merged.goals[:]
    del merged.values[:]
    del merged.skills[:]
    del merged.interests[:]
    del merged.relationships[:]
    del merged.memories[:]

    _merge_repeated(merged.preferences, passport_a.preferences, passport_b.preferences, strategy)
    _merge_repeated(merged.goals, passport_a.goals, passport_b.goals, strategy)
    _merge_repeated(merged.values, passport_a.values, passport_b.values, strategy)
    _merge_repeated(merged.skills, passport_a.skills, passport_b.skills, strategy)
    _merge_repeated(merged.interests, passport_a.interests, passport_b.interests, strategy)
    _merge_repeated(
        merged.relationships,
        passport_a.relationships,
        passport_b.relationships,
        strategy,
    )

    memories = _merge_memories(passport_a.memories, passport_b.memories, strategy)
    merged.memories.extend(memories)
    merged.verified = False
    merged.tier = "open"
    return merged


def _merge_repeated(target, values_a, values_b, strategy: str) -> None:
    if strategy == "source_a":
        target.extend(values_a)
    elif strategy == "source_b":
        target.extend(values_b)
    elif strategy in {"latest", "union"}:
        seen = set()
        for item in list(values_a) + list(values_b):
            key = item.SerializeToString(deterministic=True)
            if key not in seen:
                target.append(item)
                seen.add(key)
    else:
        raise ValueError(f"unknown merge strategy: {strategy}")


def _merge_memories(values_a, values_b, strategy: str):
    if strategy == "source_a":
        return list(values_a)
    if strategy == "source_b":
        return list(values_b)
    if strategy == "union":
        by_hash = {}
        for memory in list(values_a) + list(values_b):
            by_hash.setdefault(_content_hash(memory), memory)
        return list(by_hash.values())
    if strategy == "latest":
        by_id = {}
        for memory in list(values_a) + list(values_b):
            key = memory.memory_id or _content_hash(memory)
            current = by_id.get(key)
            if current is None or memory.updated_at >= current.updated_at:
                by_id[key] = memory
        return list(by_id.values())
    raise ValueError(f"unknown merge strategy: {strategy}")


def _content_hash(message: Message) -> str:
    return sha256_hex(message.SerializeToString(deterministic=True))
