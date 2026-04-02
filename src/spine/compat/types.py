"""Compatibility result types."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import ArtifactManifest, Project


@dataclass(frozen=True, slots=True)
class CompatibilityNote:
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    value: Project | ArtifactManifest
    source_schema_version: str
    notes: tuple[CompatibilityNote, ...] = field(default_factory=tuple)
