"""Validation helpers for canonical Spine objects."""

from __future__ import annotations

from typing import Any, Mapping

from ..models import (
    ArtifactManifest,
    EnvironmentSnapshot,
    LineageEdge,
    MetricRecord,
    OperationContext,
    Project,
    ProvenanceRecord,
    RELATION_TYPES,
    Run,
    SCHEMA_VERSION,
    StageExecution,
    StructuredEventRecord,
    TraceSpanRecord,
    normalize_timestamp,
)
from .report import ValidationIssue, ValidationReport


RUN_STATUSES = frozenset({"created", "running", "completed", "failed", "cancelled"})
RECORD_TYPES = frozenset({"structured_event", "metric", "trace_span"})
EVENT_LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
EVENT_ORIGIN_MARKERS = frozenset({"explicit_capture", "imported", "derived", "compatibility_upgrade"})
METRIC_VALUE_TYPES = frozenset({"scalar", "integer", "float"})
METRIC_AGGREGATION_SCOPES = frozenset(
    {"global", "run", "stage", "operation", "step", "batch", "epoch", "dataset"}
)
TRACE_STATUSES = frozenset({"ok", "error", "cancelled", "timeout"})
TRACE_SPAN_KINDS = frozenset({"internal", "client", "server", "producer", "consumer", "model_call"})
COMPLETENESS_MARKERS = frozenset({"complete", "partial", "unknown"})
DEGRADATION_MARKERS = frozenset({"none", "partial_failure", "capture_gap", "compatibility_upgrade"})
LINEAGE_ORIGIN_MARKERS = frozenset({"explicit", "imported", "inferred", "observed"})
CONFIDENCE_MARKERS = frozenset({"unknown", "low", "medium", "high", "certain"})


def _issues() -> list[ValidationIssue]:
    return []


def _finalize(issues: list[ValidationIssue]) -> ValidationReport:
    return ValidationReport(valid=not issues, issues=tuple(issues))


def _require(condition: bool, issues: list[ValidationIssue], path: str, message: str) -> None:
    if not condition:
        issues.append(ValidationIssue(path=path, message=message))


def _require_non_blank(value: str, issues: list[ValidationIssue], path: str, message: str) -> None:
    _require(bool(value.strip()), issues, path, message)


def _require_in(
    value: str,
    allowed: frozenset[str],
    issues: list[ValidationIssue],
    path: str,
    message: str,
) -> None:
    _require(value in allowed, issues, path, message)


def _validate_string_mapping(
    values: Mapping[str, str],
    issues: list[ValidationIssue],
    path: str,
) -> None:
    for key, value in values.items():
        _require_non_blank(key, issues, path, "mapping keys must not be blank")
        _require_non_blank(value, issues, path, "mapping values must not be blank")


def _validate_mapping_keys(
    values: Mapping[str, Any],
    issues: list[ValidationIssue],
    path: str,
) -> None:
    for key in values:
        _require_non_blank(str(key), issues, path, "mapping keys must not be blank")


def _validate_schema_version(value: str, issues: list[ValidationIssue], path: str) -> None:
    _require(bool(value), issues, path, "schema_version is required")
    _require(value == SCHEMA_VERSION, issues, path, f"unsupported schema_version: {value}")


def _is_normalized_timestamp(value: str) -> bool:
    try:
        return value == normalize_timestamp(value)
    except ValueError:
        return False


def _validate_timestamp(value: str, issues: list[ValidationIssue], path: str) -> None:
    _require(bool(value.strip()), issues, path, "timestamp is required")
    if value.strip():
        _require(_is_normalized_timestamp(value), issues, path, "timestamp must be ISO-8601 UTC with trailing Z")


def validate_project(project: Project) -> ValidationReport:
    issues = _issues()
    _require(project.project_ref.kind == "project", issues, "project_ref", "kind must be 'project'")
    _require_non_blank(project.name, issues, "name", "name is required")
    _validate_timestamp(project.created_at, issues, "created_at")
    _validate_string_mapping(project.tags, issues, "tags")
    _validate_schema_version(project.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_run(run: Run) -> ValidationReport:
    issues = _issues()
    _require(run.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    _require(run.project_ref.kind == "project", issues, "project_ref", "kind must be 'project'")
    _require_in(run.status, RUN_STATUSES, issues, "status", "invalid run status")
    _validate_timestamp(run.started_at, issues, "started_at")
    if run.ended_at is not None:
        _validate_timestamp(run.ended_at, issues, "ended_at")
        _require(run.started_at <= run.ended_at, issues, "ended_at", "ended_at must be >= started_at")
    _validate_schema_version(run.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_stage_execution(stage: StageExecution) -> ValidationReport:
    issues = _issues()
    _require(
        stage.stage_execution_ref.kind == "stage",
        issues,
        "stage_execution_ref",
        "kind must be 'stage'",
    )
    _require(stage.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    _require_non_blank(stage.stage_name, issues, "stage_name", "stage_name is required")
    _require_in(stage.status, RUN_STATUSES, issues, "status", "invalid stage status")
    _validate_timestamp(stage.started_at, issues, "started_at")
    if stage.ended_at is not None:
        _validate_timestamp(stage.ended_at, issues, "ended_at")
        _require(stage.started_at <= stage.ended_at, issues, "ended_at", "ended_at must be >= started_at")
    _validate_schema_version(stage.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_operation_context(operation: OperationContext) -> ValidationReport:
    issues = _issues()
    _require(
        operation.operation_context_ref.kind == "op",
        issues,
        "operation_context_ref",
        "kind must be 'op'",
    )
    _require(operation.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    if operation.stage_execution_ref is not None:
        _require(
            operation.stage_execution_ref.kind == "stage",
            issues,
            "stage_execution_ref",
            "kind must be 'stage'",
        )
    _require_non_blank(operation.operation_name, issues, "operation_name", "operation_name is required")
    _validate_timestamp(operation.observed_at, issues, "observed_at")
    _validate_schema_version(operation.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_environment_snapshot(snapshot: EnvironmentSnapshot) -> ValidationReport:
    issues = _issues()
    _require(
        snapshot.environment_snapshot_ref.kind == "env",
        issues,
        "environment_snapshot_ref",
        "kind must be 'env'",
    )
    _require(snapshot.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    _validate_timestamp(snapshot.captured_at, issues, "captured_at")
    _require_non_blank(snapshot.python_version, issues, "python_version", "python_version is required")
    _require_non_blank(snapshot.platform, issues, "platform", "platform is required")
    _validate_string_mapping(snapshot.packages, issues, "packages")
    _validate_string_mapping(snapshot.environment_variables, issues, "environment_variables")
    _validate_schema_version(snapshot.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_artifact_manifest(manifest: ArtifactManifest) -> ValidationReport:
    issues = _issues()
    _require(manifest.artifact_ref.kind == "artifact", issues, "artifact_ref", "kind must be 'artifact'")
    _require_non_blank(manifest.artifact_kind, issues, "artifact_kind", "artifact_kind is required")
    _validate_timestamp(manifest.created_at, issues, "created_at")
    _require_non_blank(manifest.producer_ref, issues, "producer_ref", "producer_ref is required")
    _require(manifest.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    if manifest.stage_execution_ref is not None:
        _require(
            manifest.stage_execution_ref.kind == "stage",
            issues,
            "stage_execution_ref",
            "kind must be 'stage'",
        )
    _require_non_blank(manifest.location_ref, issues, "location_ref", "location_ref is required")
    if manifest.hash_value is not None:
        _require_non_blank(manifest.hash_value, issues, "hash_value", "hash_value must not be blank")
    if manifest.size_bytes is not None:
        _require(manifest.size_bytes >= 0, issues, "size_bytes", "size_bytes must be non-negative")
    _validate_mapping_keys(manifest.attributes, issues, "attributes")
    _validate_schema_version(manifest.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_lineage_edge(edge: LineageEdge) -> ValidationReport:
    issues = _issues()
    _require(edge.relation_ref.kind == "relation", issues, "relation_ref", "kind must be 'relation'")
    _require(edge.relation_type in RELATION_TYPES, issues, "relation_type", "unsupported relation_type")
    _validate_timestamp(edge.recorded_at, issues, "recorded_at")
    _require_in(edge.origin_marker, LINEAGE_ORIGIN_MARKERS, issues, "origin_marker", "invalid origin_marker")
    _require_in(
        edge.confidence_marker,
        CONFIDENCE_MARKERS,
        issues,
        "confidence_marker",
        "invalid confidence_marker",
    )
    _require(bool(str(edge.source_ref)), issues, "source_ref", "source_ref is required")
    _require(bool(str(edge.target_ref)), issues, "target_ref", "target_ref is required")
    _validate_schema_version(edge.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_provenance_record(record: ProvenanceRecord) -> ValidationReport:
    issues = _issues()
    _require(
        record.provenance_ref.kind == "provenance",
        issues,
        "provenance_ref",
        "kind must be 'provenance'",
    )
    _require(record.relation_ref.kind == "relation", issues, "relation_ref", "kind must be 'relation'")
    _require(
        record.assertion_mode in {"explicit", "imported", "inferred"},
        issues,
        "assertion_mode",
        "invalid assertion_mode",
    )
    if record.policy_ref is not None:
        _require_non_blank(record.policy_ref, issues, "policy_ref", "policy_ref must not be blank")
    if record.evidence_bundle_ref is not None:
        _require_non_blank(
            record.evidence_bundle_ref,
            issues,
            "evidence_bundle_ref",
            "evidence_bundle_ref must not be blank",
        )
    _validate_timestamp(record.asserted_at, issues, "asserted_at")
    _validate_schema_version(record.schema_version, issues, "schema_version")
    return _finalize(issues)


def _validate_record_envelope(envelope: Any, issues: list[ValidationIssue]) -> None:
    _require(envelope.record_ref.kind == "record", issues, "envelope.record_ref", "kind must be 'record'")
    _require_in(envelope.record_type, RECORD_TYPES, issues, "envelope.record_type", "invalid record_type")
    _require(envelope.run_ref.kind == "run", issues, "envelope.run_ref", "kind must be 'run'")
    _validate_timestamp(envelope.recorded_at, issues, "envelope.recorded_at")
    _validate_timestamp(envelope.observed_at, issues, "envelope.observed_at")
    _require_non_blank(envelope.producer_ref, issues, "envelope.producer_ref", "producer_ref is required")
    _require(envelope.recorded_at >= envelope.observed_at, issues, "envelope.recorded_at", "recorded_at must be >= observed_at")
    if envelope.stage_execution_ref is not None:
        _require(
            envelope.stage_execution_ref.kind == "stage",
            issues,
            "envelope.stage_execution_ref",
            "kind must be 'stage'",
        )
    if envelope.operation_context_ref is not None:
        _require(
            envelope.operation_context_ref.kind == "op",
            issues,
            "envelope.operation_context_ref",
            "kind must be 'op'",
        )
    if envelope.correlation_refs.trace_id is not None:
        _require_non_blank(
            envelope.correlation_refs.trace_id,
            issues,
            "envelope.correlation_refs.trace_id",
            "trace_id must not be blank",
        )
    if envelope.correlation_refs.session_id is not None:
        _require_non_blank(
            envelope.correlation_refs.session_id,
            issues,
            "envelope.correlation_refs.session_id",
            "session_id must not be blank",
        )
    _require_in(
        envelope.completeness_marker,
        COMPLETENESS_MARKERS,
        issues,
        "envelope.completeness_marker",
        "invalid completeness_marker",
    )
    _require_in(
        envelope.degradation_marker,
        DEGRADATION_MARKERS,
        issues,
        "envelope.degradation_marker",
        "invalid degradation_marker",
    )
    _validate_schema_version(envelope.schema_version, issues, "envelope.schema_version")


def validate_structured_event_record(record: StructuredEventRecord) -> ValidationReport:
    issues = _issues()
    _validate_record_envelope(record.envelope, issues)
    _require(
        record.envelope.record_type == "structured_event",
        issues,
        "envelope.record_type",
        "record_type must be 'structured_event'",
    )
    _require_non_blank(record.payload.event_key, issues, "payload.event_key", "event_key is required")
    _require_in(record.payload.level, EVENT_LEVELS, issues, "payload.level", "invalid event level")
    _require_non_blank(record.payload.message, issues, "payload.message", "message is required")
    _require_in(
        record.payload.origin_marker,
        EVENT_ORIGIN_MARKERS,
        issues,
        "payload.origin_marker",
        "invalid origin_marker",
    )
    if record.payload.subject_ref is not None:
        _require_non_blank(record.payload.subject_ref, issues, "payload.subject_ref", "subject_ref must not be blank")
    _validate_mapping_keys(record.payload.attributes, issues, "payload.attributes")
    return _finalize(issues)


def validate_metric_record(record: MetricRecord) -> ValidationReport:
    issues = _issues()
    _validate_record_envelope(record.envelope, issues)
    _require(record.envelope.record_type == "metric", issues, "envelope.record_type", "record_type must be 'metric'")
    _require_non_blank(record.payload.metric_key, issues, "payload.metric_key", "metric_key is required")
    _require_in(record.payload.value_type, METRIC_VALUE_TYPES, issues, "payload.value_type", "invalid value_type")
    _require_in(
        record.payload.aggregation_scope,
        METRIC_AGGREGATION_SCOPES,
        issues,
        "payload.aggregation_scope",
        "invalid aggregation_scope",
    )
    _require(not isinstance(record.payload.value, bool), issues, "payload.value", "value must not be a bool")
    if record.payload.value_type == "integer":
        _require(isinstance(record.payload.value, int), issues, "payload.value", "value must be an integer")
    elif record.payload.value_type == "float":
        _require(isinstance(record.payload.value, float), issues, "payload.value", "value must be a float")
    else:
        _require(
            isinstance(record.payload.value, (int, float)) and not isinstance(record.payload.value, bool),
            issues,
            "payload.value",
            "value must be numeric",
        )
    if record.payload.unit is not None:
        _require_non_blank(record.payload.unit, issues, "payload.unit", "unit must not be blank")
    if record.payload.subject_ref is not None:
        _require_non_blank(record.payload.subject_ref, issues, "payload.subject_ref", "subject_ref must not be blank")
    if record.payload.slice_ref is not None:
        _require_non_blank(record.payload.slice_ref, issues, "payload.slice_ref", "slice_ref must not be blank")
    if record.payload.summary_basis is not None:
        _require_non_blank(
            record.payload.summary_basis,
            issues,
            "payload.summary_basis",
            "summary_basis must not be blank",
        )
    _validate_string_mapping(record.payload.tags, issues, "payload.tags")
    return _finalize(issues)


def validate_trace_span_record(record: TraceSpanRecord) -> ValidationReport:
    issues = _issues()
    _validate_record_envelope(record.envelope, issues)
    _require(
        record.envelope.record_type == "trace_span",
        issues,
        "envelope.record_type",
        "record_type must be 'trace_span'",
    )
    _require_non_blank(record.payload.span_id, issues, "payload.span_id", "span_id is required")
    _require_non_blank(record.payload.trace_id, issues, "payload.trace_id", "trace_id is required")
    _require_non_blank(record.payload.span_name, issues, "payload.span_name", "span_name is required")
    _require_in(record.payload.status, TRACE_STATUSES, issues, "payload.status", "invalid status")
    _require_in(record.payload.span_kind, TRACE_SPAN_KINDS, issues, "payload.span_kind", "invalid span_kind")
    _validate_timestamp(record.payload.started_at, issues, "payload.started_at")
    _validate_timestamp(record.payload.ended_at, issues, "payload.ended_at")
    _require(
        record.payload.started_at <= record.payload.ended_at,
        issues,
        "payload.ended_at",
        "ended_at must be >= started_at",
    )
    _validate_mapping_keys(record.payload.attributes, issues, "payload.attributes")
    for ref in record.payload.linked_refs:
        _require_non_blank(ref, issues, "payload.linked_refs", "linked_refs must not contain blanks")
    return _finalize(issues)
