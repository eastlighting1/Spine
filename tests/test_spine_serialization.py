import json
from pathlib import Path

import pytest

from spine import (
    ArtifactManifest,
    SerializationError,
    StableRef,
    deserialize_artifact_manifest,
    deserialize_metric_record,
    deserialize_project,
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

    assert result.value.project_ref == StableRef("project", "nova")
    assert result.value.created_at.endswith("Z")
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

    assert result.value.hash_value == "sha256:abc123"
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
