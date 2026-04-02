"""Compatibility-aware readers for historical payloads."""

from __future__ import annotations

from typing import Any

from ..exceptions import CompatibilityError
from ..models import ArtifactManifest, Project
from ..serialization import deserialize_artifact_manifest, deserialize_project
from ..validation import validate_artifact_manifest, validate_project
from .migrations import migrate_artifact_090_to_100, migrate_project_090_to_100
from .registry import CompatSpec
from .types import CompatibilityNote, CompatibilityResult


PROJECT_COMPAT_SPEC = CompatSpec(
    family="project",
    supported_versions=("0.9.0", "1.0.0"),
    target_version="1.0.0",
    migrations={"0.9.0": migrate_project_090_to_100},
    canonical_reader=deserialize_project,
)

ARTIFACT_COMPAT_SPEC = CompatSpec(
    family="artifact_manifest",
    supported_versions=("0.9.0", "1.0.0"),
    target_version="1.0.0",
    migrations={"0.9.0": migrate_artifact_090_to_100},
    canonical_reader=deserialize_artifact_manifest,
)


def _require_mapping(payload: Any, family: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CompatibilityError(f"{family} payload must be a mapping")
    return dict(payload)


def _read_compat(payload: dict[str, Any], spec: CompatSpec) -> CompatibilityResult:
    payload = _require_mapping(payload, spec.family)
    schema_version = str(payload.get("schema_version", "0.9.0"))
    if schema_version not in spec.supported_versions:
        raise CompatibilityError(f"Unsupported {spec.family} schema version: {schema_version}")

    migrated_payload = dict(payload)
    notes: tuple[CompatibilityNote, ...] = ()
    if schema_version != spec.target_version:
        migration = spec.migrations.get(schema_version)
        if migration is None:
            raise CompatibilityError(
                f"No migration path for {spec.family} schema version: {schema_version}"
            )
        migrated_payload, notes = migration(migrated_payload)

    try:
        value = spec.canonical_reader(migrated_payload)
    except Exception as exc:
        raise CompatibilityError(f"Failed to read {spec.family} payload under compatibility rules") from exc

    return CompatibilityResult(value=value, source_schema_version=schema_version, notes=notes)


def read_compat_project(payload: dict[str, Any]) -> CompatibilityResult:
    """Read a project payload under explicit compatibility rules."""
    result = _read_compat(payload, PROJECT_COMPAT_SPEC)
    project = result.value
    if not isinstance(project, Project):
        raise CompatibilityError("Compatibility result for project did not produce a Project")
    try:
        validate_project(project).raise_for_errors()
    except Exception as exc:
        raise CompatibilityError("Explicit validation failed for compat project payload") from exc
    return result


def read_compat_artifact_manifest(payload: dict[str, Any]) -> CompatibilityResult:
    """Read an artifact payload under explicit compatibility rules."""
    result = _read_compat(payload, ARTIFACT_COMPAT_SPEC)
    manifest = result.value
    if not isinstance(manifest, ArtifactManifest):
        raise CompatibilityError(
            "Compatibility result for artifact_manifest did not produce an ArtifactManifest"
        )
    try:
        validate_artifact_manifest(manifest).raise_for_errors()
    except Exception as exc:
        raise CompatibilityError("Explicit validation failed for compat artifact payload") from exc
    return result
