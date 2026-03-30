"""Artifact identity models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import ExtensionFieldSet, SCHEMA_VERSION, StableRef, _sorted_metadata


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    artifact_ref: StableRef
    artifact_kind: str
    created_at: str
    producer_ref: str
    run_ref: StableRef
    stage_execution_ref: StableRef | None
    location_ref: str
    hash_value: str | None = None
    size_bytes: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _sorted_metadata(self.attributes))
