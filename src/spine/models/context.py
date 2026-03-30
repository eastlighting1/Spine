"""Canonical context spine models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .common import ExtensionFieldSet, SCHEMA_VERSION, StableRef, _sorted_metadata


@dataclass(frozen=True, slots=True)
class Project:
    project_ref: StableRef
    name: str
    created_at: str
    description: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", _sorted_metadata(self.tags))


@dataclass(frozen=True, slots=True)
class Run:
    run_ref: StableRef
    project_ref: StableRef
    name: str
    status: str
    started_at: str
    ended_at: str | None = None
    description: str | None = None
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()


@dataclass(frozen=True, slots=True)
class StageExecution:
    stage_execution_ref: StableRef
    run_ref: StableRef
    stage_name: str
    status: str
    started_at: str
    ended_at: str | None = None
    order_index: int | None = None
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationContext:
    operation_context_ref: StableRef
    run_ref: StableRef
    stage_execution_ref: StableRef | None
    operation_name: str
    observed_at: str
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    environment_snapshot_ref: StableRef
    run_ref: StableRef
    captured_at: str
    python_version: str
    platform: str
    packages: dict[str, str] = field(default_factory=dict)
    environment_variables: dict[str, str] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "packages", _sorted_metadata(self.packages))
        object.__setattr__(self, "environment_variables", _sorted_metadata(self.environment_variables))
