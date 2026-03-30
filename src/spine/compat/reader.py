"""Compatibility-aware readers for historical payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..exceptions import CompatibilityError
from ..models import ArtifactManifest, Project, SCHEMA_VERSION, StableRef, normalize_timestamp
from ..validation import validate_artifact_manifest, validate_project


@dataclass(frozen=True, slots=True)
class CompatibilityNote:
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    value: Project | ArtifactManifest
    source_schema_version: str
    notes: tuple[CompatibilityNote, ...] = field(default_factory=tuple)


def read_compat_project(payload: dict[str, Any]) -> CompatibilityResult:
    """Read a project payload under explicit compatibility rules."""
    schema_version = str(payload.get("schema_version", "0.9.0"))
    notes: list[CompatibilityNote] = []

    if schema_version not in {"0.9.0", SCHEMA_VERSION}:
        raise CompatibilityError(f"Unsupported project schema version: {schema_version}")

    project_ref_raw = payload.get("project_ref") or payload.get("ref")
    if "ref" in payload and "project_ref" not in payload:
        notes.append(CompatibilityNote(path="ref", message="Mapped legacy 'ref' to 'project_ref'."))

    created_at_raw = payload.get("created_at") or payload.get("created")
    if "created" in payload and "created_at" not in payload:
        notes.append(CompatibilityNote(path="created", message="Mapped legacy 'created' to 'created_at'."))

    project = Project(
        project_ref=StableRef.parse(str(project_ref_raw)),
        name=str(payload["name"]),
        created_at=normalize_timestamp(str(created_at_raw)),
        description=payload.get("description"),
        tags={str(k): str(v) for k, v in dict(payload.get("tags", {})).items()},
        schema_version=SCHEMA_VERSION,
    )
    validate_project(project).raise_for_errors()
    if schema_version != SCHEMA_VERSION:
        notes.append(
            CompatibilityNote(
                path="schema_version",
                message=f"Upgraded payload from {schema_version} to {SCHEMA_VERSION}.",
            )
        )
    return CompatibilityResult(value=project, source_schema_version=schema_version, notes=tuple(notes))


def read_compat_artifact_manifest(payload: dict[str, Any]) -> CompatibilityResult:
    """Read an artifact payload under explicit compatibility rules."""
    schema_version = str(payload.get("schema_version", "0.9.0"))
    notes: list[CompatibilityNote] = []

    if schema_version not in {"0.9.0", SCHEMA_VERSION}:
        raise CompatibilityError(f"Unsupported artifact schema version: {schema_version}")

    hash_value = payload.get("hash_value")
    if hash_value is None and "hash" in payload:
        hash_value = payload["hash"]
        notes.append(CompatibilityNote(path="hash", message="Mapped legacy 'hash' to 'hash_value'."))

    manifest = ArtifactManifest(
        artifact_ref=StableRef.parse(str(payload["artifact_ref"])),
        artifact_kind=str(payload["artifact_kind"]),
        created_at=normalize_timestamp(str(payload["created_at"])),
        producer_ref=str(payload["producer_ref"]),
        run_ref=StableRef.parse(str(payload["run_ref"])),
        stage_execution_ref=StableRef.parse(str(payload["stage_execution_ref"]))
        if payload.get("stage_execution_ref")
        else None,
        location_ref=str(payload["location_ref"]),
        hash_value=str(hash_value) if hash_value is not None else None,
        size_bytes=int(payload["size_bytes"]) if payload.get("size_bytes") is not None else None,
        attributes=dict(payload.get("attributes", {})),
        schema_version=SCHEMA_VERSION,
    )
    validate_artifact_manifest(manifest).raise_for_errors()
    if schema_version != SCHEMA_VERSION:
        notes.append(
            CompatibilityNote(
                path="schema_version",
                message=f"Upgraded payload from {schema_version} to {SCHEMA_VERSION}.",
            )
        )
    return CompatibilityResult(value=manifest, source_schema_version=schema_version, notes=tuple(notes))
