# Getting Started

[User Guide Home](./README.md)

This page is the most practical starting point for a first-time Spine user. Its goals are three things:

1. get Spine importable in your local environment,
2. build a minimal `Project -> Run -> MetricRecord` flow by hand,
3. get an intuitive sense of what validation and serialization do.

By the time you finish this page, you should at least be able to implement the basic pattern of "build Spine objects, validate them, and emit them in a serialized form."

## What Problem Spine Solves

Spine is a library for standardizing the data contract shared across ML observability systems. Without it, teams tend to diverge on all of the following:

- metric payload field names,
- run id rules,
- artifact metadata structure,
- timestamp format,
- lineage representation.

In that state, collection, ingestion, search, lineage analysis, and reproducibility checks all become harder.

To reduce that drift, Spine provides:

- fixed data models,
- strict validation,
- stable JSON serialization,
- deserializers for the current schema,
- compatibility readers for legacy payloads.

In short, Spine is a library that says, "do not let ML observability data drift arbitrarily; bind it to a shared contract."

## Core Ideas To Know First

The most important thing about Spine is that it asks you to build meaningful domain objects first instead of passing around loose dicts.

The most basic flow looks like this:

```text
Project
  -> Run
    -> StageExecution
      -> RecordEnvelope + Payload
```

Once that picture is clear, the rest of the guide becomes much easier.

- `Project`: a top-level unit such as a product or model family
- `Run`: one concrete execution
- `StageExecution`: a major phase inside a run
- `RecordEnvelope + Payload`: the actual observed data

At the beginning, `Project`, `Run`, and `MetricRecord` are enough.

## Installation And Execution

### Run Locally Right Away

For local development, the simplest setup is an editable install through `uv`.

```bash
uv run --with-editable . python
```

This lets you import the source you are currently editing directly.

### Run Tests

Use the following command to run the test suite:

```bash
uv run --with-editable . --with pytest python -m pytest -q
```

When you are checking a fresh environment, this is usually the fastest sanity check.

### Check Imports

After installation, it is a good idea to confirm that at least the command below works:

```bash
uv run --with-editable . python -c "import spine; print(spine.__file__)"
```

If this succeeds, your workspace is resolving the local `spine` package correctly.

## Basic Import Pattern

Most users only need to import from the top-level `spine` package.

```python
from spine import (
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    Run,
    StableRef,
    validate_metric_record,
    validate_project,
    validate_run,
)
```

At the beginning, it is enough to remember the following:

- build models with `Project`, `Run`, and `MetricRecord`,
- use `StableRef` for identity,
- validate with `validate_*`,
- emit payloads with `to_payload()` and `to_json()`.

For library users, `spine` is the public API boundary. Unless you are extending Spine or developing the library itself, it is usually better to avoid importing internal modules such as `spine.models...`.

## Basic Rules When Building Spine Objects

Three things confuse new Spine users most often.

### 1. Use `StableRef` Instead Of Raw Strings For Identity

Good examples:

```python
StableRef("project", "nova")
StableRef("run", "train-20260330-01")
```

Examples to avoid:

```python
"project:nova"
"run-20260330-01"
```

Strings are fine at the serialized payload layer, but inside the model layer `StableRef` is much better for validation and for expressing meaning clearly.

### 2. Use UTC `Z` Timestamps

Good example:

```text
2026-03-30T09:00:00Z
```

Examples to avoid:

```text
2026-03-30T09:00:00
2026/03/30 09:00:00
```

Current validation checks that major timestamp fields follow this normalized format.

### 3. Validate Right After Construction

In Spine, the safest pattern is to validate an object immediately after you build it.

```python
report = validate_project(project)
report.raise_for_errors()
```

This greatly reduces the chance of discovering broken data only at serialization time or right before persistence.

## Build Your First Object: Project

The most common starting point is `Project`. A project is a long-lived logical unit.

```python
from spine import Project, StableRef, validate_project

project = Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00Z",
    description="Image classification project.",
    tags={"team": "research", "track": "vision"},
)

validate_project(project).raise_for_errors()
```

At this stage, it is enough to understand these field meanings:

- `project_ref`: project identifier,
- `name`: human-readable name,
- `created_at`: creation time,
- `description`: short description,
- `tags`: lightweight metadata.

### Why You Need `Project`

At first it can feel like "why not just send metrics?" But once you have `Project`, it becomes much easier to answer questions like these:

- which product or experiment family does this run belong to,
- which team owns it,
- what kind of workload is it.

## Build Your Second Object: Run

`Run` is one concrete execution.

```python
from spine import Run, validate_run

run = Run(
    run_ref=StableRef("run", "train-20260330-01"),
    project_ref=project.project_ref,
    name="baseline-resnet50",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)

validate_run(run).raise_for_errors()
```

At the beginning, these four fields matter most:

- `run_ref`: execution identifier,
- `project_ref`: which project it belongs to,
- `status`: execution status,
- `started_at`: execution start time.

Currently allowed statuses are:

- `created`
- `running`
- `completed`
- `failed`
- `cancelled`

## Build Your Third Object: The First Record

Most real observability data in Spine is represented as records. The easiest place to start is `MetricRecord`.

Spine records all follow the same high-level shape:

```text
RecordEnvelope + Payload
```

That means:

- envelope: execution context and metadata,
- payload: the actual metric value.

## Build Your First MetricRecord

```python
from spine import (
    MetricPayload,
    MetricRecord,
    RecordEnvelope,
    StableRef,
    validate_metric_record,
)

metric = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-step-42"),
        record_type="metric",
        recorded_at="2026-03-30T09:08:30Z",
        observed_at="2026-03-30T09:08:30Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=None,
        operation_context_ref=None,
    ),
    payload=MetricPayload(
        metric_key="training.loss",
        value=0.4821,
        value_type="scalar",
        unit="ratio",
        tags={"device": "cuda:0"},
    ),
)

validate_metric_record(metric).raise_for_errors()
```

### Fields To Notice In The Envelope First

- `record_ref`: record identifier
- `record_type`: `"metric"`
- `recorded_at`: when the system recorded it
- `observed_at`: when it was actually measured
- `producer_ref`: which producer emitted it
- `run_ref`: which run it belongs to

### Fields To Notice In The Payload First

- `metric_key`: metric name
- `value`: measured value
- `value_type`: type of value
- `unit`: measurement unit
- `tags`: auxiliary metadata

### Why Envelope And Payload Are Split

Metric, event, and trace records all differ in their actual content, but they share the same questions about "when was this recorded, where did it come from, and who produced it." Spine packages that shared metadata into `RecordEnvelope` so it can be reused consistently.

## Your First Serialization

Once an object is built and validation passes, you can serialize it as a payload or JSON.

```python
from spine import to_json, to_payload

payload = to_payload(metric)
encoded = to_json(metric)
```

The difference between the two functions:

- `to_payload()`: a JSON-compatible dict
- `to_json()`: a stable JSON string

For example, the result of `to_payload(metric)` looks roughly like this:

```python
{
    "record_ref": "record:metric-step-42",
    "record_type": "metric",
    "recorded_at": "2026-03-30T09:08:30Z",
    "observed_at": "2026-03-30T09:08:30Z",
    "producer_ref": "scribe.python.local",
    "run_ref": "run:train-20260330-01",
    "stage_execution_ref": None,
    "operation_context_ref": None,
    "correlation_refs": {
        "trace_id": None,
        "session_id": None,
    },
    "completeness_marker": "complete",
    "degradation_marker": "none",
    "schema_version": "1.0.0",
    "extensions": [],
    "payload": {
        "metric_key": "training.loss",
        "value": 0.4821,
        "value_type": "scalar",
        "unit": "ratio",
        "aggregation_scope": "step",
        "subject_ref": None,
        "slice_ref": None,
        "tags": {"device": "cuda:0"},
        "summary_basis": None,
    },
}
```

The key things to notice here are:

- `StableRef` becomes a `"kind:value"` string,
- dict key ordering stays deterministic,
- the result is easy to store, transmit, and compare later.

## Minimal End-To-End Example

The example below is the smallest complete flow that builds a Project, a Run, and a MetricRecord together.

```python
from spine import (
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    Run,
    StableRef,
    to_json,
    validate_metric_record,
    validate_project,
    validate_run,
)

project = Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00Z",
)
validate_project(project).raise_for_errors()

run = Run(
    run_ref=StableRef("run", "train-20260330-01"),
    project_ref=project.project_ref,
    name="baseline-resnet50",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)
validate_run(run).raise_for_errors()

metric = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-step-42"),
        record_type="metric",
        recorded_at="2026-03-30T09:08:30Z",
        observed_at="2026-03-30T09:08:30Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=None,
        operation_context_ref=None,
    ),
    payload=MetricPayload(
        metric_key="training.loss",
        value=0.4821,
        value_type="scalar",
    ),
)
validate_metric_record(metric).raise_for_errors()

print(to_json(metric))
```

This code shows the core Spine usage loop exactly as it is meant to be used.

1. Build objects.
2. Validate them.
3. Serialize them.

## What To Try Next

If you followed this page successfully, the next best steps are usually:

1. If you want to see a flow that includes `StageExecution`, read [Workflow Examples](./workflow-examples.md).
2. If you want to understand why Spine has this structure at all, read [Understanding Spine Models](./understanding-spine-models.md).
3. If you want detailed field definitions for each type, read [Context Models](./context-models.md), [Observability Records](./observability-records.md), and [Artifacts And Lineage](./artifacts-and-lineage.md).
4. If you want to understand how to read and handle validation failures, read [Validation Rules](./validation-rules.md).

## Related Files

- Basic example code: [`examples/basic_training_flow.py`](C:/Users/eastl/MLObservability/Spine/examples/basic_training_flow.py)
- Package entrypoint: [`src/spine/__init__.py`](C:/Users/eastl/MLObservability/Spine/src/spine/__init__.py)
