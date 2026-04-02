"""Artifact identity models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from types import MappingProxyType

from .common import ExtensionFieldSet, SCHEMA_VERSION, StableRef, _frozen_mapping


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
    attributes: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _frozen_mapping(self.attributes))
