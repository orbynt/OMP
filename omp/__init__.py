from __future__ import annotations

from omp.core.reader import read
from omp.core.writer import write
from omp.exceptions import InvalidOrbFile, OMPError, UnsupportedFeature, VersionMismatch
from omp.inject import inject
from omp.inspect import inspect
from omp.merge import merge
from omp.protos import (
    export_proto_bundle,
    get_ai_schema_context,
    get_all_proto_sources,
    get_proto_bundle,
    get_proto_source,
    list_proto_files,
)
from omp.query import MemoryMatch, query
from omp.schema.convert import export_passport as export
from omp.schema.version import PACKAGE_VERSION, PROTOCOL_VERSION

__version__ = PACKAGE_VERSION

__all__ = [
    "InvalidOrbFile",
    "MemoryMatch",
    "OMPError",
    "PROTOCOL_VERSION",
    "UnsupportedFeature",
    "VersionMismatch",
    "__version__",
    "export",
    "export_proto_bundle",
    "get_ai_schema_context",
    "get_all_proto_sources",
    "get_proto_bundle",
    "get_proto_source",
    "inject",
    "inspect",
    "list_proto_files",
    "merge",
    "query",
    "read",
    "write",
]
