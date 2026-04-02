import json
from pathlib import Path

import pytest

from spine import (
    ArtifactManifest,
    CompatibilityError,
    LineageEdge,
    Project,
    RecordEnvelope,
    Run,
    SerializationError,
    StableRef,
    StructuredEventPayload,
    StructuredEventRecord,
    TraceSpanPayload,
    TraceSpanRecord,
    deserialize_artifact_manifest,
    deserialize_lineage_edge,
    deserialize_metric_record,
    deserialize_project,
    deserialize_run,
    deserialize_structured_event_record,
    deserialize_trace_span_record,
    read_compat_artifact_manifest,
    read_compat_project,
    to_json,
    to_payload,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_canonical_serialization_uses_string_refs() -> None:
    manifest = ArtifactManifest(
        artifact_ref=StableRef("artifact", "checkpoint-01"),
        artifact_kind="checkpoint",
        created_at="2026-03-29T10:29:58Z",
        producer_ref="sdk.python.local",
        run_ref=StableRef("run", "run-01"),
        stage_execution_ref=StableRef("stage", "train"),
        location_ref="file://artifacts/checkpoint-01.ckpt",
        hash_value="sha256:abc123",
    )

    payload = to_payload(manifest)
    encoded = to_json(manifest)

    assert payload["artifact_ref"] == "artifact:checkpoint-01"
    assert payload["run_ref"] == "run:run-01"
    assert "\"artifact_ref\":\"artifact:checkpoint-01\"" in encoded


def test_compat_reader_maps_legacy_project_fields() -> None:
    result = read_compat_project(
        {
            "schema_version": "0.9.0",
            "ref": "project:nova",
            "name": "NovaVision",
            "created": "2026-03-29T10:15:21",
        }
    )
    assert isinstance(result.value, Project)
    project = result.value

    assert project.project_ref == StableRef("project", "nova")
    assert project.created_at.endswith("Z")
    assert any(note.path == "ref" for note in result.notes)


def test_compat_reader_maps_legacy_artifact_hash_field() -> None:
    result = read_compat_artifact_manifest(
        {
            "schema_version": "0.9.0",
            "artifact_ref": "artifact:checkpoint-01",
            "artifact_kind": "checkpoint",
            "created_at": "2026-03-29T10:29:58Z",
            "producer_ref": "sdk.python.local",
            "run_ref": "run:run-01",
            "stage_execution_ref": "stage:train",
            "location_ref": "file://artifacts/checkpoint-01.ckpt",
            "hash": "sha256:abc123",
        }
    )
    assert isinstance(result.value, ArtifactManifest)
    manifest = result.value

    assert manifest.hash_value == "sha256:abc123"
    assert any(note.path == "hash" for note in result.notes)


def test_deserialize_project_from_fixture() -> None:
    payload = json.loads((FIXTURES_DIR / "project_v1.json").read_text(encoding="utf-8"))

    project = deserialize_project(payload)

    assert project.project_ref == StableRef("project", "nova")
    assert project.tags["team"] == "research"


def test_artifact_round_trip_from_fixture() -> None:
    payload = json.loads((FIXTURES_DIR / "artifact_manifest_v1.json").read_text(encoding="utf-8"))

    manifest = deserialize_artifact_manifest(payload)

    assert to_payload(manifest) == payload


def test_metric_record_deserializes_from_fixture() -> None:
    payload = json.loads((FIXTURES_DIR / "metric_record_v1.json").read_text(encoding="utf-8"))

    record = deserialize_metric_record(payload)

    assert record.payload.metric_key == "training.loss"
    assert record.envelope.operation_context_ref == StableRef("op", "step-42")


def test_deserialize_project_rejects_non_normalized_timestamp() -> None:
    with pytest.raises(SerializationError):
        deserialize_project(
            {
                "project_ref": "project:nova",
                "name": "NovaVision",
                "created_at": "2026-03-29T10:15:21",
                "schema_version": "1.0.0",
            }
        )


def test_deserialize_project_rejects_missing_required_field_with_serialization_error() -> None:
    with pytest.raises(SerializationError, match="Missing required field: name"):
        deserialize_project(
            {
                "project_ref": "project:nova",
                "created_at": "2026-03-29T10:15:21Z",
                "schema_version": "1.0.0",
            }
        )


def test_deserialize_project_rejects_non_mapping_tags_with_serialization_error() -> None:
    with pytest.raises(SerializationError, match="Field tags must be a mapping"):
        deserialize_project(
            {
                "project_ref": "project:nova",
                "name": "NovaVision",
                "created_at": "2026-03-29T10:15:21Z",
                "schema_version": "1.0.0",
                "tags": ["not", "a", "mapping"],
            }
        )


def test_to_json_rejects_unsupported_attribute_value_type() -> None:
    manifest = ArtifactManifest(
        artifact_ref=StableRef("artifact", "checkpoint-01"),
        artifact_kind="checkpoint",
        created_at="2026-03-29T10:29:58Z",
        producer_ref="sdk.python.local",
        run_ref=StableRef("run", "run-01"),
        stage_execution_ref=StableRef("stage", "train"),
        location_ref="file://artifacts/checkpoint-01.ckpt",
        attributes={"payload": object()},
    )

    with pytest.raises(SerializationError, match="Unsupported value type"):
        to_json(manifest)


def test_deserialize_record_rejects_non_mapping_payload_body() -> None:
    with pytest.raises(SerializationError, match="MetricPayload payload must be a mapping"):
        deserialize_metric_record(
            {
                "record_ref": "record:metric-1",
                "record_type": "metric",
                "recorded_at": "2026-03-29T10:16:02Z",
                "observed_at": "2026-03-29T10:16:02Z",
                "producer_ref": "sdk.python.local",
                "run_ref": "run:run-01",
                "stage_execution_ref": "stage:train",
                "operation_context_ref": "op:step-42",
                "schema_version": "1.0.0",
                "payload": ["not", "a", "mapping"],
            }
        )


# --- Compatibility reader coverage ---


def test_compat_reader_raises_for_unsupported_schema_version() -> None:
    with pytest.raises(CompatibilityError):
        read_compat_project(
            {
                "schema_version": "2.0.0",
                "project_ref": "project:nova",
                "name": "NovaVision",
                "created_at": "2026-03-29T10:15:21Z",
            }
        )


def test_compat_reader_artifact_raises_for_unsupported_schema_version() -> None:
    with pytest.raises(CompatibilityError):
        read_compat_artifact_manifest(
            {
                "schema_version": "99.0.0",
                "artifact_ref": "artifact:checkpoint-01",
                "artifact_kind": "checkpoint",
                "created_at": "2026-03-29T10:29:58Z",
                "producer_ref": "sdk.python.local",
                "run_ref": "run:run-01",
                "stage_execution_ref": "stage:train",
                "location_ref": "file://artifacts/checkpoint-01.ckpt",
            }
        )


def test_compat_reader_current_schema_produces_no_upgrade_note() -> None:
    result = read_compat_project(
        {
            "schema_version": "1.0.0",
            "project_ref": "project:nova",
            "name": "NovaVision",
            "created_at": "2026-03-29T10:15:21Z",
        }
    )
    assert result.source_schema_version == "1.0.0"
    assert not any(note.path == "schema_version" for note in result.notes)


def test_compat_reader_legacy_project_preserves_tags_through_upgrade() -> None:
    payload = {
        "schema_version": "0.9.0",
        "ref": "project:research",
        "name": "ResearchProject",
        "created": "2026-03-29T10:00:00",
        "tags": {"team": "ml", "env": "prod"},
    }
    result = read_compat_project(
        payload
    )
    assert isinstance(result.value, Project)
    project = result.value

    assert project.tags["team"] == "ml"
    assert project.tags["env"] == "prod"
    assert any(note.path == "ref" for note in result.notes)
    assert any(note.path == "created" for note in result.notes)
    assert any(note.path == "schema_version" for note in result.notes)
    assert "project_ref" not in payload


def test_compat_reader_artifact_does_not_mutate_input_payload() -> None:
    payload = {
        "schema_version": "0.9.0",
        "artifact_ref": "artifact:checkpoint-01",
        "artifact_kind": "checkpoint",
        "created_at": "2026-03-29T10:29:58Z",
        "producer_ref": "sdk.python.local",
        "run_ref": "run:run-01",
        "stage_execution_ref": "stage:train",
        "location_ref": "file://artifacts/checkpoint-01.ckpt",
        "hash": "sha256:abc123",
    }

    result = read_compat_artifact_manifest(payload)
    assert isinstance(result.value, ArtifactManifest)
    manifest = result.value

    assert manifest.hash_value == "sha256:abc123"
    assert "hash_value" not in payload


def test_compat_reader_rejects_non_mapping_root_payload() -> None:
    with pytest.raises(CompatibilityError, match="project payload must be a mapping"):
        read_compat_project(["not", "a", "mapping"])  # type: ignore[arg-type]


# --- Deterministic serialization ---


def test_to_json_output_is_deterministic_across_repeated_calls() -> None:
    manifest = ArtifactManifest(
        artifact_ref=StableRef("artifact", "checkpoint-01"),
        artifact_kind="checkpoint",
        created_at="2026-03-29T10:29:58Z",
        producer_ref="sdk.python.local",
        run_ref=StableRef("run", "run-01"),
        stage_execution_ref=StableRef("stage", "train"),
        location_ref="file://artifacts/checkpoint-01.ckpt",
        hash_value="sha256:abc123",
    )

    first = to_json(manifest)
    second = to_json(manifest)

    assert first == second


def test_to_json_top_level_keys_are_sorted_alphabetically() -> None:
    manifest = ArtifactManifest(
        artifact_ref=StableRef("artifact", "checkpoint-01"),
        artifact_kind="checkpoint",
        created_at="2026-03-29T10:29:58Z",
        producer_ref="sdk.python.local",
        run_ref=StableRef("run", "run-01"),
        stage_execution_ref=StableRef("stage", "train"),
        location_ref="file://artifacts/checkpoint-01.ckpt",
    )

    parsed = json.loads(to_json(manifest))
    keys = list(parsed.keys())

    assert keys == sorted(keys)


# --- Round-trip serialization for all record families ---


def test_deserialize_run_round_trip_preserves_all_fields() -> None:
    run = Run(
        run_ref=StableRef("run", "run-001"),
        project_ref=StableRef("project", "nova"),
        name="baseline",
        status="running",
        started_at="2026-03-29T10:00:00Z",
    )

    result = deserialize_run(to_payload(run))

    assert result.run_ref == StableRef("run", "run-001")
    assert result.project_ref == StableRef("project", "nova")
    assert result.name == "baseline"
    assert result.status == "running"
    assert result.started_at == "2026-03-29T10:00:00Z"


def test_deserialize_structured_event_record_round_trip() -> None:
    record = StructuredEventRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "evt-round-trip"),
            record_type="structured_event",
            recorded_at="2026-03-29T10:15:21Z",
            observed_at="2026-03-29T10:15:21Z",
            producer_ref="sdk.python.local",
            run_ref=StableRef("run", "run-01"),
            stage_execution_ref=StableRef("stage", "train"),
            operation_context_ref=StableRef("op", "epoch-1"),
        ),
        payload=StructuredEventPayload(
            event_key="training.epoch.started",
            level="info",
            message="Round-trip test.",
        ),
    )

    result = deserialize_structured_event_record(to_payload(record))

    assert result.payload.event_key == "training.epoch.started"
    assert result.payload.level == "info"
    assert result.envelope.run_ref == StableRef("run", "run-01")
    assert result.envelope.record_type == "structured_event"


def test_deserialize_trace_span_record_round_trip() -> None:
    record = TraceSpanRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "trace-round-trip"),
            record_type="trace_span",
            recorded_at="2026-03-29T10:16:05Z",
            observed_at="2026-03-29T10:16:05Z",
            producer_ref="sdk.python.local",
            run_ref=StableRef("run", "run-01"),
            stage_execution_ref=StableRef("stage", "train"),
            operation_context_ref=StableRef("op", "step-42"),
        ),
        payload=TraceSpanPayload(
            span_id="span-fwd",
            trace_id="trace-train-01",
            parent_span_id=None,
            span_name="model.forward",
            started_at="2026-03-29T10:16:03Z",
            ended_at="2026-03-29T10:16:04Z",
            status="ok",
            span_kind="model_call",
        ),
    )

    result = deserialize_trace_span_record(to_payload(record))

    assert result.payload.span_id == "span-fwd"
    assert result.payload.trace_id == "trace-train-01"
    assert result.payload.span_name == "model.forward"
    assert result.envelope.run_ref == StableRef("run", "run-01")


def test_deserialize_lineage_edge_round_trip() -> None:
    edge = LineageEdge(
        relation_ref=StableRef("relation", "rel-001"),
        relation_type="produced_by",
        source_ref=StableRef("artifact", "ckpt-001"),
        target_ref=StableRef("stage", "train"),
        recorded_at="2026-03-29T10:16:05Z",
        origin_marker="explicit",
        confidence_marker="high",
    )

    result = deserialize_lineage_edge(to_payload(edge))

    assert result.relation_ref == StableRef("relation", "rel-001")
    assert result.relation_type == "produced_by"
    assert result.source_ref == StableRef("artifact", "ckpt-001")
    assert result.target_ref == StableRef("stage", "train")
    assert result.origin_marker == "explicit"
