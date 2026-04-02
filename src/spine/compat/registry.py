"""Compatibility registry types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .types import CompatibilityNote


MigrationFn = Callable[[dict[str, Any]], tuple[dict[str, Any], tuple[CompatibilityNote, ...]]]
CanonicalReaderFn = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True, slots=True)
class CompatSpec:
    family: str
    supported_versions: tuple[str, ...]
    target_version: str
    migrations: dict[str, MigrationFn]
    canonical_reader: CanonicalReaderFn
