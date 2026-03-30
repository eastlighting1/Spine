"""Canonical relation and provenance models."""

from __future__ import annotations

from dataclasses import dataclass

from .common import ExtensionFieldSet, SCHEMA_VERSION, StableRef


RELATION_TYPES = frozenset(
    {
        "generated_from",
        "consumed_by",
        "produced_by",
        "packaged_from",
        "reported_by",
        "evaluated_on",
        "deployed_from",
        "used",
        "derived_from",
        "observed_in",
    }
)


@dataclass(frozen=True, slots=True)
class LineageEdge:
    relation_ref: StableRef
    relation_type: str
    source_ref: StableRef
    target_ref: StableRef
    recorded_at: str
    origin_marker: str
    confidence_marker: str
    operation_context_ref: StableRef | None = None
    evidence_refs: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    provenance_ref: StableRef
    relation_ref: StableRef
    formation_context_ref: StableRef | None
    policy_ref: str | None
    evidence_bundle_ref: str | None
    assertion_mode: str
    asserted_at: str
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()
