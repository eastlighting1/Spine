# API Reference

[사용자 가이드 홈](./README.md)

이 문서는 `import spine` 기준 public API를 한 곳에서 찾을 수 있도록 정리한 단일 참조 문서입니다.

## Core Types

### `spine.StableRef`

`StableRef(kind, value)`

Spine 전반에서 사용하는 canonical reference 타입입니다.

Parameters:

- `kind`: reference kind. 예: `project`, `run`, `record`, `artifact`
- `value`: reference value

Returns:

- `StableRef`

Raises:

- `ValueError`: `kind` 또는 `value` 형식이 유효하지 않으면 발생

Methods:

- `StableRef.parse(raw)`: `"kind:value"` 문자열을 파싱
- `str(ref)`: `"kind:value"` 문자열 반환
- `ref.to_dict()`: `{"kind": ..., "value": ...}` 반환

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

입력 timestamp를 ISO-8601 UTC `Z` 형식으로 정규화합니다.

Parameters:

- `value`: `str | datetime`

Returns:

- `str`

Raises:

- `ValueError`: 파싱 가능한 날짜/시간 형식이 아니면 발생 가능

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

namespace 기반 extension field 집합입니다.

Parameters:

- `namespace`: `.` 를 포함하는 namespace 문자열
- `fields`: extension field dict

Returns:

- `ExtensionFieldSet`

Raises:

- `ValueError`: namespace에 `.` 가 없으면 발생

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

Notes:

- Spine은 extension field mapping을 생성 시 정렬하고 read-only로 고정합니다.

### `spine.ExtensionRegistry`

`ExtensionRegistry()`

extension namespace ownership을 관리하는 레지스트리입니다.

Methods:

- `register(namespace, owner)`
- `is_registered(namespace)`
- `owner_for(namespace)`

Raises:

- `ExtensionError`: 정책 위반 시 발생

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

최상위 project 컨텍스트입니다.

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

Notes:

- `tags`는 생성 후 정렬된 read-only mapping으로 저장됩니다.

### `spine.Run`

`Run(run_ref, project_ref, name, status, started_at, ended_at=None, description=None, schema_version="1.0.0", extensions=())`

하나의 실행 단위입니다.

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

run 내부의 stage 실행입니다.

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

step, request, task 같은 세부 실행 단위입니다.

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

환경 정보 캡처 객체입니다.

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

Notes:

- `packages`와 `environment_variables`는 생성 후 정렬된 read-only mapping으로 저장됩니다.

## Record Models

### `spine.RecordEnvelope`

`RecordEnvelope(record_ref, record_type, recorded_at, observed_at, producer_ref, run_ref, stage_execution_ref, operation_context_ref, correlation_refs=..., completeness_marker="complete", degradation_marker="none", schema_version="1.0.0", extensions=())`

event, metric, trace가 공통으로 사용하는 envelope입니다.

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

Notes:

- `attributes`는 생성 후 정렬된 read-only mapping으로 저장됩니다.
- `spine.MetricRecord`
- `spine.TraceSpanRecord`

### `spine.StructuredEventPayload`

`StructuredEventPayload(event_key, level, message, subject_ref=None, attributes={}, origin_marker="explicit_capture")`

구조화된 event payload입니다.

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

구조화된 event record입니다.

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

수치형 관측값 payload입니다.

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

Notes:

- `tags`는 생성 후 정렬된 read-only mapping으로 저장됩니다.
- validation은 `value`와 `value_type`의 정합성도 검사합니다.

### `spine.MetricRecord`

`MetricRecord(envelope, payload)`

metric record입니다.

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

trace span payload입니다.

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

Notes:

- `attributes`는 생성 후 정렬된 read-only mapping으로 저장됩니다.

### `spine.TraceSpanRecord`

`TraceSpanRecord(envelope, payload)`

trace span record입니다.

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
        span_kind="client",
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

checkpoint, report, dataset 같은 실행 결과물입니다.

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

Notes:

- `attributes`는 생성 후 정렬된 read-only mapping으로 저장됩니다.

### `spine.LineageEdge`

`LineageEdge(relation_ref, relation_type, source_ref, target_ref, recorded_at, origin_marker, confidence_marker, operation_context_ref=None, evidence_refs=(), schema_version="1.0.0", extensions=())`

두 ref 사이의 의미적 관계를 나타냅니다.

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

lineage assertion의 형성 근거입니다.

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

단일 validation 실패 항목입니다.

Parameters:

- `path`
- `message`

Returns:

- `ValidationIssue`

See also:

- `spine.ValidationReport`

### `spine.ValidationReport`

`ValidationReport(valid, issues=())`

validation 결과 객체입니다.

Parameters:

- `valid`
- `issues`

Methods:

- `raise_for_errors()`: 유효하지 않으면 `ValidationError` 발생

Returns:

- `ValidationReport`

See also:

- `spine.ValidationIssue`
- `spine.validate_project`
- `spine.validate_metric_record`

### validator functions

모든 validator는 `ValidationReport`를 반환합니다.

#### `spine.validate_project(project)`

`Project`를 검증합니다.

Checks:

- `project_ref.kind == "project"`
- `name` 비어 있지 않음
- `created_at` 정규 timestamp
- `tags`의 key와 value는 비어 있지 않음
- `schema_version` 일치

Returns:

- `ValidationReport`

Raises:

- `ValidationError`: `report.raise_for_errors()` 호출 시

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

`Run`을 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.Run`

#### `spine.validate_stage_execution(stage)`

`StageExecution`을 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.StageExecution`

#### `spine.validate_operation_context(operation)`

`OperationContext`를 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.OperationContext`

#### `spine.validate_environment_snapshot(snapshot)`

`EnvironmentSnapshot`을 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.EnvironmentSnapshot`

#### `spine.validate_artifact_manifest(manifest)`

`ArtifactManifest`를 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.ArtifactManifest`

#### `spine.validate_lineage_edge(edge)`

`LineageEdge`를 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.LineageEdge`

#### `spine.validate_provenance_record(record)`

`ProvenanceRecord`를 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.ProvenanceRecord`

#### `spine.validate_structured_event_record(record)`

`StructuredEventRecord`를 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.StructuredEventRecord`

#### `spine.validate_metric_record(record)`

`MetricRecord`를 검증합니다.

Checks:

- `envelope.record_type == "metric"`
- `metric_key` 비어 있지 않음
- `value_type` 허용값
- `value`가 `value_type`과 일치함
- `aggregation_scope`가 허용값에 포함됨
- optional string 필드는 값이 있을 경우 비어 있지 않아야 함

Returns:

- `ValidationReport`

Raises:

- `ValidationError`: `report.raise_for_errors()` 호출 시

See also:

- `spine.MetricRecord`
- `spine.ValidationReport`

#### `spine.validate_trace_span_record(record)`

`TraceSpanRecord`를 검증합니다.

Returns:

- `ValidationReport`

See also:

- `spine.TraceSpanRecord`

## Serialization

### `spine.to_payload`

`to_payload(obj)`

canonical object를 deterministic JSON-compatible payload로 직렬화합니다.

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

canonical object를 deterministic JSON 문자열로 직렬화합니다.

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

current schema payload를 current canonical object로 읽습니다.

record 계열 deserializer는 canonical flat payload와 `to_payload()`가 만드는 중첩형 `{"envelope": ..., "payload": ...}` 구조를 모두 읽을 수 있습니다.

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

compatibility 업그레이드 중 발생한 개별 변환 기록입니다.

Parameters:

- `path`
- `message`

Returns:

- `CompatibilityNote`

See also:

- `spine.CompatibilityResult`

### `spine.CompatibilityResult`

`CompatibilityResult(value, source_schema_version, notes=())`

compatibility reader 결과입니다.

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

legacy project payload를 현재 schema `Project`로 읽습니다.

Returns:

- `CompatibilityResult`

Raises:

- `CompatibilityError`

Notes:

- legacy `ref` -> `project_ref`
- legacy `created` -> `created_at`
- timestamp 정규화
- current schema deserializer를 호출하기 전에 명시적인 migration step을 수행함

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

legacy artifact payload를 현재 schema `ArtifactManifest`로 읽습니다.

Returns:

- `CompatibilityResult`

Raises:

- `CompatibilityError`

Notes:

- legacy `hash` -> `hash_value`
- timestamp 정규화
- current schema deserializer를 호출하기 전에 명시적인 migration step을 수행함

See also:

- `spine.ArtifactManifest`
- `spine.CompatibilityResult`

## Exceptions

### `spine.SpineError`

Spine의 기본 예외 타입입니다.

See also:

- `spine.ValidationError`
- `spine.SerializationError`
- `spine.CompatibilityError`
- `spine.ExtensionError`

### `spine.ValidationError`

validation 실패 시 사용됩니다.

### `spine.SerializationError`

serialization 또는 deserialization 실패 시 사용됩니다.

### `spine.CompatibilityError`

compatibility reader가 payload를 읽지 못할 때 사용됩니다.

### `spine.ExtensionError`

extension registry 정책 위반 시 사용됩니다.
