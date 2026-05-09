from __future__ import annotations

import pytest

from omp.core.framer import Chunk, ChunkFlag, ChunkType, frame_chunks, parse_framed
from omp.exceptions import InvalidOrbFile, VersionMismatch
from omp.proto import memory_pb2


def test_unknown_required_chunk_is_rejected():
    data = frame_chunks([Chunk(4242, b"payload")])

    with pytest.raises(VersionMismatch):
        parse_framed(data)


def test_unknown_optional_chunk_is_skipped():
    bundle = memory_pb2.MemoryBundle()
    data = frame_chunks(
        [
            Chunk(4242, b"payload", int(ChunkFlag.OPTIONAL)),
            Chunk(
                int(ChunkType.MEMORY_BUNDLE),
                bundle.SerializeToString(deterministic=True),
            ),
        ]
    )

    frame = parse_framed(data)
    assert [chunk.chunk_type for chunk in frame.chunks] == [int(ChunkType.MEMORY_BUNDLE)]


def test_footer_checksum_is_validated():
    data = bytearray(frame_chunks([Chunk(int(ChunkType.MEMORY_BUNDLE), b"")]))
    data[-45] ^= 0x01

    with pytest.raises(InvalidOrbFile):
        parse_framed(bytes(data))

