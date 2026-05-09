from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from uuid import uuid4

from google.protobuf.message import Message

from omp.exceptions import InvalidOrbFile
from omp.proto import adapter_pb2, identity_pb2, memory_pb2, passport_pb2
from omp.schema.version import PACKAGE_VERSION, PROTOCOL_VERSION

_MEMORY_TYPE_BY_NAME = {
    "fact": memory_pb2.MEMORY_TYPE_FACT,
    "goal": memory_pb2.MEMORY_TYPE_GOAL,
    "preference": memory_pb2.MEMORY_TYPE_PREFERENCE,
    "value": memory_pb2.MEMORY_TYPE_VALUE,
    "skill": memory_pb2.MEMORY_TYPE_SKILL,
    "interest": memory_pb2.MEMORY_TYPE_INTEREST,
    "relationship": memory_pb2.MEMORY_TYPE_RELATIONSHIP,
    "event": memory_pb2.MEMORY_TYPE_EVENT,
    "project": memory_pb2.MEMORY_TYPE_PROJECT,
    "note": memory_pb2.MEMORY_TYPE_NOTE,
    "conversation": memory_pb2.MEMORY_TYPE_CONVERSATION,
    "episodic": memory_pb2.MEMORY_TYPE_EPISODIC,
}


def build_passport(
    *,
    identity: Mapping[str, object] | None = None,
    profile: Mapping[str, object] | None = None,
    preferences: Mapping[str, object] | Sequence[Mapping[str, object]] | None = None,
    goals: Sequence[Mapping[str, object]] | None = None,
    values: Sequence[Mapping[str, object]] | None = None,
    skills: Sequence[Mapping[str, object]] | None = None,
    interests: Sequence[Mapping[str, object]] | None = None,
    relationships: Sequence[Mapping[str, object]] | None = None,
    memories: Sequence[Mapping[str, object]] | None = None,
    adapters: Sequence[Mapping[str, object]] | None = None,
    provenance: Sequence[Mapping[str, object]] | None = None,
    export_policy: Mapping[str, object] | None = None,
    version: tuple[int, int, int] | None = None,
) -> passport_pb2.OrbPassport:
    identity_data = dict(identity or {})
    protocol_version = ".".join(str(part) for part in version) if version else PROTOCOL_VERSION
    now = _now()

    passport_id = str(identity_data.get("passport_id") or _canonical_id("passport"))
    namespace_id = str(identity_data.get("namespace_id") or _canonical_id("namespace"))
    identity_id = str(identity_data.get("identity_id") or _canonical_id("identity"))

    passport = passport_pb2.OrbPassport()
    _fill_protocol_metadata(
        passport.protocol_metadata,
        protocol_version=protocol_version,
        namespace_id=namespace_id,
        now=now,
        compression_algorithm=str(identity_data.get("compression_algorithm") or "none"),
    )

    passport.identity.passport_id = passport_id
    passport.identity.identity_id = identity_id
    passport.identity.display_name = str(identity_data.get("display_name") or "")
    passport.identity.username = str(identity_data.get("username") or "")
    passport.identity.aliases.extend(str(alias) for alias in identity_data.get("aliases", []) or [])
    passport.identity.locale = str(identity_data.get("locale") or "")
    passport.identity.timezone = str(identity_data.get("timezone") or "")
    passport.identity.country = str(identity_data.get("country") or "")
    passport.identity.primary_language = str(identity_data.get("primary_language") or "")
    passport.identity.namespace_id = namespace_id
    _fill_provenance(passport.identity.provenance, identity_data, now, default_label="identity")

    _fill_profile(passport.profile, profile or identity_data.get("profile") or {})

    for pref in _normalise_preferences(preferences, identity_data):
        passport.preferences.append(_preference_from_mapping(pref, now))

    for goal in _normalise_sequence(goals or identity_data.get("goals")):
        passport.goals.append(_goal_from_mapping(goal, now))

    for value in _normalise_sequence(values or identity_data.get("values")):
        passport.values.append(_value_from_mapping(value, now))

    for skill in _normalise_sequence(skills or identity_data.get("skills")):
        passport.skills.append(_skill_from_mapping(skill, now))

    for interest in _normalise_sequence(interests or identity_data.get("interests")):
        passport.interests.append(_interest_from_mapping(interest, now))

    for relationship in _normalise_sequence(
        relationships or identity_data.get("relationships")
    ):
        passport.relationships.append(_relationship_from_mapping(relationship, now))

    for item in memories or []:
        passport.memories.append(_memory_from_mapping(item, now, namespace_id))

    for adapter in _normalise_sequence(adapters):
        passport.adapters.append(_adapter_from_mapping(adapter))

    provenance_items = _normalise_sequence(provenance)
    if provenance_items:
        for item in provenance_items:
            prov = passport.provenance.add()
            _fill_provenance(prov, item, now)
    else:
        prov = passport.provenance.add()
        _fill_provenance(prov, {"source": "omp-python"}, now, default_label="creator")

    _fill_export_policy(passport.export_policy, export_policy or {})
    passport.integrity.verification_mode = "OPEN"
    passport.integrity.checksum_algorithm = "SHA-256"
    passport.integrity.checksum_scope = "bytes before footer"
    passport.integrity.signature_algorithm = "none"
    passport.verified = False
    passport.tier = "open"
    return passport


def memory_type_from_name(memory_type: str | int) -> int:
    if isinstance(memory_type, int):
        return memory_type
    normalised = memory_type.lower()
    normalised = normalised.removeprefix("memory_type_").removeprefix("memory_kind_")
    if normalised not in _MEMORY_TYPE_BY_NAME:
        raise InvalidOrbFile(f"unknown memory type: {memory_type}")
    return _MEMORY_TYPE_BY_NAME[normalised]


def memory_type_name(memory_type: int) -> str:
    for name, value in _MEMORY_TYPE_BY_NAME.items():
        if value == memory_type:
            return name
    return "unspecified"


memory_kind_from_name = memory_type_from_name
memory_kind_name = memory_type_name


def _fill_protocol_metadata(
    metadata: passport_pb2.PassportMetadata,
    *,
    protocol_version: str,
    namespace_id: str,
    now: str,
    compression_algorithm: str,
) -> None:
    metadata.protocol_name = "OMP"
    metadata.protocol_version = protocol_version
    metadata.schema_version = "orbynt.memory.protocol.v1"
    metadata.file_format_version = "ORB1"
    metadata.created_at = now
    metadata.updated_at = now
    metadata.export_mode = "OPEN"
    metadata.checksum_algorithm = "SHA-256"
    metadata.compression_algorithm = compression_algorithm
    metadata.creator_library_version = PACKAGE_VERSION
    metadata.namespace_id = namespace_id
    namespace = metadata.namespaces.add()
    namespace.namespace_id = namespace_id
    namespace.name = "default"


def _fill_profile(profile: passport_pb2.Profile, data: object) -> None:
    if not isinstance(data, Mapping):
        return
    profile.biography = str(data.get("biography") or "")
    profile.occupation = str(data.get("occupation") or "")
    profile.education = str(data.get("education") or "")
    profile.organization = str(data.get("organization") or "")
    profile.website_links.extend(str(link) for link in data.get("website_links", []) or [])


def _normalise_preferences(
    preferences: Mapping[str, object] | Sequence[Mapping[str, object]] | None,
    identity_data: Mapping[str, object],
) -> list[Mapping[str, object]]:
    source = preferences if preferences is not None else identity_data.get("preferences")
    if source is None:
        return []
    if isinstance(source, Mapping):
        return [{"key": str(key), "value": value} for key, value in source.items()]
    return _normalise_sequence(source)


def _normalise_sequence(value: object) -> list[Mapping[str, object]]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, str):
        raise InvalidOrbFile("expected a sequence of mappings, got a string")
    return [dict(item) for item in value]  # type: ignore[arg-type]


def _preference_from_mapping(
    value: Mapping[str, object],
    now: str,
) -> identity_pb2.Preference:
    pref = identity_pb2.Preference()
    pref.key = str(value.get("key") or "")
    pref.value = str(value.get("value") or "")
    pref.confidence = float(value.get("confidence", 1.0))
    pref.category = str(value.get("category") or "")
    _fill_provenance(pref.provenance, value, now)
    return pref


def _goal_from_mapping(value: Mapping[str, object], now: str) -> passport_pb2.Goal:
    goal = passport_pb2.Goal()
    goal.title = str(value.get("title") or value.get("summary") or "")
    goal.description = str(value.get("description") or value.get("content") or "")
    goal.priority = str(value.get("priority") or "")
    goal.status = str(value.get("status") or "")
    goal.deadline = str(value.get("deadline") or "")
    _fill_provenance(goal.provenance, value, now)
    return goal


def _value_from_mapping(value: Mapping[str, object], now: str) -> passport_pb2.Value:
    item = passport_pb2.Value()
    item.statement = str(value.get("statement") or value.get("summary") or "")
    item.priority = str(value.get("priority") or "")
    item.category = str(value.get("category") or "")
    _fill_provenance(item.provenance, value, now)
    return item


def _skill_from_mapping(value: Mapping[str, object], now: str) -> identity_pb2.Skill:
    skill = identity_pb2.Skill()
    skill.name = str(value.get("name") or "")
    skill.description = str(value.get("description") or "")
    skill.level = str(value.get("level") or "")
    skill.years_experience = float(value.get("years_experience", 0.0))
    skill.evidence.extend(str(item) for item in value.get("evidence", []) or [])
    skill.confidence = float(value.get("confidence", 1.0))
    _fill_provenance(skill.provenance, value, now)
    return skill


def _interest_from_mapping(value: Mapping[str, object], now: str) -> identity_pb2.Interest:
    interest = identity_pb2.Interest()
    interest.name = str(value.get("name") or value.get("topic") or "")
    interest.description = str(value.get("description") or "")
    interest.confidence = float(value.get("confidence", 1.0))
    _fill_provenance(interest.provenance, value, now)
    return interest


def _relationship_from_mapping(
    value: Mapping[str, object],
    now: str,
) -> passport_pb2.Relationship:
    relationship = passport_pb2.Relationship()
    relationship.person_name = str(value.get("person_name") or value.get("name") or "")
    relationship.relationship_type = str(value.get("relationship_type") or value.get("type") or "")
    relationship.notes = str(value.get("notes") or "")
    _fill_provenance(relationship.provenance, value, now)
    return relationship


def _memory_from_mapping(
    value: Mapping[str, object],
    now: str,
    default_namespace_id: str,
) -> memory_pb2.MemoryRecord:
    record = memory_pb2.MemoryRecord()
    record.memory_id = str(value.get("memory_id") or _canonical_id("memory"))
    record.memory_type = memory_type_from_name(
        value.get("memory_type", value.get("kind", "fact"))  # type: ignore[arg-type]
    )
    record.summary = str(value.get("summary") or "")
    record.full_content = str(value.get("full_content") or value.get("content") or "")
    record.namespace_id = str(value.get("namespace_id") or default_namespace_id)
    record.tags.extend(str(tag) for tag in value.get("tags", []) or [])
    record.confidence = float(value.get("confidence", 1.0))
    record.importance = float(value.get("importance", 0.0))
    record.created_at = str(value.get("created_at") or now)
    record.updated_at = str(value.get("updated_at") or record.created_at)
    _fill_provenance(record.provenance, value, now)
    record.related_memory_ids.extend(
        str(memory_id) for memory_id in value.get("related_memory_ids", []) or []
    )
    record.graph_node_refs.extend(
        str(node_ref) for node_ref in value.get("graph_node_refs", []) or []
    )
    for key, raw in dict(value.get("custom_attributes", {}) or {}).items():
        record.custom_attributes[str(key)] = str(raw)
    if keywords := value.get("keywords"):
        record.retrieval.keywords.extend(str(keyword) for keyword in keywords)
    return record


def _adapter_from_mapping(value: Mapping[str, object]) -> adapter_pb2.AdapterMetadata:
    adapter = adapter_pb2.AdapterMetadata()
    adapter.adapter_id = str(value.get("adapter_id") or _canonical_id("adapter"))
    adapter.target_ai = str(value.get("target_ai") or value.get("target_system") or "")
    return adapter


def _fill_export_policy(
    policy,
    value: Mapping[str, object],
) -> None:
    policy.allow_export = bool(value.get("allow_export", True))
    policy.allowed_targets.extend(str(item) for item in value.get("allowed_targets", []) or [])
    policy.redacted_tags.extend(str(item) for item in value.get("redacted_tags", []) or [])
    policy.include_embeddings = bool(value.get("include_embeddings", False))
    policy.include_graph = bool(value.get("include_graph", True))
    policy.include_preferences = bool(value.get("include_preferences", True))
    policy.include_private_memories = bool(value.get("include_private_memories", False))


def _fill_provenance(
    provenance,
    value: Mapping[str, object],
    now: str,
    *,
    default_label: str = "",
) -> None:
    provenance.source = str(value.get("source") or "user")
    provenance.created_at = str(value.get("created_at") or now)
    provenance.updated_at = str(value.get("updated_at") or now)
    provenance.source_id = str(value.get("source_id") or "")
    provenance.source_type = str(value.get("source_type") or "manual")
    provenance.source_label = str(value.get("source_label") or default_label)
    provenance.acquisition_time = str(value.get("acquisition_time") or now)
    for key, raw in dict(value.get("attributes", {}) or {}).items():
        provenance.attributes[str(key)] = str(raw)


def _canonical_id(kind: str) -> str:
    return f"omp://{kind}/{uuid4()}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
