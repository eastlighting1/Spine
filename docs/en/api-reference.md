# API Reference

[User Guide Home](./README.md)

This page is a single reference document that collects the public API exposed through `import spine` in one place.

## Core Types

### `spine.StableRef`

`StableRef(kind, value)`

The canonical reference type used throughout Spine.

Parameters:

- `kind`: reference kind. Examples: `project`, `run`, `record`, `artifact`
- `value`: reference value

Returns:

- `StableRef`

Raises:

- `ValueError`: raised if the `kind` or `value` format is invalid

Methods:

- `StableRef.parse(raw)`: parse a `"kind:value"` string
- `str(ref)`: return a `"kind:value"` string
- `ref.to_dict()`: return `{"kind": ..., "value": ...}`

Example:

```python
from spine import StableRef

project_ref = StableRef("project", "nova")
run_ref = StableRef.parse("run:train-20260330-01")
```

See also:

- `spine.normalize_timestamp`
- `spine.Project`

### `spine.normalize_timestamp`

`normalize_timestamp(value)`

Normalize an input timestamp into ISO-8601 UTC `Z` form.

Parameters:

- `value`: `str | datetime`

Returns:

- `str`

Raises:

- `ValueError`: may be raised if the value is not a parseable date/time form

Example:

```python
from spine import normalize_timestamp

normalize_timestamp("2026-03-30T09:00:00")
# "2026-03-30T09:00:00Z"
```

See also:

- `spine.StableRef`
- `spine.deserialize_project`
- `spine.read_compat_project`

### `spine.ExtensionFieldSet`

`ExtensionFieldSet(namespace, fields={})`

A namespace-based extension field set.

Parameters:

- `namespace`: a namespace string containing `.`
- `fields`: extension field dict

Returns:

- `ExtensionFieldSet`

Raises:

- `ValueError`: raised if the namespace does not contain `.`

Example:

```python
from spine import ExtensionFieldSet

ext = ExtensionFieldSet(
    namespace="ml.team",
    fields={"owner": "research-platform", "priority": "high"},
)
```

See also:

- `spine.ExtensionRegistry`
- `spine.ArtifactManifest`

### `spine.ExtensionRegistry`

`ExtensionRegistry()`

Registry for managing extension namespace ownership.

Methods:

- `register(namespace, owner)`
- `is_registered(namespace)`
- `owner_for(namespace)`

Raises:

- `ExtensionError`: raised when extension policy is violated

Example:

```python
from spine import ExtensionRegistry

registry = ExtensionRegistry()
registry.register("ml.team", owner="research-platform")
```

See also:

- `spine.ExtensionFieldSet`
- `spine.ExtensionError`

## Context Models

### `spine.Project`

`Project(project_ref, name, created_at, description=None, tags={}, schema_version="1.0.0", extensions=())`

Top-level project context.

Parameters:

- `project_ref`: `StableRef`, `kind="project"`
- `name`
- `created_at`
- `description`
- `tags`
- `schema_version`
- `extensions`

Returns:

- `Project`

Example:

```python
from spine import Project, StableRef

project = Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00Z",
)
```

See also:

- `spine.Run`
- `spine.validate_project`
- `spine.deserialize_project`

### `spine.Run`

`Run(run_ref, project_ref, name, status, started_at, ended_at=None, description=None, schema_version="1.0.0", extensions=())`

One execution unit.

Parameters:

- `run_ref`: `StableRef`, `kind="run"`
- `project_ref`
- `name`
- `status`
- `started_at`
- `ended_at`
- `description`
- `schema_version`
- `extensions`

Returns:

- `Run`

Example:

```python
from spine import Run, StableRef

run = Run(
    run_ref=StableRef("run", "train-20260330-01"),
    project_ref=StableRef("project", "nova"),
    name="baseline-resnet50",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)
```

See also:

- `spine.Project`
- `spine.StageExecution`
- `spine.validate_run`

### `spine.StageExecution`

`StageExecution(stage_execution_ref, run_ref, stage_name, status, started_at, ended_at=None, order_index=None, schema_version="1.0.0", extensions=())`

A stage execution inside a run.

Parameters:

- `stage_execution_ref`: `StableRef`, `kind="stage"`
- `run_ref`
- `stage_name`
- `status`
- `started_at`
- `ended_at`
- `order_index`
- `schema_version`
- `extensions`

Returns:

- `StageExecution`

Example:

```python
from spine import StageExecution, StableRef

stage = StageExecution(
    stage_execution_ref=StableRef("stage", "train"),
    run_ref=StableRef("run", "train-20260330-01"),
    stage_name="train",
    status="running",
    started_at="2026-03-30T09:06:00Z",
)
```

See also:

- `spine.Run`
- `spine.OperationContext`
- `spine.validate_stage_execution`

### `spine.OperationContext`

`OperationContext(operation_context_ref, run_ref, stage_execution_ref, operation_name, observed_at, schema_version="1.0.0", extensions=())`

A detailed execution unit such as a step, request, or task.

Parameters:

- `operation_context_ref`: `StableRef`, `kind="op"`
- `run_ref`
- `stage_execution_ref`
- `operation_name`
- `observed_at`
- `schema_version`
- `extensions`

Returns:

- `OperationContext`

Example:

```python
from spine import OperationContext, StableRef

op = OperationContext(
    operation_context_ref=StableRef("op", "request-0001"),
    run_ref=StableRef("run", "serving-20260330"),
    stage_execution_ref=None,
    operation_name="predict",
    observed_at="2026-03-30T09:10:00Z",
)
```

See also:

- `spine.RecordEnvelope`
- `spine.TraceSpanRecord`
- `spine.validate_operation_context`

### `spine.EnvironmentSnapshot`

`EnvironmentSnapshot(environment_snapshot_ref, run_ref, captured_at, python_version, platform, packages={}, environment_variables={}, schema_version="1.0.0", extensions=())`

Environment information capture object.

Parameters:

- `environment_snapshot_ref`: `StableRef`, `kind="env"`
- `run_ref`
- `captured_at`
- `python_version`
- `platform`
- `packages`
- `environment_variables`
- `schema_version`
- `extensions`

Returns:

- `EnvironmentSnapshot`

Example:

```python
from spine import EnvironmentSnapshot, StableRef

snapshot = EnvironmentSnapshot(
    environment_snapshot_ref=StableRef("env", "train-env-01"),
    run_ref=StableRef("run", "train-20260330-01"),
    captured_at="2026-03-30T09:05:00Z",
    python_version="3.14.3",
    platform="win32",
)
```

See also:

- `spine.Run`
- `spine.validate_environment_snapshot`

## Record Models

### `spine.RecordEnvelope`

`RecordEnvelope(record_ref, record_type, recorded_at, observed_at, producer_ref, run_ref, stage_execution_ref, operation_context_ref, correlation_refs=..., completeness_marker="complete", degradation_marker="none", schema_version="1.0.0", extensions=())`

The shared envelope used by events, metrics, and traces.

Parameters:

- `record_ref`: `StableRef`, `kind="record"`
- `record_type`: `structured_event`, `metric`, `trace_span`
- `recorded_at`
- `observed_at`
- `producer_ref`
- `run_ref`
- `stage_execution_ref`
- `operation_context_ref`
- `correlation_refs`
- `completeness_marker`
- `degradation_marker`
- `schema_version`
- `extensions`

Returns:

- `RecordEnvelope`

See also:

- `spine.StructuredEventRecord`
- `spine.MetricRecord`
- `spine.TraceSpanRecord`

### `spine.StructuredEventPayload`

`StructuredEventPayload(event_key, level, message, subject_ref=None, attributes={}, origin_marker="explicit_capture")`

A structured event payload.

Parameters:

- `event_key`
- `level`
- `message`
- `subject_ref`
- `attributes`
- `origin_marker`

Returns:

- `StructuredEventPayload`

See also:

- `spine.StructuredEventRecord`

### `spine.StructuredEventRecord`

`StructuredEventRecord(envelope, payload)`

A structured event record.

Parameters:

- `envelope`: `RecordEnvelope`, `record_type="structured_event"`
- `payload`: `StructuredEventPayload`

Returns:

- `StructuredEventRecord`

Example:

```python
from spine import RecordEnvelope, StableRef, StructuredEventPayload, StructuredEventRecord

event = StructuredEventRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "event-epoch-1-start"),
        record_type="structured_event",
        recorded_at="2026-03-30T09:07:00Z",
        observed_at="2026-03-30T09:07:00Z",
        producer_ref="scribe.python.local",
        run_ref=StableRef("run", "train-20260330-01"),
        stage_execution_ref=StableRef("stage", "train"),
        operation_context_ref=None,
    ),
    payload=StructuredEventPayload(
        event_key="training.epoch.started",
        level="info",
        message="Epoch 1 started.",
    ),
)
```

See also:

- `spine.RecordEnvelope`
- `spine.validate_structured_event_record`

### `spine.MetricPayload`

`MetricPayload(metric_key, value, value_type, unit=None, aggregation_scope="step", subject_ref=None, slice_ref=None, tags={}, summary_basis=None)`

A numeric observation payload.

Parameters:

- `metric_key`
- `value`
- `value_type`
- `unit`
- `aggregation_scope`
- `subject_ref`
- `slice_ref`
- `tags`
- `summary_basis`

Returns:

- `MetricPayload`

See also:

- `spine.MetricRecord`

### `spine.MetricRecord`

`MetricRecord(envelope, payload)`

A metric record.

Parameters:

- `envelope`: `RecordEnvelope`, `record_type="metric"`
- `payload`: `MetricPayload`

Returns:

- `MetricRecord`

Example:

```python
from spine import MetricPayload, MetricRecord, RecordEnvelope, StableRef

metric = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-step-42"),
        record_type="metric",
        recorded_at="2026-03-30T09:08:30Z",
        observed_at="2026-03-30T09:08:30Z",
        producer_ref="scribe.python.local",
        run_ref=StableRef("run", "train-20260330-01"),
        stage_execution_ref=StableRef("stage", "train"),
        operation_context_ref=StableRef("op", "step-42"),
    ),
    payload=MetricPayload(
        metric_key="training.loss",
        value=0.4821,
        value_type="scalar",
        unit="ratio",
    ),
)
```

See also:

- `spine.MetricPayload`
- `spine.validate_metric_record`
- `spine.deserialize_metric_record`

### `spine.TraceSpanPayload`

`TraceSpanPayload(span_id, trace_id, parent_span_id, span_name, started_at, ended_at, status, span_kind, attributes={}, linked_refs=())`

A trace span payload.

Parameters:

- `span_id`
- `trace_id`
- `parent_span_id`
- `span_name`
- `started_at`
- `ended_at`
- `status`
- `span_kind`
- `attributes`
- `linked_refs`

Returns:

- `TraceSpanPayload`

See also:

- `spine.TraceSpanRecord`

### `spine.TraceSpanRecord`

`TraceSpanRecord(envelope, payload)`

A trace span record.

Parameters:

- `envelope`: `RecordEnvelope`, `record_type="trace_span"`
- `payload`: `TraceSpanPayload`

Returns:

- `TraceSpanRecord`

Example:

```python
from spine import RecordEnvelope, StableRef, TraceSpanPayload, TraceSpanRecord

trace = TraceSpanRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "trace-request-0001"),
        record_type="trace_span",
        recorded_at="2026-03-30T09:10:01Z",
        observed_at="2026-03-30T09:10:01Z",
        producer_ref="gateway.inference.local",
        run_ref=StableRef("run", "serving-20260330"),
        stage_execution_ref=None,
        operation_context_ref=StableRef("op", "request-0001"),
    ),
    payload=TraceSpanPayload(
        span_id="span-0001",
        trace_id="trace-0001",
        parent_span_id=None,
        span_name="predict.request",
        started_at="2026-03-30T09:10:00Z",
        ended_at="2026-03-30T09:10:01Z",
        status="ok",
        span_kind="request",
    ),
)
```

See also:

- `spine.RecordEnvelope`
- `spine.OperationContext`
- `spine.validate_trace_span_record`

## Artifact And Lineage Models

### `spine.ArtifactManifest`

`ArtifactManifest(artifact_ref, artifact_kind, created_at, producer_ref, run_ref, stage_execution_ref, location_ref, hash_value=None, size_bytes=None, attributes={}, schema_version="1.0.0", extensions=())`

An execution output such as a checkpoint, report, or dataset.

Parameters:

- `artifact_ref`: `StableRef`, `kind="artifact"`
- `artifact_kind`
- `created_at`
- `producer_ref`
- `run_ref`
- `stage_execution_ref`
- `location_ref`
- `hash_value`
- `size_bytes`
- `attributes`
- `schema_version`
- `extensions`

Returns:

- `ArtifactManifest`

Example:

```python
from spine import ArtifactManifest, StableRef

artifact = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=StableRef("stage", "train"),
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
)
```

See also:

- `spine.LineageEdge`
- `spine.validate_artifact_manifest`
- `spine.read_compat_artifact_manifest`

### `spine.LineageEdge`

`LineageEdge(relation_ref, relation_type, source_ref, target_ref, recorded_at, origin_marker, confidence_marker, operation_context_ref=None, evidence_refs=(), schema_version="1.0.0", extensions=())`

Represents a semantic relationship between two refs.

Parameters:

- `relation_ref`: `StableRef`, `kind="relation"`
- `relation_type`
- `source_ref`
- `target_ref`
- `recorded_at`
- `origin_marker`
- `confidence_marker`
- `operation_context_ref`
- `evidence_refs`
- `schema_version`
- `extensions`

Returns:

- `LineageEdge`

See also:

- `spine.ArtifactManifest`
- `spine.ProvenanceRecord`
- `spine.validate_lineage_edge`

### `spine.ProvenanceRecord`

`ProvenanceRecord(provenance_ref, relation_ref, formation_context_ref, policy_ref, evidence_bundle_ref, assertion_mode, asserted_at, schema_version="1.0.0", extensions=())`

The formation basis for a lineage assertion.

Parameters:

- `provenance_ref`: `StableRef`, `kind="provenance"`
- `relation_ref`
- `formation_context_ref`
- `policy_ref`
- `evidence_bundle_ref`
- `assertion_mode`
- `asserted_at`
- `schema_version`
- `extensions`

Returns:

- `ProvenanceRecord`

See also:

- `spine.LineageEdge`
- `spine.validate_provenance_record`

## Validation

### `spine.ValidationIssue`

`ValidationIssue(path, message)`

A single validation failure item.

Parameters:

- `path`
- `message`

Returns:

- `ValidationIssue`

See also:

- `spine.ValidationReport`

### `spine.ValidationReport`

`ValidationReport(valid, issues=())`

A validation result object.

Parameters:

- `valid`
- `issues`

Methods:

- `raise_for_errors()`: raise `ValidationError` if invalid

Returns:

- `ValidationReport`

See also:

- `spine.ValidationIssue`
- `spine.validate_project`
- `spine.validate_metric_record`

### validator functions

All validators return `ValidationReport`.

#### `spine.validate_project(project)`

Validate a `Project`.

Checks:

- `project_ref.kind == "project"`
- `name` is not blank
- `created_at` is a normalized timestamp
- `schema_version` matches

Returns:

- `ValidationReport`

Raises:

- `ValidationError`: when `report.raise_for_errors()` is called

Example:

```python
from spine import validate_project

report = validate_project(project)
report.raise_for_errors()
```

See also:

- `spine.Project`
- `spine.ValidationReport`

#### `spine.validate_run(run)`

Validate a `Run`.

Returns:

- `ValidationReport`

See also:

- `spine.Run`

#### `spine.validate_stage_execution(stage)`

Validate a `StageExecution`.

Returns:

- `ValidationReport`

See also:

- `spine.StageExecution`

#### `spine.validate_operation_context(operation)`

Validate an `OperationContext`.

Returns:

- `ValidationReport`

See also:

- `spine.OperationContext`

#### `spine.validate_environment_snapshot(snapshot)`

Validate an `EnvironmentSnapshot`.

Returns:

- `ValidationReport`

See also:

- `spine.EnvironmentSnapshot`

#### `spine.validate_artifact_manifest(manifest)`

Validate an `ArtifactManifest`.

Returns:

- `ValidationReport`

See also:

- `spine.ArtifactManifest`

#### `spine.validate_lineage_edge(edge)`

Validate a `LineageEdge`.

Returns:

- `ValidationReport`

See also:

- `spine.LineageEdge`

#### `spine.validate_provenance_record(record)`

Validate a `ProvenanceRecord`.

Returns:

- `ValidationReport`

See also:

- `spine.ProvenanceRecord`

#### `spine.validate_structured_event_record(record)`

Validate a `StructuredEventRecord`.

Returns:

- `ValidationReport`

See also:

- `spine.StructuredEventRecord`

#### `spine.validate_metric_record(record)`

Validate a `MetricRecord`.

Checks:

- `envelope.record_type == "metric"`
- `metric_key` is not blank
- `value_type` is in the allowed set

Returns:

- `ValidationReport`

Raises:

- `ValidationError`: when `report.raise_for_errors()` is called

See also:

- `spine.MetricRecord`
- `spine.ValidationReport`

#### `spine.validate_trace_span_record(record)`

Validate a `TraceSpanRecord`.

Returns:

- `ValidationReport`

See also:

- `spine.TraceSpanRecord`

## Serialization

### `spine.to_payload`

`to_payload(obj)`

Serialize a canonical object into a deterministic JSON-compatible payload.

Parameters:

- `obj`: Spine canonical object

Returns:

- `dict`

Raises:

- `SerializationError`

Example:

```python
from spine import to_payload

payload = to_payload(metric)
```

See also:

- `spine.to_json`
- `spine.deserialize_metric_record`

### `spine.to_json`

`to_json(obj)`

Serialize a canonical object into a deterministic JSON string.

Parameters:

- `obj`

Returns:

- `str`

Raises:

- `SerializationError`

Example:

```python
from spine import to_json

encoded = to_json(metric)
```

See also:

- `spine.to_payload`

### deserializer functions

Read current-schema payloads into current canonical objects.

#### `spine.deserialize_project(payload)`

Returns:

- `Project`

Raises:

- `SerializationError`

Example:

```python
from spine import deserialize_project

project = deserialize_project(
    {
        "project_ref": "project:nova",
        "name": "NovaVision",
        "created_at": "2026-03-30T09:00:00Z",
        "schema_version": "1.0.0",
    }
)
```

See also:

- `spine.Project`
- `spine.read_compat_project`

#### `spine.deserialize_run(payload)`

Returns:

- `Run`

Raises:

- `SerializationError`

See also:

- `spine.Run`

#### `spine.deserialize_stage_execution(payload)`

Returns:

- `StageExecution`

Raises:

- `SerializationError`

See also:

- `spine.StageExecution`

#### `spine.deserialize_operation_context(payload)`

Returns:

- `OperationContext`

Raises:

- `SerializationError`

See also:

- `spine.OperationContext`

#### `spine.deserialize_environment_snapshot(payload)`

Returns:

- `EnvironmentSnapshot`

Raises:

- `SerializationError`

See also:

- `spine.EnvironmentSnapshot`

#### `spine.deserialize_artifact_manifest(payload)`

Returns:

- `ArtifactManifest`

Raises:

- `SerializationError`

See also:

- `spine.ArtifactManifest`
- `spine.read_compat_artifact_manifest`

#### `spine.deserialize_lineage_edge(payload)`

Returns:

- `LineageEdge`

Raises:

- `SerializationError`

See also:

- `spine.LineageEdge`

#### `spine.deserialize_provenance_record(payload)`

Returns:

- `ProvenanceRecord`

Raises:

- `SerializationError`

See also:

- `spine.ProvenanceRecord`

#### `spine.deserialize_structured_event_record(payload)`

Returns:

- `StructuredEventRecord`

Raises:

- `SerializationError`

See also:

- `spine.StructuredEventRecord`

#### `spine.deserialize_metric_record(payload)`

Returns:

- `MetricRecord`

Raises:

- `SerializationError`

See also:

- `spine.MetricRecord`
- `spine.to_payload`

#### `spine.deserialize_trace_span_record(payload)`

Returns:

- `TraceSpanRecord`

Raises:

- `SerializationError`

See also:

- `spine.TraceSpanRecord`

## Compatibility

### `spine.CompatibilityNote`

`CompatibilityNote(path, message)`

An individual transformation record emitted during a compatibility upgrade.

Parameters:

- `path`
- `message`

Returns:

- `CompatibilityNote`

See also:

- `spine.CompatibilityResult`

### `spine.CompatibilityResult`

`CompatibilityResult(value, source_schema_version, notes=())`

Compatibility reader result.

Parameters:

- `value`
- `source_schema_version`
- `notes`

Returns:

- `CompatibilityResult`

See also:

- `spine.read_compat_project`
- `spine.read_compat_artifact_manifest`

### compatibility reader functions

#### `spine.read_compat_project(payload)`

Read a legacy project payload as a current-schema `Project`.

Returns:

- `CompatibilityResult`

Raises:

- `CompatibilityError`

Notes:

- legacy `ref` -> `project_ref`
- legacy `created` -> `created_at`
- timestamp normalization

Example:

```python
from spine import read_compat_project

result = read_compat_project(
    {
        "schema_version": "0.9.0",
        "ref": "project:nova",
        "name": "NovaVision",
        "created": "2026-03-30T09:00:00",
    }
)
```

See also:

- `spine.deserialize_project`
- `spine.CompatibilityResult`

#### `spine.read_compat_artifact_manifest(payload)`

Read a legacy artifact payload as a current-schema `ArtifactManifest`.

Returns:

- `CompatibilityResult`

Raises:

- `CompatibilityError`

Notes:

- legacy `hash` -> `hash_value`
- timestamp normalization

See also:

- `spine.ArtifactManifest`
- `spine.CompatibilityResult`

## Exceptions

### `spine.SpineError`

Base Spine exception type.

See also:

- `spine.ValidationError`
- `spine.SerializationError`
- `spine.CompatibilityError`
- `spine.ExtensionError`

### `spine.ValidationError`

Used when validation fails.

### `spine.SerializationError`

Used when serialization or deserialization fails.

### `spine.CompatibilityError`

Used when a compatibility reader cannot read a payload.

### `spine.ExtensionError`

Used when extension registry policy is violated.
