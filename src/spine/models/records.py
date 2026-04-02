"""Canonical record envelope models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from types import MappingProxyType

from .common import ExtensionFieldSet, SCHEMA_VERSION, StableRef, _frozen_mapping


@dataclass(frozen=True, slots=True)
class CorrelationRefs:
    trace_id: str | None = None
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class StructuredEventPayload:
    event_key: str
    level: str
    message: str
    subject_ref: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    origin_marker: str = "explicit_capture"

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _frozen_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class MetricPayload:
    metric_key: str
    value: int | float
    value_type: str
    unit: str | None = None
    aggregation_scope: str = "step"
    subject_ref: str | None = None
    slice_ref: str | None = None
    tags: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    summary_basis: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "tags", _frozen_mapping(self.tags))


@dataclass(frozen=True, slots=True)
class TraceSpanPayload:
    span_id: str
    trace_id: str
    parent_span_id: str | None
    span_name: str
    started_at: str
    ended_at: str
    status: str
    span_kind: str
    attributes: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    linked_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _frozen_mapping(self.attributes))


@dataclass(frozen=True, slots=True)
class RecordEnvelope:
    record_ref: StableRef
    record_type: str
    recorded_at: str
    observed_at: str
    producer_ref: str
    run_ref: StableRef
    stage_execution_ref: StableRef | None
    operation_context_ref: StableRef | None
    correlation_refs: CorrelationRefs = field(default_factory=CorrelationRefs)
    completeness_marker: str = "complete"
    degradation_marker: str = "none"
    schema_version: str = SCHEMA_VERSION
    extensions: tuple[ExtensionFieldSet, ...] = ()


@dataclass(frozen=True, slots=True)
class StructuredEventRecord:
    envelope: RecordEnvelope
    payload: StructuredEventPayload


@dataclass(frozen=True, slots=True)
class MetricRecord:
    envelope: RecordEnvelope
    payload: MetricPayload


@dataclass(frozen=True, slots=True)
class TraceSpanRecord:
    envelope: RecordEnvelope
    payload: TraceSpanPayload
