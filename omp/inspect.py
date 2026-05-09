from __future__ import annotations

from collections import Counter
from pathlib import Path

from omp.core.framer import read_framed_file
from omp.core.reader import read
from omp.schema.builder import memory_type_name


def inspect(path: str | Path) -> str:
    frame = read_framed_file(path)
    passport = read(path)
    counts = Counter(memory_type_name(memory.memory_type) for memory in passport.memories)
    kinds = ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))
    size = Path(path).stat().st_size
    summary = [
        f"File       : {path}",
        f"Size       : {_format_size(size)}",
        "OMP Tier   : OPEN (unverified)",
        f"Version    : {'.'.join(str(part) for part in frame.version)}",
        f"Identity   : {passport.identity.display_name or '(unnamed)'}",
        f"Memories   : {len(passport.memories)} records"
        + (f" ({kinds})" if kinds else ""),
        f"Graph      : {len(passport.graph.nodes)} nodes, {len(passport.graph.edges)} edges",
        "Checksum   : valid",
        "Signature  : none (open tier)",
    ]
    output = "\n".join(summary)
    print(output)
    return output


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
