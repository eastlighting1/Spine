"""Deterministic canonical serialization helpers."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
import json
from typing import Any, Callable, Mapping, TypeVar, cast

from ..exceptions import SerializationError, ValidationError
from ..models import (
    ArtifactManifest,
    CorrelationRefs,
    EnvironmentSnapshot,
    LineageEdge,
    MetricPayload,
    MetricRecord,
    OperationContext,
    Project,
    ProvenanceRecord,
    RecordEnvelope,
    Run,
    StableRef,
    StageExecution,
    StructuredEventPayload,
    StructuredEventRecord,
    TraceSpanPayload,
    TraceSpanRecord,
)
from ..validation import (
    validate_artifact_manifest,
    validate_environment_snapshot,
    validate_lineage_edge,
    validate_metric_record,
    validate_operation_context,
    validate_project,
    validate_provenance_record,
    validate_run,
    validate_stage_execution,
    validate_structured_event_record,
    validate_trace_span_record,
)


CanonicalObject = (
    Project
    | Run
    | StageExecution
    | OperationContext
    | EnvironmentSnapshot
    | ArtifactManifest
    | LineageEdge
    | ProvenanceRecord
    | StructuredEventRecord
    | MetricRecord
    | TraceSpanRecord
)

T = TypeVar("T")


def _convert(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, StableRef):
        return str(value)
    if is_dataclass(value):
        return {field.name: _convert(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_convert(item) for item in value]
    if isinstance(value, list):
        return [_convert(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _convert(value[key]) for key in sorted(value)}
    raise SerializationError(
        f"Unsupported value type for canonical serialization: {type(value).__name__}"
    )


def to_payload(obj: CanonicalObject) -> dict[str, Any]:
    """Serialize a canonical object to a deterministic JSON-compatible payload."""
    try:
        payload = _convert(obj)
        if not isinstance(payload, dict):
            raise SerializationError(f"Serialized payload for {type(obj).__name__} is not a mapping")
        return cast(dict[str, Any], payload)
    except SerializationError:
        raise
    except Exception as exc:  # pragma: no cover
        raise SerializationError(f"Failed to serialize {type(obj).__name__}") from exc


def to_json(obj: CanonicalObject) -> str:
    """Serialize a canonical object to a deterministic JSON string."""
    try:
        return json.dumps(to_payload(obj), sort_keys=True, separators=(",", ":"))
    except SerializationError:
        raise
    except Exception as exc:  # pragma: no cover
        raise SerializationError(f"Failed to encode JSON for {type(obj).__name__}") from exc


def _parse_ref(raw: str | None, field_name: str) -> StableRef:
    if raw is None:
        raise SerializationError(f"Missing required reference field: {field_name}")
    try:
        return StableRef.parse(raw)
    except ValueError as exc:
        raise SerializationError(f"Invalid StableRef for {field_name}: {raw!r}") from exc


def _require_mapping(raw: Any, context: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise SerializationError(f"{context} payload must be a mapping")
    return {str(key): value for key, value in raw.items()}


def _read_required(payload: Mapping[str, Any], field_name: str) -> Any:
    if field_name not in payload:
        raise SerializationError(f"Missing required field: {field_name}")
    return payload[field_name]


def _read_string(payload: Mapping[str, Any], field_name: str, *, required: bool = True) -> str | None:
    if not required and field_name not in payload:
        return None
    value = _read_required(payload, field_name) if required else payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SerializationError(f"Field {field_name} must be a string")
    return value


def _read_int(payload: Mapping[str, Any], field_name: str, *, required: bool = True) -> int | None:
    if not required and field_name not in payload:
        return None
    value = _read_required(payload, field_name) if required else payload.get(field_name)
    if value is None:
        return None
    if isinstance(value, bool):
        raise SerializationError(f"Field {field_name} must be an integer")
    if not isinstance(value, int):
        raise SerializationError(f"Field {field_name} must be an integer")
    return value


def _read_string_mapping(payload: Mapping[str, Any], field_name: str) -> dict[str, str]:
    raw = payload.get(field_name, {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise SerializationError(f"Field {field_name} must be a mapping")
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise SerializationError(f"Field {field_name} must be a mapping of string keys to string values")
        result[key] = value
    return result


def _read_mapping(payload: Mapping[str, Any], field_name: str) -> dict[str, Any]:
    raw = payload.get(field_name, {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise SerializationError(f"Field {field_name} must be a mapping")
    return {str(key): value for key, value in raw.items()}


def _read_string_tuple(payload: Mapping[str, Any], field_name: str) -> tuple[str, ...]:
    raw = payload.get(field_name, ())
    if raw is None:
        return ()
    if not isinstance(raw, (list, tuple)):
        raise SerializationError(f"Field {field_name} must be a list of strings")
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise SerializationError(f"Field {field_name} must be a list of strings")
        result.append(item)
    return tuple(result)


def _read_ref(payload: Mapping[str, Any], field_name: str, *, required: bool = True) -> StableRef | None:
    raw = _read_string(payload, field_name, required=required)
    if raw is None:
        return None
    return _parse_ref(raw, field_name)


def _validate_deserialized(value: T, validator: Callable[[T], Any]) -> T:
    try:
        validator(value).raise_for_errors()
    except ValidationError as exc:
        raise SerializationError(f"Failed to deserialize {type(value).__name__}: {exc}") from exc
    return value


def deserialize_project(payload: dict[str, Any]) -> Project:
    payload = _require_mapping(payload, "Project")
    project = Project(
        project_ref=cast(StableRef, _read_ref(payload, "project_ref")),
        name=cast(str, _read_string(payload, "name")),
        created_at=cast(str, _read_string(payload, "created_at")),
        description=_read_string(payload, "description", required=False),
        tags=_read_string_mapping(payload, "tags"),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(project, validate_project)


def deserialize_run(payload: dict[str, Any]) -> Run:
    payload = _require_mapping(payload, "Run")
    run = Run(
        run_ref=cast(StableRef, _read_ref(payload, "run_ref")),
        project_ref=cast(StableRef, _read_ref(payload, "project_ref")),
        name=cast(str, _read_string(payload, "name")),
        status=cast(str, _read_string(payload, "status")),
        started_at=cast(str, _read_string(payload, "started_at")),
        ended_at=_read_string(payload, "ended_at", required=False),
        description=_read_string(payload, "description", required=False),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(run, validate_run)


def deserialize_stage_execution(payload: dict[str, Any]) -> StageExecution:
    payload = _require_mapping(payload, "StageExecution")
    stage = StageExecution(
        stage_execution_ref=cast(StableRef, _read_ref(payload, "stage_execution_ref")),
        run_ref=cast(StableRef, _read_ref(payload, "run_ref")),
        stage_name=cast(str, _read_string(payload, "stage_name")),
        status=cast(str, _read_string(payload, "status")),
        started_at=cast(str, _read_string(payload, "started_at")),
        ended_at=_read_string(payload, "ended_at", required=False),
        order_index=_read_int(payload, "order_index", required=False),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(stage, validate_stage_execution)


def deserialize_operation_context(payload: dict[str, Any]) -> OperationContext:
    payload = _require_mapping(payload, "OperationContext")
    operation = OperationContext(
        operation_context_ref=cast(StableRef, _read_ref(payload, "operation_context_ref")),
        run_ref=cast(StableRef, _read_ref(payload, "run_ref")),
        stage_execution_ref=_read_ref(payload, "stage_execution_ref", required=False),
        operation_name=cast(str, _read_string(payload, "operation_name")),
        observed_at=cast(str, _read_string(payload, "observed_at")),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(operation, validate_operation_context)


def deserialize_environment_snapshot(payload: dict[str, Any]) -> EnvironmentSnapshot:
    payload = _require_mapping(payload, "EnvironmentSnapshot")
    snapshot = EnvironmentSnapshot(
        environment_snapshot_ref=cast(StableRef, _read_ref(payload, "environment_snapshot_ref")),
        run_ref=cast(StableRef, _read_ref(payload, "run_ref")),
        captured_at=cast(str, _read_string(payload, "captured_at")),
        python_version=cast(str, _read_string(payload, "python_version")),
        platform=cast(str, _read_string(payload, "platform")),
        packages=_read_string_mapping(payload, "packages"),
        environment_variables=_read_string_mapping(payload, "environment_variables"),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(snapshot, validate_environment_snapshot)


def deserialize_artifact_manifest(payload: dict[str, Any]) -> ArtifactManifest:
    payload = _require_mapping(payload, "ArtifactManifest")
    manifest = ArtifactManifest(
        artifact_ref=cast(StableRef, _read_ref(payload, "artifact_ref")),
        artifact_kind=cast(str, _read_string(payload, "artifact_kind")),
        created_at=cast(str, _read_string(payload, "created_at")),
        producer_ref=cast(str, _read_string(payload, "producer_ref")),
        run_ref=cast(StableRef, _read_ref(payload, "run_ref")),
        stage_execution_ref=_read_ref(payload, "stage_execution_ref", required=False),
        location_ref=cast(str, _read_string(payload, "location_ref")),
        hash_value=_read_string(payload, "hash_value", required=False),
        size_bytes=_read_int(payload, "size_bytes", required=False),
        attributes=_read_mapping(payload, "attributes"),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(manifest, validate_artifact_manifest)


def deserialize_lineage_edge(payload: dict[str, Any]) -> LineageEdge:
    payload = _require_mapping(payload, "LineageEdge")
    edge = LineageEdge(
        relation_ref=cast(StableRef, _read_ref(payload, "relation_ref")),
        relation_type=cast(str, _read_string(payload, "relation_type")),
        source_ref=cast(StableRef, _read_ref(payload, "source_ref")),
        target_ref=cast(StableRef, _read_ref(payload, "target_ref")),
        recorded_at=cast(str, _read_string(payload, "recorded_at")),
        origin_marker=cast(str, _read_string(payload, "origin_marker")),
        confidence_marker=cast(str, _read_string(payload, "confidence_marker")),
        operation_context_ref=_read_ref(payload, "operation_context_ref", required=False),
        evidence_refs=_read_string_tuple(payload, "evidence_refs"),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(edge, validate_lineage_edge)


def deserialize_provenance_record(payload: dict[str, Any]) -> ProvenanceRecord:
    payload = _require_mapping(payload, "ProvenanceRecord")
    record = ProvenanceRecord(
        provenance_ref=cast(StableRef, _read_ref(payload, "provenance_ref")),
        relation_ref=cast(StableRef, _read_ref(payload, "relation_ref")),
        formation_context_ref=_read_ref(payload, "formation_context_ref", required=False),
        policy_ref=_read_string(payload, "policy_ref", required=False),
        evidence_bundle_ref=_read_string(payload, "evidence_bundle_ref", required=False),
        assertion_mode=cast(str, _read_string(payload, "assertion_mode")),
        asserted_at=cast(str, _read_string(payload, "asserted_at")),
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )
    return _validate_deserialized(record, validate_provenance_record)


def _deserialize_envelope(payload: dict[str, Any]) -> RecordEnvelope:
    payload = _require_mapping(payload, "RecordEnvelope")
    correlation_payload = _read_mapping(payload, "correlation_refs")
    return RecordEnvelope(
        record_ref=cast(StableRef, _read_ref(payload, "record_ref")),
        record_type=cast(str, _read_string(payload, "record_type")),
        recorded_at=cast(str, _read_string(payload, "recorded_at")),
        observed_at=cast(str, _read_string(payload, "observed_at")),
        producer_ref=cast(str, _read_string(payload, "producer_ref")),
        run_ref=cast(StableRef, _read_ref(payload, "run_ref")),
        stage_execution_ref=_read_ref(payload, "stage_execution_ref", required=False),
        operation_context_ref=_read_ref(payload, "operation_context_ref", required=False),
        correlation_refs=CorrelationRefs(
            trace_id=_read_string(correlation_payload, "trace_id", required=False),
            session_id=_read_string(correlation_payload, "session_id", required=False),
        ),
        completeness_marker=_read_string(payload, "completeness_marker", required=False) or "complete",
        degradation_marker=_read_string(payload, "degradation_marker", required=False) or "none",
        schema_version=cast(str, _read_string(payload, "schema_version")),
    )


def _split_record_payload(
    payload: dict[str, Any],
    envelope_context: str,
    body_context: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _require_mapping(payload, envelope_context)
    envelope_payload = payload
    if "envelope" in payload:
        envelope_payload = _require_mapping(_read_required(payload, "envelope"), "RecordEnvelope")
    payload_body = _require_mapping(_read_required(payload, "payload"), body_context)
    return envelope_payload, payload_body


def deserialize_structured_event_record(payload: dict[str, Any]) -> StructuredEventRecord:
    envelope_payload, payload_body = _split_record_payload(
        payload,
        "StructuredEventRecord",
        "StructuredEventPayload",
    )
    record = StructuredEventRecord(
        envelope=_deserialize_envelope(envelope_payload),
        payload=StructuredEventPayload(
            event_key=cast(str, _read_string(payload_body, "event_key")),
            level=cast(str, _read_string(payload_body, "level")),
            message=cast(str, _read_string(payload_body, "message")),
            subject_ref=_read_string(payload_body, "subject_ref", required=False),
            attributes=_read_mapping(payload_body, "attributes"),
            origin_marker=_read_string(payload_body, "origin_marker", required=False) or "explicit_capture",
        ),
    )
    return _validate_deserialized(record, validate_structured_event_record)


def deserialize_metric_record(payload: dict[str, Any]) -> MetricRecord:
    envelope_payload, payload_body = _split_record_payload(
        payload,
        "MetricRecord",
        "MetricPayload",
    )
    record = MetricRecord(
        envelope=_deserialize_envelope(envelope_payload),
        payload=MetricPayload(
            metric_key=cast(str, _read_string(payload_body, "metric_key")),
            value=_read_required(payload_body, "value"),
            value_type=cast(str, _read_string(payload_body, "value_type")),
            unit=_read_string(payload_body, "unit", required=False),
            aggregation_scope=_read_string(payload_body, "aggregation_scope", required=False) or "step",
            subject_ref=_read_string(payload_body, "subject_ref", required=False),
            slice_ref=_read_string(payload_body, "slice_ref", required=False),
            tags=_read_string_mapping(payload_body, "tags"),
            summary_basis=_read_string(payload_body, "summary_basis", required=False),
        ),
    )
    return _validate_deserialized(record, validate_metric_record)


def deserialize_trace_span_record(payload: dict[str, Any]) -> TraceSpanRecord:
    envelope_payload, payload_body = _split_record_payload(
        payload,
        "TraceSpanRecord",
        "TraceSpanPayload",
    )
    record = TraceSpanRecord(
        envelope=_deserialize_envelope(envelope_payload),
        payload=TraceSpanPayload(
            span_id=cast(str, _read_string(payload_body, "span_id")),
            trace_id=cast(str, _read_string(payload_body, "trace_id")),
            parent_span_id=_read_string(payload_body, "parent_span_id", required=False),
            span_name=cast(str, _read_string(payload_body, "span_name")),
            started_at=cast(str, _read_string(payload_body, "started_at")),
            ended_at=cast(str, _read_string(payload_body, "ended_at")),
            status=cast(str, _read_string(payload_body, "status")),
            span_kind=cast(str, _read_string(payload_body, "span_kind")),
            attributes=_read_mapping(payload_body, "attributes"),
            linked_refs=_read_string_tuple(payload_body, "linked_refs"),
        ),
    )
    return _validate_deserialized(record, validate_trace_span_record)
