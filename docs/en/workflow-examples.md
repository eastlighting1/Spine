# Workflow Examples

[User Guide Home](./README.md)

When teams first try to put Spine into a project, the most common question is usually, "In what order do I create these objects?" This page exists to answer that question.

It is best read as a page about the feel of assembling objects in the flow `Project -> Run -> Stage -> Record -> Artifact`, rather than as a page to memorize field definitions.

## Basic Training Flow

The basic example included in the project is [`examples/basic_training_flow.py`](C:/Users/eastl/MLObservability/Spine/examples/basic_training_flow.py).

Flow:

1. create `Project`,
2. create `Run`,
3. create `StageExecution`,
4. create `StructuredEventRecord`,
5. create `MetricRecord`,
6. create `ArtifactManifest`.

This order is not accidental. It directly reflects Spine's model layering.

- first create context,
- then create records inside that context,
- finally attach outputs and relationships.

That flow repeats across almost every Spine use case. Whether the scenario is training, evaluation, or deployment, the most stable order is usually "context -> observation -> outputs."

## Step-By-Step Example

```python
from spine import (
    ArtifactManifest,
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    Run,
    StableRef,
    StageExecution,
    StructuredEventPayload,
    StructuredEventRecord,
    validate_artifact_manifest,
    validate_metric_record,
    validate_project,
    validate_run,
    validate_stage_execution,
    validate_structured_event_record,
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

stage = StageExecution(
    stage_execution_ref=StableRef("stage", "train"),
    run_ref=run.run_ref,
    stage_name="train",
    status="running",
    started_at="2026-03-30T09:06:00Z",
)
validate_stage_execution(stage).raise_for_errors()

event = StructuredEventRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "event-epoch-1-start"),
        record_type="structured_event",
        recorded_at="2026-03-30T09:07:00Z",
        observed_at="2026-03-30T09:07:00Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=stage.stage_execution_ref,
        operation_context_ref=None,
    ),
    payload=StructuredEventPayload(
        event_key="training.epoch.started",
        level="info",
        message="Epoch 1 started.",
    ),
)
validate_structured_event_record(event).raise_for_errors()

metric = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-step-42"),
        record_type="metric",
        recorded_at="2026-03-30T09:08:30Z",
        observed_at="2026-03-30T09:08:30Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=stage.stage_execution_ref,
        operation_context_ref=StableRef("op", "step-42"),
    ),
    payload=MetricPayload(
        metric_key="training.loss",
        value=0.4821,
        value_type="scalar",
    ),
)
validate_metric_record(metric).raise_for_errors()

artifact = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=run.run_ref,
    stage_execution_ref=stage.stage_execution_ref,
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
    hash_value="sha256:abc123",
    size_bytes=184223744,
)
validate_artifact_manifest(artifact).raise_for_errors()
```

The shortest way to restate this example is:

1. create project and execution context,
2. emit events and metrics inside the stage,
3. register execution outputs as artifacts,
4. stop contract violations immediately with validation at each step.

So the point of the example is not the line-by-line code itself. It is that Spine is being used as "structure the execution first, then attach facts to it."

## How To Read This Example

### 1. Context comes first

The example creates `Project -> Run -> StageExecution` before any records because all later records and artifacts refer back to that context.

### 2. The envelope connects shared context

`MetricRecord` and `StructuredEventRecord` differ in content, but they refer to the same run and stage. `RecordEnvelope` is the connection point that carries that shared context.

### 3. Artifacts attach as outputs

An artifact may look like an independent object, but in practice it is the output of the same run and stage.

If you combine those three perspectives, the basic assembly principle becomes clear:

- context objects are the skeleton everything else leans on,
- records are observed facts attached to that skeleton,
- artifacts are the durable outputs left behind by execution.

## What To Notice In The Example

- Build context models first, then reuse them.
- Records connect execution context through the envelope.
- Artifacts should be attached to run and stage so later lineage analysis becomes easier.
- Validating immediately at each step is the safest pattern.

## How Real Code Usually Splits Responsibilities

In production code, this example usually does not live inside one function exactly like this. Instead, the responsibilities are often split roughly like:

- `Project` and `Run` during run bootstrap,
- `StageExecution` at stage entry,
- event, metric, and trace emission at step or request level,
- artifact and lineage creation near completion.

So the best way to read the example is not "everything gets built in one place," but "Spine objects get assembled gradually across the lifecycle of an execution."

In many systems, the code is spread across roles like:

- a scheduler or runner starts the `Run`,
- a stage executor creates `StageExecution`,
- a trainer or service handler emits records,
- an artifact writer registers outputs.

So this example is really a compressed summary that puts those distributed responsibilities on one screen.

## Common Assembly Order In Practice

When you integrate Spine into real producer code, the following order is usually the natural one:

1. confirm or create `Project` and `Run` at run start,
2. create `StageExecution` at stage start,
3. create `OperationContext` if step or request level tracking is needed,
4. emit event, metric, and trace records,
5. create artifacts,
6. attach lineage if needed.

So the natural usage pattern of Spine is "structure the execution first, then attach observations to it."

## How The Flow Changes By Scenario

### 1. Training pipeline

This is the scenario the current example most closely represents.

- `Project`
- `Run`
- `StageExecution(train)`
- epoch or step events,
- loss or throughput metrics,
- checkpoint artifact.

Here the core concern is repeated execution plus output tracking.

### 2. Evaluation pipeline

In evaluation, the following structure is usually natural:

- confirm the existing model artifact or run context,
- create `StageExecution(evaluate)`,
- emit evaluation start and completion events,
- emit metrics like accuracy, f1, and latency,
- create a report artifact.

So the structure is similar to training, but the output kinds and metric interpretation differ.

### 3. Online inference flow

In inference, object lifetimes are usually shorter and request-level context matters more.

- long-lived run or service-run context,
- request or step level `OperationContext`,
- request event, latency metric, trace span,
- optional report or drift-signal artifact.

In this case, operation context and correlation fields often matter more than stage.

So even though the same Spine model is used, the emphasis changes by scenario.

## Second Short Example: Request-Centered Inference Flow

Compared against the training example, online inference usually makes operation context and short time intervals more important.

```python
from spine import (
    MetricPayload,
    MetricRecord,
    OperationContext,
    RecordEnvelope,
    Run,
    StableRef,
    TraceSpanPayload,
    TraceSpanRecord,
    validate_metric_record,
    validate_operation_context,
    validate_run,
    validate_trace_span_record,
)

run = Run(
    run_ref=StableRef("run", "serving-20260330"),
    project_ref=StableRef("project", "nova"),
    name="online-inference",
    status="running",
    started_at="2026-03-30T09:00:00Z",
)
validate_run(run).raise_for_errors()

op = OperationContext(
    operation_context_ref=StableRef("op", "request-0001"),
    run_ref=run.run_ref,
    stage_execution_ref=None,
    operation_name="predict",
    observed_at="2026-03-30T09:10:00Z",
)
validate_operation_context(op).raise_for_errors()

trace = TraceSpanRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "trace-request-0001"),
        record_type="trace_span",
        recorded_at="2026-03-30T09:10:01Z",
        observed_at="2026-03-30T09:10:01Z",
        producer_ref="gateway.inference.local",
        run_ref=run.run_ref,
        stage_execution_ref=None,
        operation_context_ref=op.operation_context_ref,
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
validate_trace_span_record(trace).raise_for_errors()

latency = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-request-0001-latency"),
        record_type="metric",
        recorded_at="2026-03-30T09:10:01Z",
        observed_at="2026-03-30T09:10:01Z",
        producer_ref="gateway.inference.local",
        run_ref=run.run_ref,
        stage_execution_ref=None,
        operation_context_ref=op.operation_context_ref,
    ),
    payload=MetricPayload(
        metric_key="inference.latency",
        value=152,
        value_type="integer",
        unit="ms",
    ),
)
validate_metric_record(latency).raise_for_errors()
```

This second example highlights three things:

- place request-level operation contexts under one longer-lived service run,
- connect traces and metrics from the same request through the same `operation_context_ref`,
- even without a stage, Spine assembly still feels natural.

So Spine is not a model designed only for training pipelines. The same principles apply naturally to request-centered systems too.

## What The Example Intentionally Leaves Out

This page focuses on explaining assembly order, so some elements are intentionally simplified or omitted:

- `OperationContext` in the basic example,
- `TraceSpanRecord`,
- `LineageEdge` and `ProvenanceRecord`,
- extension attachment,
- compatibility reader paths.

That does not mean those pieces are unimportant. It simply keeps the entry barrier lower by showing the core flow first.

Put differently, when you introduce Spine into a real system, it also matters in which order you introduce these omitted parts.

Usually the most natural sequence is:

1. start with context plus core metric and event flow,
2. attach artifacts,
3. add operation context and traces when needed,
4. finally add advanced paths such as lineage, extensions, and compatibility.

So Spine adoption itself usually deepens in stages rather than arriving complete in one shot.

## Good Producer Code Patterns

When putting Spine into actual producer code, the following patterns are usually stable.

### Reuse context through small helpers

Because `run_ref`, `stage_execution_ref`, and `producer_ref` appear repeatedly, helper functions for creating envelopes or artifacts make the code much cleaner.

### Validate immediately where the object is created

If you do not delay failure, it becomes much easier to see exactly where the contract broke.

### Serialize only at external boundaries

It is usually safest to keep Spine objects internally and apply `to_payload()` or `to_json()` only right before storage or transmission.

### Split producer responsibilities, but reuse refs consistently

Even when multiple modules emit records together, they should reuse the same `run_ref`, `stage_execution_ref`, and `operation_context_ref` values. One of the most common failures in Spine assembly is "many objects exist, but their context no longer connects."

## The Core Intuition To Keep From This Page

In very short form:

- Spine assembly is usually read in the order `Project -> Run -> Stage -> Record/Artifact`,
- create context first, then attach records and artifacts to that context,
- validation is safest when done immediately at each step,
- in real systems the same flow is varied slightly for training, evaluation, and inference scenarios.

## What To Read Next

If this example made sense, the next useful pages are:

- if you want deeper type semantics: [Context Models](./context-models.md), [Observability Records](./observability-records.md), [Artifacts And Lineage](./artifacts-and-lineage.md),
- if you want the payload conversion flow: [Serialization And Schema](./serialization-and-schema.md),
- if you want legacy input handling: [Compatibility And Migrations](./compatibility-and-migrations.md).
