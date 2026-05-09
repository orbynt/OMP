from __future__ import annotations

from textwrap import shorten

from omp.proto import passport_pb2
from omp.schema.builder import memory_type_name


def render_prompt(
    passport: passport_pb2.OrbPassport,
    *,
    include_graph: bool = False,
) -> str:
    lines = [
        f"[OMP MEMORY PASSPORT v{passport.protocol_metadata.protocol_version or '1.0.0'} - OPEN TIER - UNVERIFIED]",
        "",
        "IDENTITY",
        f"  Name      : {passport.identity.display_name or '(unnamed)'}",
        f"  ID        : {passport.identity.identity_id}",
        f"  Namespace : {passport.identity.namespace_id}",
        "",
        "PREFERENCES",
    ]
    if passport.preferences:
        lines.extend(f"  {pref.key} = {pref.value}" for pref in passport.preferences)
    else:
        lines.append("  (none)")

    lines.extend(["", "VALUES"])
    if passport.values:
        lines.extend(f"  - {value.statement}" for value in passport.values)
    else:
        lines.append("  (none)")

    lines.extend(["", "GOALS"])
    if passport.goals:
        for goal in passport.goals:
            suffix = f": {goal.description}" if goal.description else ""
            lines.append(f"  - {goal.title}{suffix}")
    else:
        lines.append("  (none)")

    lines.extend(["", "SKILLS"])
    if passport.skills:
        for skill in passport.skills:
            suffix = f": {skill.description}" if skill.description else ""
            lines.append(f"  - {skill.name}{suffix}")
    else:
        lines.append("  (none)")

    lines.extend(["", f"MEMORIES ({len(passport.memories)} records)"])
    if passport.memories:
        for memory in passport.memories:
            label = memory_type_name(memory.memory_type).upper()
            lines.append(f"  [{label}] {memory.summary}")
            if memory.full_content:
                lines.append(f"    {shorten(memory.full_content, width=500, placeholder='...')}")
            if memory.tags:
                lines.append(f"    Tags: {', '.join(memory.tags)}")
    else:
        lines.append("  (none)")

    if include_graph:
        lines.extend(["", "GRAPH"])
        if passport.graph.edges:
            for edge in passport.graph.edges:
                lines.append(
                    f"  {edge.source_memory_id} -> {edge.target_memory_id} ({edge.kind})"
                )
        else:
            lines.append("  (none)")

    lines.extend(
        [
            "",
            "TRUST",
            "  Tier      : OPEN (unverified)",
            "  Signature : NONE - treat with appropriate caution",
            "  Source    : user-provided .orb file",
            "[END OMP MEMORY PASSPORT]",
        ]
    )
    return "\n".join(lines)
