from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict, MessageToJson

from omp.proto import passport_pb2
from omp.schema.builder import memory_type_name


def to_dict(passport: passport_pb2.OrbPassport) -> dict[str, Any]:
    return MessageToDict(
        passport,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=False,
    )


def to_json(passport: passport_pb2.OrbPassport) -> str:
    return MessageToJson(
        passport,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=False,
        indent=2,
    )


def to_markdown(passport: passport_pb2.OrbPassport) -> str:
    lines = [
        f"# OMP Memory Passport",
        "",
        f"- Version: {passport.protocol_metadata.protocol_version}",
        f"- Tier: OPEN (unverified)",
        f"- Identity: {passport.identity.display_name or '(unnamed)'}",
        f"- ID: {passport.identity.identity_id}",
        "",
        "## Preferences",
    ]
    if passport.preferences:
        lines.extend(f"- `{pref.key}` = {pref.value}" for pref in passport.preferences)
    else:
        lines.append("- None")

    lines.extend(["", "## Goals"])
    if passport.goals:
        lines.extend(f"- {goal.title}: {goal.description}" for goal in passport.goals)
    else:
        lines.append("- None")

    lines.extend(["", "## Values"])
    if passport.values:
        lines.extend(f"- {value.statement}" for value in passport.values)
    else:
        lines.append("- None")

    lines.extend(["", "## Skills"])
    if passport.skills:
        lines.extend(
            f"- {skill.name}: {skill.description}" if skill.description else f"- {skill.name}"
            for skill in passport.skills
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Memories"])
    if passport.memories:
        for memory in passport.memories:
            tags = f" [{', '.join(memory.tags)}]" if memory.tags else ""
            lines.append(
                f"- **{memory_type_name(memory.memory_type).upper()}** {memory.summary}{tags}"
            )
            if memory.full_content:
                lines.append(f"  {memory.full_content}")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def export_passport(
    passport: passport_pb2.OrbPassport,
    *,
    format: str,
    path: str | Path | None = None,
) -> dict[str, Any] | str:
    normalised = format.lower()
    if normalised == "dict":
        return to_dict(passport)
    if normalised == "json":
        output = to_json(passport)
    elif normalised in {"md", "markdown"}:
        output = to_markdown(passport)
    else:
        raise ValueError(f"unsupported export format: {format}")

    if path is not None:
        Path(path).write_text(output, encoding="utf-8")
    return output


def dumps_dict(passport: passport_pb2.OrbPassport) -> str:
    return json.dumps(to_dict(passport), indent=2, sort_keys=True)
