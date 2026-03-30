"""Deterministic canonical serialization helpers."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
import json
from typing import Any

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


def _convert(value: Any) -> Any:
    if isinstance(value, StableRef):
        return str(value)
    if is_dataclass(value):
        return {field.name: _convert(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, tuple):
        return [_convert(item) for item in value]
    if isinstance(value, list):
        return [_convert(item) for item in value]
    if isinstance(value, dict):
        return {key: _convert(value[key]) for key in sorted(value)}
    return value


def to_payload(obj: CanonicalObject) -> dict[str, Any]:
    """Serialize a canonical object to a deterministic JSON-compatible payload."""
    try:
        return _convert(obj)
    except Exception as exc:  # pragma: no cover
        raise SerializationError(f"Failed to serialize {type(obj).__name__}") from exc


def to_json(obj: CanonicalObject) -> str:
    """Serialize a canonical object to a deterministic JSON string."""
    try:
        return json.dumps(to_payload(obj), sort_keys=True, separators=(",", ":"))
    except Exception as exc:  # pragma: no cover
        raise SerializationError(f"Failed to encode JSON for {type(obj).__name__}") from exc


def _parse_ref(raw: str | None, field_name: str) -> StableRef:
    if raw is None:
        raise SerializationError(f"Missing required reference field: {field_name}")
    try:
        return StableRef.parse(raw)
    except ValueError as exc:
        raise SerializationError(f"Invalid StableRef for {field_name}: {raw!r}") from exc


def _validate_deserialized(value: CanonicalObject, validator: Any) -> CanonicalObject:
    try:
        validator(value).raise_for_errors()
    except ValidationError as exc:
        raise SerializationError(f"Failed to deserialize {type(value).__name__}: {exc}") from exc
    return value


def deserialize_project(payload: dict[str, Any]) -> Project:
    project = Project(
        project_ref=_parse_ref(payload.get("project_ref"), "project_ref"),
        name=str(payload["name"]),
        created_at=str(payload["created_at"]),
        description=payload.get("description"),
        tags={str(k): str(v) for k, v in dict(payload.get("tags", {})).items()},
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(project, validate_project)


def deserialize_run(payload: dict[str, Any]) -> Run:
    run = Run(
        run_ref=_parse_ref(payload.get("run_ref"), "run_ref"),
        project_ref=_parse_ref(payload.get("project_ref"), "project_ref"),
        name=str(payload["name"]),
        status=str(payload["status"]),
        started_at=str(payload["started_at"]),
        ended_at=str(payload["ended_at"]) if payload.get("ended_at") is not None else None,
        description=payload.get("description"),
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(run, validate_run)


def deserialize_stage_execution(payload: dict[str, Any]) -> StageExecution:
    stage = StageExecution(
        stage_execution_ref=_parse_ref(payload.get("stage_execution_ref"), "stage_execution_ref"),
        run_ref=_parse_ref(payload.get("run_ref"), "run_ref"),
        stage_name=str(payload["stage_name"]),
        status=str(payload["status"]),
        started_at=str(payload["started_at"]),
        ended_at=str(payload["ended_at"]) if payload.get("ended_at") is not None else None,
        order_index=int(payload["order_index"]) if payload.get("order_index") is not None else None,
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(stage, validate_stage_execution)


def deserialize_operation_context(payload: dict[str, Any]) -> OperationContext:
    operation = OperationContext(
        operation_context_ref=_parse_ref(payload.get("operation_context_ref"), "operation_context_ref"),
        run_ref=_parse_ref(payload.get("run_ref"), "run_ref"),
        stage_execution_ref=_parse_ref(payload["stage_execution_ref"], "stage_execution_ref")
        if payload.get("stage_execution_ref")
        else None,
        operation_name=str(payload["operation_name"]),
        observed_at=str(payload["observed_at"]),
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(operation, validate_operation_context)


def deserialize_environment_snapshot(payload: dict[str, Any]) -> EnvironmentSnapshot:
    snapshot = EnvironmentSnapshot(
        environment_snapshot_ref=_parse_ref(
            payload.get("environment_snapshot_ref"), "environment_snapshot_ref"
        ),
        run_ref=_parse_ref(payload.get("run_ref"), "run_ref"),
        captured_at=str(payload["captured_at"]),
        python_version=str(payload["python_version"]),
        platform=str(payload["platform"]),
        packages={str(k): str(v) for k, v in dict(payload.get("packages", {})).items()},
        environment_variables={
            str(k): str(v) for k, v in dict(payload.get("environment_variables", {})).items()
        },
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(snapshot, validate_environment_snapshot)


def deserialize_artifact_manifest(payload: dict[str, Any]) -> ArtifactManifest:
    manifest = ArtifactManifest(
        artifact_ref=_parse_ref(payload.get("artifact_ref"), "artifact_ref"),
        artifact_kind=str(payload["artifact_kind"]),
        created_at=str(payload["created_at"]),
        producer_ref=str(payload["producer_ref"]),
        run_ref=_parse_ref(payload.get("run_ref"), "run_ref"),
        stage_execution_ref=_parse_ref(payload["stage_execution_ref"], "stage_execution_ref")
        if payload.get("stage_execution_ref")
        else None,
        location_ref=str(payload["location_ref"]),
        hash_value=str(payload["hash_value"]) if payload.get("hash_value") is not None else None,
        size_bytes=int(payload["size_bytes"]) if payload.get("size_bytes") is not None else None,
        attributes=dict(payload.get("attributes", {})),
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(manifest, validate_artifact_manifest)


def deserialize_lineage_edge(payload: dict[str, Any]) -> LineageEdge:
    edge = LineageEdge(
        relation_ref=_parse_ref(payload.get("relation_ref"), "relation_ref"),
        relation_type=str(payload["relation_type"]),
        source_ref=_parse_ref(payload.get("source_ref"), "source_ref"),
        target_ref=_parse_ref(payload.get("target_ref"), "target_ref"),
        recorded_at=str(payload["recorded_at"]),
        origin_marker=str(payload["origin_marker"]),
        confidence_marker=str(payload["confidence_marker"]),
        operation_context_ref=_parse_ref(payload["operation_context_ref"], "operation_context_ref")
        if payload.get("operation_context_ref")
        else None,
        evidence_refs=tuple(str(item) for item in payload.get("evidence_refs", ())),
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(edge, validate_lineage_edge)


def deserialize_provenance_record(payload: dict[str, Any]) -> ProvenanceRecord:
    record = ProvenanceRecord(
        provenance_ref=_parse_ref(payload.get("provenance_ref"), "provenance_ref"),
        relation_ref=_parse_ref(payload.get("relation_ref"), "relation_ref"),
        formation_context_ref=_parse_ref(payload["formation_context_ref"], "formation_context_ref")
        if payload.get("formation_context_ref")
        else None,
        policy_ref=str(payload["policy_ref"]) if payload.get("policy_ref") is not None else None,
        evidence_bundle_ref=str(payload["evidence_bundle_ref"])
        if payload.get("evidence_bundle_ref") is not None
        else None,
        assertion_mode=str(payload["assertion_mode"]),
        asserted_at=str(payload["asserted_at"]),
        schema_version=str(payload.get("schema_version", "")),
    )
    return _validate_deserialized(record, validate_provenance_record)


def _deserialize_envelope(payload: dict[str, Any]) -> RecordEnvelope:
    correlation_payload = dict(payload.get("correlation_refs", {}))
    return RecordEnvelope(
        record_ref=_parse_ref(payload.get("record_ref"), "record_ref"),
        record_type=str(payload["record_type"]),
        recorded_at=str(payload["recorded_at"]),
        observed_at=str(payload["observed_at"]),
        producer_ref=str(payload["producer_ref"]),
        run_ref=_parse_ref(payload.get("run_ref"), "run_ref"),
        stage_execution_ref=_parse_ref(payload["stage_execution_ref"], "stage_execution_ref")
        if payload.get("stage_execution_ref")
        else None,
        operation_context_ref=_parse_ref(payload["operation_context_ref"], "operation_context_ref")
        if payload.get("operation_context_ref")
        else None,
        correlation_refs=CorrelationRefs(
            trace_id=str(correlation_payload["trace_id"])
            if correlation_payload.get("trace_id") is not None
            else None,
            session_id=str(correlation_payload["session_id"])
            if correlation_payload.get("session_id") is not None
            else None,
        ),
        completeness_marker=str(payload.get("completeness_marker", "complete")),
        degradation_marker=str(payload.get("degradation_marker", "none")),
        schema_version=str(payload.get("schema_version", "")),
    )


def deserialize_structured_event_record(payload: dict[str, Any]) -> StructuredEventRecord:
    record = StructuredEventRecord(
        envelope=_deserialize_envelope(payload),
        payload=StructuredEventPayload(
            event_key=str(payload["payload"]["event_key"]),
            level=str(payload["payload"]["level"]),
            message=str(payload["payload"]["message"]),
            subject_ref=str(payload["payload"]["subject_ref"])
            if payload["payload"].get("subject_ref") is not None
            else None,
            attributes=dict(payload["payload"].get("attributes", {})),
            origin_marker=str(payload["payload"].get("origin_marker", "explicit_capture")),
        ),
    )
    return _validate_deserialized(record, validate_structured_event_record)


def deserialize_metric_record(payload: dict[str, Any]) -> MetricRecord:
    record = MetricRecord(
        envelope=_deserialize_envelope(payload),
        payload=MetricPayload(
            metric_key=str(payload["payload"]["metric_key"]),
            value=payload["payload"]["value"],
            value_type=str(payload["payload"]["value_type"]),
            unit=str(payload["payload"]["unit"]) if payload["payload"].get("unit") is not None else None,
            aggregation_scope=str(payload["payload"].get("aggregation_scope", "step")),
            subject_ref=str(payload["payload"]["subject_ref"])
            if payload["payload"].get("subject_ref") is not None
            else None,
            slice_ref=str(payload["payload"]["slice_ref"])
            if payload["payload"].get("slice_ref") is not None
            else None,
            tags={str(k): str(v) for k, v in dict(payload["payload"].get("tags", {})).items()},
            summary_basis=str(payload["payload"]["summary_basis"])
            if payload["payload"].get("summary_basis") is not None
            else None,
        ),
    )
    return _validate_deserialized(record, validate_metric_record)


def deserialize_trace_span_record(payload: dict[str, Any]) -> TraceSpanRecord:
    record = TraceSpanRecord(
        envelope=_deserialize_envelope(payload),
        payload=TraceSpanPayload(
            span_id=str(payload["payload"]["span_id"]),
            trace_id=str(payload["payload"]["trace_id"]),
            parent_span_id=str(payload["payload"]["parent_span_id"])
            if payload["payload"].get("parent_span_id") is not None
            else None,
            span_name=str(payload["payload"]["span_name"]),
            started_at=str(payload["payload"]["started_at"]),
            ended_at=str(payload["payload"]["ended_at"]),
            status=str(payload["payload"]["status"]),
            span_kind=str(payload["payload"]["span_kind"]),
            attributes=dict(payload["payload"].get("attributes", {})),
            linked_refs=tuple(str(item) for item in payload["payload"].get("linked_refs", ())),
        ),
    )
    return _validate_deserialized(record, validate_trace_span_record)
