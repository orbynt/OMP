from __future__ import annotations

import omp
from omp.core.framer import ChunkType, read_framed_file


def test_write_read_inject_query_export_round_trip(tmp_path):
    path = tmp_path / "memory.orb"

    omp.write(
        path,
        identity={"display_name": "Abhishek"},
        profile={"occupation": "Founder", "website_links": ["https://omp.dev"]},
        memories=[
            {
                "memory_type": "fact",
                "summary": "Abhishek is building OMP protocol",
                "full_content": "OMP moves portable AI memory between systems.",
                "tags": ["engineering", "protocols"],
                "importance": 0.9,
            },
            {
                "kind": "preference",
                "summary": "Prefers concise technical explanations",
                "tags": ["communication"],
            },
        ],
        preferences={"communication.style": "concise but complete"},
        goals=[{"title": "Build OMP", "description": "Publish portable AI memory"}],
        values=[{"statement": "Build ethically", "priority": "high"}],
        skills=[{"name": "protocol design", "description": "Binary interchange"}],
        interests=[{"name": "AI"}],
        relationships=[{"person_name": "OMP", "relationship_type": "project"}],
    )

    raw = path.read_bytes()
    assert raw[:4] == b"ORB1"
    assert raw[-4:] == b"ORBF"
    frame = read_framed_file(path)
    assert [entry.chunk_type for entry in frame.entries] == [
        int(ChunkType.PROTOCOL_METADATA),
        int(ChunkType.IDENTITY),
        int(ChunkType.PROFILE),
        int(ChunkType.PREFERENCES),
        int(ChunkType.GOALS),
        int(ChunkType.VALUES),
        int(ChunkType.SKILLS),
        int(ChunkType.INTERESTS),
        int(ChunkType.RELATIONSHIPS),
        int(ChunkType.MEMORY_BUNDLE),
        int(ChunkType.MEMORY_GRAPH),
        int(ChunkType.ADAPTER_METADATA),
        int(ChunkType.PROVENANCE),
        int(ChunkType.EXPORT_POLICY),
        int(ChunkType.INTEGRITY_METADATA),
    ]

    passport = omp.read(path)
    assert passport.protocol_metadata.protocol_name == "OMP"
    assert passport.protocol_metadata.schema_version == "orbynt.memory.protocol.v1"
    assert passport.identity.display_name == "Abhishek"
    assert passport.profile.occupation == "Founder"
    assert passport.verified is False
    assert passport.tier == "open"
    assert [pref.key for pref in passport.preferences] == ["communication.style"]
    assert passport.goals[0].title == "Build OMP"
    assert passport.values[0].statement == "Build ethically"
    assert passport.interests[0].name == "AI"
    assert passport.relationships[0].person_name == "OMP"
    assert len(passport.memories) == 2
    assert passport.memories[0].memory_type
    assert passport.memories[0].full_content == "OMP moves portable AI memory between systems."

    prompt = omp.inject(passport, target="anthropic")
    assert "TRUST" in prompt
    assert "OPEN (unverified)" in prompt
    assert "Abhishek is building OMP protocol" in prompt

    matches = omp.query(passport, text="portable memory", limit=1)
    assert len(matches) == 1
    assert matches[0].memory.summary == "Abhishek is building OMP protocol"

    exported = omp.export(passport, format="dict")
    assert exported["identity"]["display_name"] == "Abhishek"
    assert exported["protocol_metadata"]["protocol_name"] == "OMP"


def test_merge_latest_keeps_newer_memory(tmp_path):
    a = omp.write(
        tmp_path / "a.orb",
        identity={"display_name": "A"},
        memories=[
            {
                "memory_id": "omp://memory/1",
                "memory_type": "fact",
                "summary": "Old",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ],
    )
    b = omp.write(
        tmp_path / "b.orb",
        identity={"display_name": "B"},
        memories=[
            {
                "memory_id": "omp://memory/1",
                "memory_type": "fact",
                "summary": "New",
                "updated_at": "2026-02-01T00:00:00Z",
            }
        ],
    )

    merged = omp.merge(a, b, strategy="latest")
    assert len(merged.memories) == 1
    assert merged.memories[0].summary == "New"


def test_proto_sources_are_available_to_ai_functions(tmp_path):
    files = omp.list_proto_files()
    assert "memory.proto" in files
    assert "passport.proto" in files

    memory_source = omp.get_proto_source("memory")
    assert "message MemoryRecord" in memory_source
    assert "memory_type = 2" in memory_source

    all_sources = omp.get_all_proto_sources()
    assert all_sources["passport.proto"].startswith('syntax = "proto3";')

    bundle = omp.get_proto_bundle()
    assert "// ===== memory.proto =====" in bundle
    assert "message OrbPassport" in bundle

    out = tmp_path / "omp-protos.txt"
    returned = omp.export_proto_bundle(out)
    assert out.read_text(encoding="utf-8") == returned
