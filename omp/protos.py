from __future__ import annotations

from importlib import resources
from pathlib import Path

from omp.exceptions import OMPError

PROTO_FILENAMES = (
    "common.proto",
    "identity.proto",
    "memory.proto",
    "graph.proto",
    "embedding.proto",
    "passport.proto",
    "orb.proto",
    "adapter.proto",
    "encryption.proto",
    "registry.proto",
    "query.proto",
    "response.proto",
)


def list_proto_files() -> list[str]:
    """Return bundled OMP .proto filenames in canonical dependency order."""
    proto_dir = resources.files("omp.proto")
    existing = {
        child.name
        for child in proto_dir.iterdir()
        if child.is_file() and child.name.endswith(".proto")
    }
    ordered = [name for name in PROTO_FILENAMES if name in existing]
    ordered.extend(sorted(existing - set(ordered)))
    return ordered


def get_proto_source(name: str) -> str:
    """Return the source text for one bundled .proto file."""
    filename = _normalise_proto_name(name)
    if filename not in list_proto_files():
        raise OMPError(f"unknown bundled proto file: {name}")
    return (resources.files("omp.proto") / filename).read_text(encoding="utf-8").lstrip("\ufeff")


def get_all_proto_sources() -> dict[str, str]:
    """Return every bundled .proto source keyed by filename."""
    return {name: get_proto_source(name) for name in list_proto_files()}


def get_proto_bundle(*, include_headers: bool = True) -> str:
    """Return all .proto files as one text bundle suitable for AI context."""
    parts: list[str] = []
    for name, source in get_all_proto_sources().items():
        body = source.rstrip()
        if include_headers:
            body = f"// ===== {name} =====\n{body}"
        parts.append(body)
    return "\n\n".join(parts) + "\n"


def get_ai_schema_context() -> str:
    """Return a concise AI-readable schema context containing all .proto files."""
    return (
        "OMP protobuf schema bundle. Use these schemas to parse, validate, "
        "generate, or explain .orb memory passports.\n\n"
        + get_proto_bundle(include_headers=True)
    )


def export_proto_bundle(path: str | Path, *, include_headers: bool = True) -> str:
    """Write the full bundled .proto schema text to a file and return it."""
    output = get_proto_bundle(include_headers=include_headers)
    Path(path).write_text(output, encoding="utf-8")
    return output


def _normalise_proto_name(name: str) -> str:
    filename = name.strip().replace("\\", "/").rsplit("/", 1)[-1]
    if not filename.endswith(".proto"):
        filename = f"{filename}.proto"
    return filename
