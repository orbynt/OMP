from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable

from omp.proto import memory_pb2, passport_pb2
from omp.schema.builder import memory_type_from_name

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class MemoryMatch:
    score: float
    memory: memory_pb2.MemoryRecord


def query(
    passport: passport_pb2.OrbPassport,
    *,
    text: str = "",
    kind: str | int | None = None,
    tags: Iterable[str] | None = None,
    limit: int = 5,
    min_confidence: float | None = None,
) -> list[MemoryMatch]:
    wanted_kind = memory_type_from_name(kind) if kind is not None else None
    wanted_tags = {tag.lower() for tag in tags or []}
    query_terms = _tokens(text)

    matches: list[MemoryMatch] = []
    for memory in passport.memories:
        if wanted_kind is not None and memory.memory_type != wanted_kind:
            continue
        if wanted_tags and not (wanted_tags & {tag.lower() for tag in memory.tags}):
            continue
        confidence = memory.confidence if memory.confidence else 1.0
        if min_confidence is not None and confidence < min_confidence:
            continue

        score = _score(memory, query_terms, text)
        if query_terms and score <= 0:
            continue
        matches.append(MemoryMatch(score=score, memory=memory))

    matches.sort(key=lambda match: match.score, reverse=True)
    return matches[: max(limit, 0)]


def _score(memory: memory_pb2.MemoryRecord, query_terms: list[str], raw_query: str) -> float:
    if not query_terms:
        return 1.0

    haystack = " ".join([memory.summary, memory.full_content, " ".join(memory.tags)]).lower()
    haystack_terms = _tokens(haystack)
    if not haystack_terms:
        return 0.0

    counts = {term: haystack_terms.count(term) for term in set(haystack_terms)}
    score = 0.0
    for term in query_terms:
        tf = counts.get(term, 0)
        if tf:
            score += 1.0 + math.log(tf)
    if raw_query and raw_query.lower() in haystack:
        score += 2.0
    return score * (memory.confidence if memory.confidence else 1.0)


def _tokens(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]
