# Observability Records

[User Guide Home](./README.md)

In Spine, the objects you create most often are usually event, metric, and trace records. This page explains how to distinguish those three types and how they all sit on the same shared structure.

The two core ideas of this page are:

1. every record has a `RecordEnvelope + Payload` shape,
2. event, metric, and trace hold different content but are interpreted on top of the same context model.

After reading this page, you should be able to decide all of the following right away:

- when to use event, metric, and trace,
- how the envelope and payload divide responsibilities,
- how records connect inside the same run, stage, or operation,
- what goes wrong when observability records are modeled poorly.

## Why Observability Records Are Their Own Layer

Context models explain "where and in what execution something happened." Observability records explain "what was observed during that execution."

So:

- context: the background
- records: the observed facts

Separating the two makes the following much easier:

- viewing events and metrics from the same run together,
- comparing traces and metrics from the same stage,
- adding record types while reusing shared metadata,
- applying shared rules in the ingestion layer.

Through this split, Spine models "what data exists" separately from "where that data belongs."

## Why Not Merge Records Into One Loose Object

At first, it can be tempting to put everything into one loose record type like this:

```json
{
  "type": "metric",
  "name": "training.loss",
  "value": 0.4821,
  "run": "train-20260330-01",
  "timestamp": "2026-03-30T09:08:30Z"
}
```

But problems appear quickly over time.

- events do not have `value`
- traces need `started_at` and `ended_at`
- the number of shared field names keeps growing
- fields with the same meaning start to drift by type

To avoid that confusion, Spine moves the shared part into the envelope and keeps type-specific meaning in the payload.

## The Shared Shape: RecordEnvelope + Payload

All Spine records follow this structure:

```text
RecordEnvelope
  + Payload
```

The point of this structure is to separate metadata from the actual observation.

- envelope: when, where, and by whom was it recorded
- payload: what was actually observed

This is not just coding style. It is one of the key design choices that keeps observability data consistent and extensible.

## RecordEnvelope

This is the metadata structure shared by every record.

Major fields:

- `record_ref`
- `record_type`
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

## What The Envelope Does

The envelope holds the facts around the payload.

- which producer created it,
- which execution it belongs to,
- which stage or operation it belongs to,
- how actual observation time differs from record time,
- what the data quality state is.

So the envelope is the context metadata that tells you how to read the payload.

Even when the payload is identical, interpretation can change drastically if the envelope changes.

Example:

- the same `training.loss=0.48` means very different things depending on whether it is
  - from run A or run B,
  - from the train stage or the evaluate stage,
  - a step-level value or an epoch aggregate.

## `record_ref` And `record_type`

### `record_ref`

This is the identifier for each record. In practice, it usually uses a form like `StableRef("record", "...")`.

Examples:

- `record:event-epoch-1-start`
- `record:metric-step-42`
- `record:trace-forward-001`

### `record_type`

This tells consumers how the payload should be interpreted.

Current major values:

- `structured_event`
- `metric`
- `trace_span`

Spine validation checks that the record object type and the envelope's `record_type` agree.

Example:

- `MetricRecord` with `record_type="structured_event"` fails validation

## `recorded_at` vs `observed_at`

Core distinction:

- `observed_at`: when the phenomenon actually happened
- `recorded_at`: when the phenomenon was recorded in the system

Current validation expects `recorded_at >= observed_at`.

Common cases where they differ:

- asynchronous batch collection,
- buffer flush,
- recording after retry,
- sidecar exporters,
- late upload by a collector.

Separating these two fields makes the following possible:

- measuring ingestion delay,
- separating real event time from storage time,
- correctly reordering late-arriving data.

So these are not just similar timestamps. They represent different time semantics.

## `producer_ref`

`producer_ref` identifies which system, library, or agent created the record.

Examples:

- `scribe.python.local`
- `sdk.python.local`
- `collector.inference.gateway`

This field is more important than it may first appear. Even for the same record type, meaning and quality may differ by producer.

Example:

- one producer may emit step-level metrics,
- another may emit only epoch aggregates.

## `run_ref`, `stage_execution_ref`, `operation_context_ref`

These three fields decide which execution context a record belongs to.

- `run_ref`: which run
- `stage_execution_ref`: which stage
- `operation_context_ref`: which detailed unit of work

Those links make analyses like these easy:

- query all metrics from the same run,
- collect only error events from the train stage,
- inspect traces and metrics together for `op:step-42`.

If these fields are left empty, the record still exists, but its operational value drops sharply.

## CorrelationRefs

These are auxiliary fields for connecting Spine records to external tracing systems.

They contain:

- `trace_id`
- `session_id`

For example, they are useful when you want to match request-level inference traces against an external tracing system.

With these fields, you can connect internal Spine records to external tracing ids.

They are especially useful for:

- connecting internal metrics to OpenTelemetry traces,
- grouping by API session,
- bundling events and metrics from the same user session.

In practice, it helps to think of envelope `run/stage/op` context as the structure that connects data inside Spine, while `correlation_refs` provides the bridge to observability systems outside Spine.

For example:

- use `run_ref` and `stage_execution_ref` to track which execution a record belongs to,
- use `correlation_refs.trace_id` to align with spans and traces in an external backend,
- use `correlation_refs.session_id` to regroup one end-user request flow.

So records can exist without `correlation_refs`, but in distributed systems this is often a very important axis for connecting Spine to external tools.

## completeness_marker

Allowed values:

- `complete`
- `partial`
- `unknown`

This expresses whether the data is complete, only partially collected, or in an unclear state.

Examples:

- a metric where only some fields were captured,
- an event where a downstream exporter omitted part of the payload,
- a span with trace continuity but missing some attributes.

Operationally, who sets this value depends on where the incompleteness is known:

- the producer can set it directly if it knows from the start that only partial capture happened,
- a collector or compatibility layer can set it if it detects loss during downstream processing.

The important point is that this does not mean "the payload is empty." It signals that interpretation should be done with care because completeness is limited.

## degradation_marker

Allowed values:

- `none`
- `partial_failure`
- `capture_gap`
- `compatibility_upgrade`

This shows whether there was any quality degradation during collection.

Examples:

- some attributes were lost because of an internal collector failure,
- trace continuity was partially broken,
- the payload was upgraded to the current schema through a compatibility reader.

These two markers let the model express a real-world condition: the value exists, but its quality may be imperfect.

From an operations perspective, it is better to use these as real filter conditions rather than treat them as decorative metadata.

Examples:

- collect only records with `degradation_marker != "none"` to monitor collection quality issues,
- exclude or separately label metrics with `completeness_marker == "partial"` in aggregates,
- if `compatibility_upgrade` appears frequently, investigate which legacy producers are still active.

## StructuredEventRecord

This type stores event-like logs in structured form.

Payload fields:

- `event_key`
- `level`
- `message`
- `subject_ref`
- `attributes`
- `origin_marker`

Allowed levels:

- `debug`
- `info`
- `warning`
- `error`
- `critical`

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
        attributes={"epoch": 1},
    ),
)
```

If you look at it in a fixture-like payload shape, it resembles this:

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": "session-train-01",
    "trace_id": "trace-train-01"
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-30T09:07:00Z",
  "operation_context_ref": null,
  "payload": {
    "attributes": {
      "epoch": 1
    },
    "event_key": "training.epoch.started",
    "level": "info",
    "message": "Epoch 1 started.",
    "origin_marker": "explicit_capture",
    "subject_ref": null
  },
  "producer_ref": "scribe.python.local",
  "record_ref": "record:event-epoch-1-start",
  "record_type": "structured_event",
  "recorded_at": "2026-03-30T09:07:00Z",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

### When Event Is The Right Fit

- state transition notifications,
- warning and error events,
- operationally meaningful messages humans may read,
- important facts worth recording as discrete occurrences.

Good examples:

- `training.epoch.started`
- `dataset.load.failed`
- `model.registration.completed`
- `drift.alert.triggered`

Less suitable examples:

- simple numeric measurements,
- time-interval information such as span duration.

### How To Use Event Payload Well

#### `event_key`

This is the machine-classifiable event name. It should be suitable for search, categorization, and aggregation.

#### `message`

This is the human-readable explanation.

#### `attributes`

This holds additional details attached to the event.

Example:

```python
attributes={"epoch": 1, "worker": "trainer-0"}
```

In practice, the strongest pattern is:

- `event_key` for structure,
- `message` for explanation,
- `attributes` for details.

#### `origin_marker`

This gives a hint about how the event was captured.

For example:

- was it emitted explicitly by application code,
- or derived from another log or system state.

Even for the same event, the capture path can change how trustworthy or how direct the event is, so origin metadata is surprisingly useful in operations analysis.

## MetricRecord

This type represents numeric observations.

Payload fields:

- `metric_key`
- `value`
- `value_type`
- `unit`
- `aggregation_scope`
- `subject_ref`
- `slice_ref`
- `tags`
- `summary_basis`

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
        aggregation_scope="step",
        tags={"device": "cuda:0"},
        summary_basis="raw_step_observation",
    ),
)
```

Fixture-based payload example:

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": null,
    "trace_id": "trace-train-01"
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-29T10:16:02Z",
  "operation_context_ref": "op:step-42",
  "payload": {
    "aggregation_scope": "step",
    "metric_key": "training.loss",
    "slice_ref": null,
    "subject_ref": null,
    "summary_basis": "raw_step_observation",
    "tags": {
      "device": "cuda:0"
    },
    "unit": "ratio",
    "value": 0.4821,
    "value_type": "scalar"
  },
  "producer_ref": "sdk.python.local",
  "record_ref": "record:metric-step-42",
  "record_type": "metric",
  "recorded_at": "2026-03-29T10:16:02Z",
  "run_ref": "run:run-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

### When Metric Is The Right Fit

- loss, accuracy, latency, throughput,
- resource usage,
- evaluation scores,
- drift score, calibration error, queue depth,
- success ratio, error count.

### How To Read The Fields Inside MetricPayload

#### `metric_key`

This is the name that describes the meaning of the metric.

Examples:

- `training.loss`
- `gpu.memory.used`
- `inference.latency.p95`

#### `value`

This is the actual numeric value.

#### `value_type`

This tells you how the value should be interpreted.

Current allowed values:

- `scalar`
- `integer`
- `float`

#### `unit`

This makes the measurement unit explicit.

Examples:

- `ratio`
- `ms`
- `bytes`

#### `aggregation_scope`

This shows the scope over which the value was calculated.

Examples:

- step
- batch
- epoch
- run

#### `tags`

These are additional classification fields.

Example:

```python
tags={"device": "cuda:0", "split": "validation"}
```

#### `summary_basis`

This describes how the value was produced.

Examples:

- raw step observation,
- batch mean,
- epoch aggregate.

So a metric is not just a number. It is a structured explanation of what kind of observed number it is.

## TraceSpanRecord

This type represents a time span.

Payload fields:

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

When it is appropriate:

- tracking model call latency,
- analyzing external API calls,
- finding bottlenecks by pipeline phase,
- analyzing request-level execution paths,
- representing flows where parent-child structure matters.

Validation checks `started_at <= ended_at`.

### When Trace Is The Right Fit

- when "how long did it take" is the main question,
- when parent-child call structure matters,
- when a time interval matters more than a single value.

Examples:

- `model.forward`
- `feature.lookup`
- `http.request`
- `vector.search`

### Key Fields In TraceSpanPayload

#### `span_id`

Identifier for the current span.

#### `trace_id`

Identifier for the whole trace.

#### `parent_span_id`

Connection to the parent span.

#### `started_at`, `ended_at`

These define the time interval.

#### `span_kind`

This describes the nature of the span.

Examples:

- model call,
- network call,
- internal stage.

#### `linked_refs`

These are additional reference links.

This structure carries much richer execution information than a single duration metric.

Example:

```python
from spine import RecordEnvelope, StableRef, TraceSpanPayload, TraceSpanRecord

trace = TraceSpanRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "trace-forward-001"),
        record_type="trace_span",
        recorded_at="2026-03-30T09:08:31Z",
        observed_at="2026-03-30T09:08:31Z",
        producer_ref="scribe.python.local",
        run_ref=StableRef("run", "train-20260330-01"),
        stage_execution_ref=StableRef("stage", "train"),
        operation_context_ref=StableRef("op", "step-42"),
    ),
    payload=TraceSpanPayload(
        span_id="span-forward-001",
        trace_id="trace-train-01",
        parent_span_id="span-step-42",
        span_name="model.forward",
        started_at="2026-03-30T09:08:30Z",
        ended_at="2026-03-30T09:08:31Z",
        status="ok",
        span_kind="model_call",
        attributes={"device": "cuda:0", "batch_size": 32},
        linked_refs=("artifact:checkpoint-epoch-1",),
    ),
)
```

The payload shape looks roughly like this:

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": null,
    "trace_id": "trace-train-01"
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-30T09:08:31Z",
  "operation_context_ref": "op:step-42",
  "payload": {
    "attributes": {
      "batch_size": 32,
      "device": "cuda:0"
    },
    "ended_at": "2026-03-30T09:08:31Z",
    "linked_refs": [
      "artifact:checkpoint-epoch-1"
    ],
    "parent_span_id": "span-step-42",
    "span_id": "span-forward-001",
    "span_kind": "model_call",
    "span_name": "model.forward",
    "started_at": "2026-03-30T09:08:30Z",
    "status": "ok",
    "trace_id": "trace-train-01"
  },
  "producer_ref": "scribe.python.local",
  "record_ref": "record:trace-forward-001",
  "record_type": "trace_span",
  "recorded_at": "2026-03-30T09:08:31Z",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

When reading traces, it is usually better to inspect more than just one duration number:

- under which parent span did this execute,
- which operation context does it connect to,
- what are the span status and linked refs.

That is what makes bottleneck analysis, failure propagation analysis, and request-path reconstruction much easier.

## Event, Metric, And Trace Are Not Competing Types

In practice, it is common to use all three together rather than pick just one. Even for the same execution, event, metric, and trace answer different questions.

For example, inside one training step, these three records can all be meaningful at once:

- the fact that an epoch started is an event,
- the loss at that point is a metric,
- the duration of `model.forward` is a trace span.

So these are not substitutes. They complement one another. Keeping all three perspectives is the natural way to describe one execution more completely.

Put differently:

- event says "what happened,"
- metric says "what was the value,"
- trace says "how long did it take, and in what execution flow."

## Which Record Type Should You Use And When

The best criterion for choosing a record type is "how will I want to read this data later." It is much better to choose based on future questions than based only on what is easiest to emit right now.

### A Quick One-Sentence Rule

As a very short guide:

- if "what happened" matters most, use event,
- if "what was the value" matters most, use metric,
- if "how long did it take and what was the execution flow" matters most, use trace.

That is only the first rule of thumb. In real systems, all three are often used together.

## Example Combinations Of Observability Records

Using the same training loop as an example, the three records below serve different purposes.

### Example 1. Epoch start

```text
training.epoch.started
```

This is a state transition, so event is the right fit.

### Example 2. Step loss

```text
training.loss = 0.4821
```

This is meant for numerical comparison and time-series analysis, so metric is the right fit.

### Example 3. Forward pass duration

```text
model.forward started_at=... ended_at=...
```

This is about a time interval and execution path, so a trace span is the right fit.

So even inside a single execution, the record type changes depending on the nature of what is being observed.

## Common Mistakes In Observability Record Modeling

This section is especially important. Most operational data breaks not because it cannot be stored, but because it becomes hard to read correctly later.

### 1. Sending everything as metrics

This is one of the most common mistakes. If you force even state transitions into numeric form, the result looks simple but the meaning becomes much weaker.

For example:

```text
training.epoch.started=1
```

This looks like a number, but semantically it is much closer to an event. Modeling it as a metric creates problems like:

- event search becomes harder,
- human-readable meaning becomes blurry,
- bad aggregates become easier to create.

### 2. Hiding core numeric observations inside events

The reverse mistake is also common: putting important numeric observations only inside human-readable messages.

For example:

```text
"training loss is 0.4821"
```

This is easy to read by eye, but it is poor for later averaging, charting, or threshold-based filtering. Data like this should usually be modeled as metrics.

### 3. Replacing trace spans with a start event and an end event

Leaving only "start" and "end" events may look sufficient for rough duration calculation, but you lose much of the structure trace spans are meant to preserve.

In particular, you weaken:

- parent-child relationships,
- nested span structure,
- linked spans,
- trace-level grouping.

If the time interval itself matters, trace spans are a much better fit.

### 4. Leaving envelope context empty

If run, stage, or operation links are missing, the record may still exist, but its operational meaning drops sharply.

Even with a single metric, interpretation gets much harder if you do not know:

- which run,
- which stage,
- which operation context.

Even if it feels tedious early on, it is usually worth filling at least `run_ref` whenever possible.

### 5. Mismatching `record_type` And Payload Meaning

If the object type and the envelope's `record_type` disagree, validation fails. This is not just a syntactic problem; it is a structural error that prevents the system from knowing how to read the record.

Example:

- `MetricRecord` with `record_type="structured_event"`

In that case, a consumer cannot consistently decide whether the payload should be interpreted as a metric or as an event.

### 6. Ignoring `producer_ref`

Even for the same metric, different producers may imply different meaning or quality. Producer information is extremely useful later when debugging data quality problems.

For example:

- one producer emits raw step metrics,
- another emits only epoch aggregates,
- another may omit some fields.

If those differences are not preserved, the same metric key can silently mix data with different meaning.

## Practical Guide For Better Record Design

When designing records, it helps to ask these questions first.

### Will this data be aggregated later

If yes, metric is usually the better fit.

### Is it important that humans read it as a message

If yes, event is usually the better fit.

### Are call structure and time intervals important

If yes, trace spans are usually the better fit.

### Is it important to know which execution context this belongs to

Almost always yes, which is why it is usually worth filling at least `run_ref`.

### Does it need to connect to an external trace or session system

If yes, it is worth using `correlation_refs` actively.

## Why Observability Records Matter For Later Analysis

When the record structure is solid, questions like these become natural:

- collect all error events for a specific run,
- aggregate only latency metrics from the train stage,
- inspect traces and metrics for a specific request together,
- extract only records with `degradation_marker != none`,
- bundle events, metrics, and spans that share the same `trace_id`.

So record structure is not just a storage format. It is the basic unit for operations analysis.

## After Reading This Page

Observability records always need to be read with context, and they often connect to artifacts and lineage as well.

- higher-level execution context: [Context Models](./context-models.md)
- artifacts and relations: [Artifacts And Lineage](./artifacts-and-lineage.md)

The natural next page is [Artifacts And Lineage](./artifacts-and-lineage.md), which completes the other half of Spine.
