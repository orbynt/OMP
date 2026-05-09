from __future__ import annotations

from omp.exceptions import UnsupportedFeature


def _zstd():
    try:
        import zstandard as zstd
    except ImportError as exc:
        raise UnsupportedFeature(
            "zstandard is required for compressed .orb chunks. Install omp with zstandard."
        ) from exc
    return zstd


def compress(data: bytes) -> bytes:
    zstd = _zstd()
    return zstd.ZstdCompressor().compress(data)


def decompress(data: bytes) -> bytes:
    zstd = _zstd()
    return zstd.ZstdDecompressor().decompress(data)

