from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from pathlib import Path
from typing import Iterable

from omp.core.checksum import sha256
from omp.exceptions import InvalidOrbFile, VersionMismatch
from omp.schema.version import PROTOCOL_MAJOR

MAGIC = b"ORB1"
FOOTER_MAGIC = b"ORBF"

HEADER_STRUCT = struct.Struct("<4sHHHHII")
CHUNK_ENTRY_STRUCT = struct.Struct("<IIQQ")
CHUNK_PREAMBLE_STRUCT = struct.Struct("<IQ")
FOOTER_STRUCT = struct.Struct("<Q32s4s")

HEADER_FIXED_LENGTH = HEADER_STRUCT.size
CHUNK_ENTRY_LENGTH = CHUNK_ENTRY_STRUCT.size
CHUNK_PREAMBLE_LENGTH = CHUNK_PREAMBLE_STRUCT.size
FOOTER_LENGTH = FOOTER_STRUCT.size


class FileFlag(IntFlag):
    HAS_COMPRESSION = 1 << 0
    HAS_ENCRYPTION = 1 << 1
    HAS_SIGNATURE = 1 << 2
    HAS_GRAPH = 1 << 3
    HAS_EMBEDDINGS = 1 << 4
    HAS_ADAPTERS = 1 << 5


class ChunkFlag(IntFlag):
    COMPRESSED = 1 << 0
    ENCRYPTED = 1 << 1
    OPTIONAL = 1 << 2


class ChunkType(IntEnum):
    PROTOCOL_METADATA = 1
    IDENTITY = 2
    MEMORY_BUNDLE = 3
    MEMORY_GRAPH = 4
    EMBEDDING_INDEX = 5
    ADAPTER_METADATA = 6
    REGISTRY_SNAPSHOT = 7
    EXPORT_POLICY = 8
    PROFILE = 9
    PREFERENCES = 10
    GOALS = 11
    VALUES = 12
    SKILLS = 13
    INTERESTS = 14
    RELATIONSHIPS = 15
    PROVENANCE = 16
    INTEGRITY_METADATA = 17
    CUSTOM_EXTENSION = 1000


KNOWN_CHUNK_TYPES = {item.value for item in ChunkType}
OPEN_FORBIDDEN_FILE_FLAGS = FileFlag.HAS_ENCRYPTION | FileFlag.HAS_SIGNATURE
OPEN_FORBIDDEN_CHUNK_FLAGS = ChunkFlag.ENCRYPTED
RESERVED_FILE_FLAG_MASK = ~sum(flag.value for flag in FileFlag)
RESERVED_CHUNK_FLAG_MASK = ~sum(flag.value for flag in ChunkFlag)


@dataclass(frozen=True)
class Chunk:
    chunk_type: int
    data: bytes
    flags: int = 0


@dataclass(frozen=True)
class ChunkEntry:
    chunk_type: int
    chunk_flags: int
    chunk_offset: int
    chunk_length: int


@dataclass(frozen=True)
class FramedOrb:
    version: tuple[int, int, int]
    flags: int
    chunks: list[Chunk]
    entries: list[ChunkEntry]
    checksum: bytes


def frame_chunks(
    chunks: Iterable[Chunk],
    *,
    version: tuple[int, int, int] = (1, 0, 0),
) -> bytes:
    chunk_list = list(chunks)
    flags = _derive_file_flags(chunk_list)
    header_length = HEADER_FIXED_LENGTH + len(chunk_list) * CHUNK_ENTRY_LENGTH

    entries: list[ChunkEntry] = []
    records: list[bytes] = []
    offset = header_length
    for chunk in chunk_list:
        _validate_chunk_for_write(chunk)
        record = CHUNK_PREAMBLE_STRUCT.pack(chunk.chunk_type, len(chunk.data)) + chunk.data
        entries.append(
            ChunkEntry(
                chunk_type=chunk.chunk_type,
                chunk_flags=chunk.flags,
                chunk_offset=offset,
                chunk_length=len(chunk.data),
            )
        )
        records.append(record)
        offset += len(record)

    major, minor, patch = version
    header = HEADER_STRUCT.pack(
        MAGIC,
        major,
        minor,
        patch,
        flags,
        header_length,
        len(chunk_list),
    )
    table = b"".join(
        CHUNK_ENTRY_STRUCT.pack(
            entry.chunk_type,
            entry.chunk_flags,
            entry.chunk_offset,
            entry.chunk_length,
        )
        for entry in entries
    )
    body = header + table + b"".join(records)
    footer = FOOTER_STRUCT.pack(len(body) + FOOTER_LENGTH, sha256(body), FOOTER_MAGIC)
    return body + footer


def parse_framed(data: bytes) -> FramedOrb:
    if len(data) < HEADER_FIXED_LENGTH + FOOTER_LENGTH:
        raise InvalidOrbFile("file is too small to be a valid .orb container")

    magic, major, minor, patch, flags, header_length, chunk_count = HEADER_STRUCT.unpack_from(
        data, 0
    )
    if magic != MAGIC:
        raise InvalidOrbFile("invalid .orb magic bytes")
    if major > PROTOCOL_MAJOR:
        raise VersionMismatch(f"unsupported OMP major version {major}")
    _validate_file_flags(flags)

    minimum_header_length = HEADER_FIXED_LENGTH + chunk_count * CHUNK_ENTRY_LENGTH
    if header_length < minimum_header_length:
        raise InvalidOrbFile("header_length is shorter than the chunk table")
    if header_length > len(data) - FOOTER_LENGTH:
        raise InvalidOrbFile("header_length points beyond the file body")

    footer_start = len(data) - FOOTER_LENGTH
    total_length, digest, footer_magic = FOOTER_STRUCT.unpack_from(data, footer_start)
    if footer_magic != FOOTER_MAGIC:
        raise InvalidOrbFile("invalid .orb footer magic")
    if total_length != len(data):
        raise InvalidOrbFile("footer total_file_length does not match actual file size")
    if sha256(data[:footer_start]) != digest:
        raise InvalidOrbFile("footer SHA-256 checksum mismatch")

    entries = _parse_entries(data, chunk_count)
    chunks: list[Chunk] = []
    for entry in entries:
        _validate_entry(entry, footer_start, header_length)
        if entry.chunk_type not in KNOWN_CHUNK_TYPES:
            if entry.chunk_flags & ChunkFlag.OPTIONAL:
                continue
            raise VersionMismatch(f"unknown required chunk type {entry.chunk_type}")

        actual_type, actual_length = CHUNK_PREAMBLE_STRUCT.unpack_from(data, entry.chunk_offset)
        if actual_type != entry.chunk_type:
            raise InvalidOrbFile("chunk table type does not match chunk payload type")
        if actual_length != entry.chunk_length:
            raise InvalidOrbFile("chunk table length does not match chunk payload length")

        payload_start = entry.chunk_offset + CHUNK_PREAMBLE_LENGTH
        payload_end = payload_start + entry.chunk_length
        chunks.append(
            Chunk(
                chunk_type=entry.chunk_type,
                flags=entry.chunk_flags,
                data=data[payload_start:payload_end],
            )
        )

    return FramedOrb(
        version=(major, minor, patch),
        flags=flags,
        chunks=chunks,
        entries=entries,
        checksum=digest,
    )


def write_framed_file(
    path: str | Path,
    chunks: Iterable[Chunk],
    *,
    version: tuple[int, int, int] = (1, 0, 0),
) -> bytes:
    data = frame_chunks(chunks, version=version)
    Path(path).write_bytes(data)
    return data


def read_framed_file(path: str | Path) -> FramedOrb:
    return parse_framed(Path(path).read_bytes())


def _derive_file_flags(chunks: list[Chunk]) -> int:
    flags = FileFlag(0)
    for chunk in chunks:
        if chunk.flags & ChunkFlag.COMPRESSED:
            flags |= FileFlag.HAS_COMPRESSION
        if chunk.flags & ChunkFlag.ENCRYPTED:
            flags |= FileFlag.HAS_ENCRYPTION
        if chunk.chunk_type == ChunkType.MEMORY_GRAPH:
            flags |= FileFlag.HAS_GRAPH
        if chunk.chunk_type == ChunkType.EMBEDDING_INDEX:
            flags |= FileFlag.HAS_EMBEDDINGS
        if chunk.chunk_type == ChunkType.ADAPTER_METADATA:
            flags |= FileFlag.HAS_ADAPTERS
    _validate_file_flags(int(flags))
    return int(flags)


def _validate_chunk_for_write(chunk: Chunk) -> None:
    if chunk.flags & RESERVED_CHUNK_FLAG_MASK:
        raise InvalidOrbFile(f"reserved chunk flags are set: {chunk.flags}")
    if chunk.flags & OPEN_FORBIDDEN_CHUNK_FLAGS:
        raise InvalidOrbFile("open-tier .orb files cannot contain encrypted chunks")
    if chunk.chunk_type == ChunkType.CUSTOM_EXTENSION and not (
        chunk.flags & ChunkFlag.OPTIONAL
    ):
        raise InvalidOrbFile("CUSTOM_EXTENSION chunks must be flagged OPTIONAL")


def _validate_file_flags(flags: int) -> None:
    if flags & RESERVED_FILE_FLAG_MASK:
        raise InvalidOrbFile(f"reserved file flags are set: {flags}")
    if flags & OPEN_FORBIDDEN_FILE_FLAGS:
        raise InvalidOrbFile("open-tier .orb files cannot set encryption/signature flags")


def _parse_entries(data: bytes, chunk_count: int) -> list[ChunkEntry]:
    entries: list[ChunkEntry] = []
    offset = HEADER_FIXED_LENGTH
    for _ in range(chunk_count):
        chunk_type, chunk_flags, chunk_offset, chunk_length = CHUNK_ENTRY_STRUCT.unpack_from(
            data, offset
        )
        if chunk_flags & RESERVED_CHUNK_FLAG_MASK:
            raise InvalidOrbFile(f"reserved chunk flags are set: {chunk_flags}")
        if chunk_flags & OPEN_FORBIDDEN_CHUNK_FLAGS:
            raise InvalidOrbFile("open-tier .orb files cannot contain encrypted chunks")
        entries.append(ChunkEntry(chunk_type, chunk_flags, chunk_offset, chunk_length))
        offset += CHUNK_ENTRY_LENGTH
    return entries


def _validate_entry(entry: ChunkEntry, footer_start: int, header_length: int) -> None:
    if entry.chunk_offset < header_length:
        raise InvalidOrbFile("chunk offset points inside the header")
    payload_start = entry.chunk_offset + CHUNK_PREAMBLE_LENGTH
    payload_end = payload_start + entry.chunk_length
    if payload_start > footer_start or payload_end > footer_start:
        raise InvalidOrbFile("chunk extends beyond the file body")
