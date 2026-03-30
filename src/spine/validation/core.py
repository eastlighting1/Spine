"""Validation helpers for canonical Spine objects."""

from __future__ import annotations

from typing import Any

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


def _issues() -> list[ValidationIssue]:
    return []


def _finalize(issues: list[ValidationIssue]) -> ValidationReport:
    return ValidationReport(valid=not issues, issues=tuple(issues))


def _require(condition: bool, issues: list[ValidationIssue], path: str, message: str) -> None:
    if not condition:
        issues.append(ValidationIssue(path=path, message=message))


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
    _require(bool(project.name.strip()), issues, "name", "name is required")
    _validate_timestamp(project.created_at, issues, "created_at")
    _validate_schema_version(project.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_run(run: Run) -> ValidationReport:
    issues = _issues()
    _require(run.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    _require(run.project_ref.kind == "project", issues, "project_ref", "kind must be 'project'")
    _require(
        run.status in {"created", "running", "completed", "failed", "cancelled"},
        issues,
        "status",
        "invalid run status",
    )
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
    _require(bool(stage.stage_name.strip()), issues, "stage_name", "stage_name is required")
    _require(
        stage.status in {"created", "running", "completed", "failed", "cancelled"},
        issues,
        "status",
        "invalid stage status",
    )
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
    _require(
        bool(operation.operation_name.strip()),
        issues,
        "operation_name",
        "operation_name is required",
    )
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
    _require(bool(snapshot.python_version.strip()), issues, "python_version", "python_version is required")
    _require(bool(snapshot.platform.strip()), issues, "platform", "platform is required")
    _validate_schema_version(snapshot.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_artifact_manifest(manifest: ArtifactManifest) -> ValidationReport:
    issues = _issues()
    _require(manifest.artifact_ref.kind == "artifact", issues, "artifact_ref", "kind must be 'artifact'")
    _require(bool(manifest.artifact_kind.strip()), issues, "artifact_kind", "artifact_kind is required")
    _validate_timestamp(manifest.created_at, issues, "created_at")
    _require(manifest.run_ref.kind == "run", issues, "run_ref", "kind must be 'run'")
    if manifest.stage_execution_ref is not None:
        _require(
            manifest.stage_execution_ref.kind == "stage",
            issues,
            "stage_execution_ref",
            "kind must be 'stage'",
        )
    if manifest.size_bytes is not None:
        _require(manifest.size_bytes >= 0, issues, "size_bytes", "size_bytes must be non-negative")
    _validate_schema_version(manifest.schema_version, issues, "schema_version")
    return _finalize(issues)


def validate_lineage_edge(edge: LineageEdge) -> ValidationReport:
    issues = _issues()
    _require(edge.relation_ref.kind == "relation", issues, "relation_ref", "kind must be 'relation'")
    _require(edge.relation_type in RELATION_TYPES, issues, "relation_type", "unsupported relation_type")
    _validate_timestamp(edge.recorded_at, issues, "recorded_at")
    _require(bool(edge.origin_marker.strip()), issues, "origin_marker", "origin_marker is required")
    _require(
        bool(edge.confidence_marker.strip()),
        issues,
        "confidence_marker",
        "confidence_marker is required",
    )
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
    _validate_timestamp(record.asserted_at, issues, "asserted_at")
    _validate_schema_version(record.schema_version, issues, "schema_version")
    return _finalize(issues)


def _validate_record_envelope(envelope: Any, issues: list[ValidationIssue]) -> None:
    _require(envelope.record_ref.kind == "record", issues, "envelope.record_ref", "kind must be 'record'")
    _require(envelope.run_ref.kind == "run", issues, "envelope.run_ref", "kind must be 'run'")
    _validate_timestamp(envelope.recorded_at, issues, "envelope.recorded_at")
    _validate_timestamp(envelope.observed_at, issues, "envelope.observed_at")
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
    _require(
        envelope.completeness_marker in {"complete", "partial", "unknown"},
        issues,
        "envelope.completeness_marker",
        "invalid completeness_marker",
    )
    _require(
        envelope.degradation_marker in {"none", "partial_failure", "capture_gap", "compatibility_upgrade"},
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
    _require(bool(record.payload.event_key.strip()), issues, "payload.event_key", "event_key is required")
    _require(
        record.payload.level in {"debug", "info", "warning", "error", "critical"},
        issues,
        "payload.level",
        "invalid event level",
    )
    if record.payload.subject_ref is not None:
        _require(bool(record.payload.subject_ref.strip()), issues, "payload.subject_ref", "subject_ref must not be blank")
    return _finalize(issues)


def validate_metric_record(record: MetricRecord) -> ValidationReport:
    issues = _issues()
    _validate_record_envelope(record.envelope, issues)
    _require(record.envelope.record_type == "metric", issues, "envelope.record_type", "record_type must be 'metric'")
    _require(bool(record.payload.metric_key.strip()), issues, "payload.metric_key", "metric_key is required")
    _require(
        record.payload.value_type in {"scalar", "integer", "float"},
        issues,
        "payload.value_type",
        "invalid value_type",
    )
    if record.payload.subject_ref is not None:
        _require(bool(record.payload.subject_ref.strip()), issues, "payload.subject_ref", "subject_ref must not be blank")
    if record.payload.slice_ref is not None:
        _require(bool(record.payload.slice_ref.strip()), issues, "payload.slice_ref", "slice_ref must not be blank")
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
    _require(bool(record.payload.span_id.strip()), issues, "payload.span_id", "span_id is required")
    _require(bool(record.payload.trace_id.strip()), issues, "payload.trace_id", "trace_id is required")
    _validate_timestamp(record.payload.started_at, issues, "payload.started_at")
    _validate_timestamp(record.payload.ended_at, issues, "payload.ended_at")
    _require(
        record.payload.started_at <= record.payload.ended_at,
        issues,
        "payload.ended_at",
        "ended_at must be >= started_at",
    )
    return _finalize(issues)
