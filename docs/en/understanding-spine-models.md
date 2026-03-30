# Understanding Spine Models

[User Guide Home](./README.md)

When people first see Spine, the first reaction is often, "Why are there so many separate objects?" This page is the conceptual guide that answers that question.

If `Getting Started` is the page where you build your first objects by hand, this page is the one that helps you decide which object to use and when.

The goals of this document are:

1. organize Spine's model layers into one mental picture,
2. explain why seemingly similar objects are intentionally separated,
3. give you criteria for deciding how far to model a real system,
4. help you avoid common modeling mistakes before they happen.

After reading this page, you should be able to understand Spine's design direction clearly even without memorizing every field on every type.

## The Core Question For Understanding Spine

The most important question in Spine is not "what logs do we emit," but "which entities and relationships do we fix as part of the contract."

Many observability systems stop at something like:

- one JSON log line,
- a metric name and value,
- one trace span.

For ML systems, that is usually not enough. Sooner or later, the following questions always show up:

- which run did this metric come from,
- which stage produced this artifact,
- was this relationship explicitly declared or inferred,
- is this payload in the current schema or an older one,
- is this record complete or only partially collected,
- which project or model family does this execution belong to,
- did environment differences change the outcome,
- how much of this should count as "the same execution."

Spine is a library that splits the model structure ahead of time so those questions stay answerable.

## Looking More Concretely At The Problem Spine Solves

Without Spine, teams usually fall into one of the following patterns.

### 1. Everything gets pushed into log strings

Example:

```text
2026-03-30T09:08:30Z training.loss=0.4821 run=train-20260330-01 stage=train step=42
```

Humans can read this easily, but without a contract it becomes hard to do all of the following:

- detect missing fields,
- validate types,
- handle backward compatibility,
- represent lineage and provenance.

### 2. Everything is kept in loose JSON dicts

Example:

```json
{
  "type": "metric",
  "name": "training.loss",
  "value": 0.4821,
  "run": "train-20260330-01"
}
```

This looks flexible at first, but over time the same meaning gets expressed through many field names.

Examples:

- `run`, `run_id`, `runRef`, `run_ref`
- `eventTime`, `observed_at`, `timestamp`
- `artifactPath`, `location`, `uri`

### 3. Tracing, metrics, and artifacts are modeled as completely separate worlds

In that case, each system works on its own, but the links between them stay weak.

For example:

- the metric only knows a run id,
- the artifact only knows a file path,
- the trace only knows a span id.

Then it becomes hard to answer questions like, "which artifact was created around the time this trace span happened, and what did the metrics look like at that point?"

Spine reduces this fragmentation by providing shared context and a shared contract.

## How Spine Splits The Model

Spine's models can be understood as five large layers:

- context layer: `Project`, `Run`, `StageExecution`, `OperationContext`, `EnvironmentSnapshot`
- observability layer: `StructuredEventRecord`, `MetricRecord`, `TraceSpanRecord`
- output layer: `ArtifactManifest`
- relationship layer: `LineageEdge`, `ProvenanceRecord`
- shared infrastructure layer: `StableRef`, `ExtensionFieldSet`, `schema_version`, validation, serialization

You can summarize the structure like this:

```text
which system
  -> had which execution
    -> inside which stages and operations
      -> produced which observations and outputs
        -> with which relationships between them
```

In that sense, Spine is closer to "a model for structuring observable ML executions" than just "a format for storing observability data."

## Spine's Object Graph

The most basic Spine object graph looks like this:

```text
Project
  -> Run
    -> StageExecution
      -> OperationContext
        -> RecordEnvelope + Payload
    -> EnvironmentSnapshot
    -> ArtifactManifest
    -> LineageEdge / ProvenanceRecord
```

This graph carries several important messages.

### 1. Records do not stand alone

You can store a metric by itself, but Spine always treats "where did this metric come from" as important.

That is why records usually connect to:

- `run_ref`
- `stage_execution_ref`
- `operation_context_ref`

Once those links exist, you can ask questions like:

- show only metrics from the train stage,
- show only events from step 42,
- show only trace spans that belong to a specific run,
- collect error events by stage inside the same run,
- find artifacts produced by a specific operation context.

### 2. Artifacts also connect to execution context

An artifact is not just a file. It is an output of an execution. That is why `ArtifactManifest` is not just file metadata; it is an object connected to a run or stage.

In Spine, it is better to think about an artifact like this:

```text
checkpoint file
  -> created inside a run
  -> created inside a specific stage
  -> created by a specific producer
```

Without those connections, the artifact remains just "a file somewhere." In ML operations, that is rarely enough.

- which experiment produced this checkpoint,
- which training stage created it,
- which producer exported it,
- what are its hash and size.

### 3. Relations are a separate layer

Having artifacts, records, and runs does not automatically explain the relationships between them. "What came from what" is a separate modeled meaning.

That is why Spine has `LineageEdge` and `ProvenanceRecord` as their own layer.

This design lets Spine express not only simple event storage, but also lineage and provenance.

Even for the same artifact, the following are completely different claims:

- `generated_from` a dataset,
- `produced_by` a stage,
- `deployed_from` a deployment artifact.

Spine's direction is to keep those as structured models instead of burying them inside free-form memo strings.

## Why Context, Observation, Outputs, And Relations Are Separate

To understand Spine well, it helps to ask why these need to be different classes at all.

### Context

Context is the execution background surrounding an observation.

Example questions:

- which project's execution is this,
- which stage is this,
- which operation is this.

### Observation

Observation is the data that was actually measured or recorded.

Example questions:

- what metric is this,
- what event happened,
- which span ran for how long.

### Output

Outputs are the durable results produced during execution.

Example questions:

- which file, model, or report was created,
- where was it stored,
- what are its hash and size.

### Relation

Relations are the semantic connections between entities.

Example questions:

- which artifact was derived from which dataset,
- which result was reported by which execution,
- was the claim explicit or inferred.

All four are important, but once they are mixed into one object, the model boundary collapses quickly. Spine separates them to prevent that.

## Why `Project -> Run -> StageExecution -> OperationContext`

This structure exists so you do not lose either the large-scale context or the fine-grained work unit.

### Project

`Project` is a long-lived logical unit.

Examples:

- one model family,
- one product capability,
- one experiment track,
- one service family.

`Project` usually persists for a long time. Many runs can accumulate over days, weeks, or months.

### Run

`Run` is one real execution.

Examples:

- one training job,
- one batch evaluation,
- one day's offline inference.

The important point is that `Run` is an execution unit. If Project is the long-lived static anchor, Run is the dynamic anchor with a time axis.

### StageExecution

`StageExecution` is a major phase inside a run.

Examples:

- `extract`
- `prepare`
- `train`
- `evaluate`
- `deploy`

Not every system needs stages, but once a run contains meaningful large phases, operations and debugging become much easier.

Examples:

- "Did the failure happen in train or evaluate?"
- "Was this artifact created in the train stage?"
- "Was this metric produced before or after deploy?"

### OperationContext

`OperationContext` is a finer-grained unit of work inside a stage.

Examples:

- `epoch-1`
- `step-42`
- `batch-000123`
- `request-abc123`

This level matters especially when you deal with dense metrics or traces.

Examples:

- at which step did loss spike sharply,
- in which batch was latency abnormal,
- in which request did the error span occur.

All four layers exist for the same reason:

- if you model too coarsely, detailed tracking disappears,
- if you model too finely, the big picture disappears,
- operations and analysis need both.

## What Spine Uses To Decide Model Levels

Spine's context layer is effectively a way of splitting scope.

- `Project`: long-lived logical scope
- `Run`: one execution scope
- `StageExecution`: phase scope inside an execution
- `OperationContext`: fine-grained operation scope inside a phase

Seen this way, the design is fairly natural. To interpret observability data, you must know which scope it belongs to.

## Why Records Are Split Into Envelope And Payload

This is one of Spine's most important design decisions.

Metric, event, and trace records hold different data, but they share the same metadata:

- `record_ref`
- `record_type`
- `recorded_at`
- `observed_at`
- `producer_ref`
- `run_ref`
- `stage_execution_ref`
- `operation_context_ref`

The actual payload is different:

- event: `event_key`, `message`, `level`
- metric: `metric_key`, `value`, `unit`
- trace: `span_id`, `trace_id`, `started_at`, `ended_at`

Benefits of this split:

- reuse of shared validation logic,
- simpler ingestion pipelines,
- a common indexing strategy across records,
- reuse of envelope rules when new record types are added,
- the same context queries for every record type.

In other words, the envelope/payload split is not just an implementation preference. It is core to keeping the observability model extensible and consistent.

## What Envelope Means

The envelope holds the facts around the record.

Most importantly:

- who produced it (`producer_ref`)
- when it was recorded (`recorded_at`)
- when it was actually observed (`observed_at`)
- which run, stage, or operation it belongs to
- what its data quality state is (`completeness_marker`, `degradation_marker`)

So the envelope is the context needed to interpret the payload.

By contrast, the payload is the core data itself.

Examples:

- event payload: what happened,
- metric payload: what value was measured,
- trace payload: which span ran for how long.

## Why Keep Both `observed_at` And `recorded_at`

At first glance these can look redundant, but in real operations they diverge.

- `observed_at`: when the phenomenon actually happened
- `recorded_at`: when that phenomenon was written as a Spine record

Common cases where they differ:

- asynchronous buffer flush,
- network delay,
- batch collectors,
- sidecar exporters,
- retransmission after retry.

When both exist, you can do all of the following:

- track ingestion delay,
- analyze bottlenecks in the collection pipeline,
- interpret the gap between observation and recording,
- place late-arriving data on the correct time axis.

So the difference is not just metadata. It is part of the time semantics.

## Why `StableRef` Is Its Own Type

`StableRef` is not just a string wrapper. In Spine, identity is part of the contract.

These may look similar, but they mean different things:

```python
"project:nova"
StableRef("project", "nova")
```

Using `StableRef` gives you:

- a visible kind/value structure at the code level,
- earlier validation of malformed identity,
- one guaranteed serialized representation,
- clearer type meaning in code.

For example, if `run_ref` accidentally gets a `project` kind, the model layer can surface that problem much earlier.

The point is that ids are not left to a string convention alone; they are lifted into the model itself.

## Why Schema Version Lives In The Object

Spine does not treat payloads as temporary in-memory data that disappears immediately. It assumes payloads may be stored, transmitted, and read again later.

Without schema version, the following become unclear:

- which contract version produced this payload,
- whether the current reader can consume it directly,
- whether field remapping for an older schema is needed,
- whether a field name still means what it used to mean.

Schema version serves these roles:

- marking the contract version of the current payload,
- providing upgrade criteria for compatibility readers,
- making the validation target schema explicit,
- giving a basis for interpreting historical payloads.

So schema version is not auxiliary metadata. It tells you which contract should be used to read the object.

## Why Extensions Are A Separate Structure Instead Of Top-Level Fields

In real systems, data outside the standard schema always appears. The problem is that if every team adds arbitrary top-level fields, the contract collapses very quickly.

For example:

- team A uses `owner`
- team B uses `team_owner`
- team C uses `serviceOwner`

The meaning is similar, but the structure drifts.

To reduce that drift, Spine has `ExtensionFieldSet` and `ExtensionRegistry`.

- standard fields stay in the core schema,
- non-standard fields live under namespaced extensions,
- namespace ownership can be controlled through the registry.

Advantages of this approach:

- the standard vs non-standard boundary stays explicit,
- semantic collisions are easier to avoid,
- candidates for eventual promotion into the standard schema are easier to manage,
- each team can add needed metadata without breaking the shared contract.

## Modeling Principles Spine Tries To Enforce

These are the principles worth remembering while you use the library.

### 1. Do not rely only on payload names for semantics

Instead of putting all meaning into a `metric_key` string, Spine distributes semantics across run, stage, operation, record, artifact, and relation structure.

### 2. Preserve execution context explicitly

For observability data, the value by itself matters less than "which execution produced this value." Spine forces that context into the model.

### 3. Treat relationships as first-class objects

"A came from B" is not incidental commentary. It has its own meaning, so Spine models lineage as separate entities.

### 4. Upgrade legacy payloads explicitly

Legacy inputs are not accepted silently. They move through an explicit migration path using compatibility readers.

### 5. Prefer structures that can be validated

Very loose models feel convenient early on, but they make validation and operations harder later. Spine intentionally chooses a more structured model.

## Questions Spine Makes Possible

Whether a model is good is ultimately revealed by the questions it can answer. If you use the Spine structure well, questions like these become possible:

- list all runs in a specific project,
- show only train-stage metrics inside one run,
- inspect trace spans and metrics together for one operation context,
- find which run and stage produced a specific artifact,
- distinguish explicit lineage edges from inferred ones,
- track how often legacy payloads are being upgraded.

So Spine does more than normalize storage format. It enables later analysis and operational queries.

## How Far Should You Model

In practice, you do not need to create every object all the time. But you do need criteria for deciding how far to model.

### Minimal

- `Project`
- `Run`
- `MetricRecord` or `StructuredEventRecord`

This is enough for basic observability.

Good fit for:

- small experimental systems,
- teams starting with metric collection first,
- early-stage systems where lineage is not yet important.

### Operational

- `Project`
- `Run`
- `StageExecution`
- record models
- `ArtifactManifest`

At this level, most dashboards, operations, and incident analysis become possible.

Good fit for:

- systems with clearly separated training and evaluation pipelines,
- teams where artifact management matters,
- production environments that need stage-level observation.

### Lineage / Audit

- everything above
- `LineageEdge`
- `ProvenanceRecord`
- `EnvironmentSnapshot`

At this level, reproducibility, relationship tracking, and policy-aware analysis become possible.

Good fit for:

- environments where auditability matters,
- environments that need lineage visualization,
- environments that must explain which evidence produced which result.

## Modeling Decision Guide

These questions are a useful way to decide.

### Do you need `StageExecution`?

You usually do if any of the following are true:

- the run clearly contains distinct phases,
- you want to inspect metrics or artifacts by stage,
- you need to identify failure points at the stage level.

### Do you need `OperationContext`?

It is worth considering if any of the following are true:

- you need step, batch, or request level tracking,
- you need to distinguish many fine-grained units inside the same stage,
- you need to group traces or metrics at a denser unit.

### Do you need `LineageEdge`?

You do if you need to answer questions like:

- what was created from what,
- which result depends on which input, policy, or prior artifact,
- should the system, not just a human, be able to query those relationships.

## Common Modeling Mistakes

### 1. Packing everything into one metric

Once even state transitions that should be events get encoded as metrics, the meaning gets distorted.

Example:

- `training.epoch.started=1`

This looks numeric, but semantically it is much closer to an event.

### 2. Storing records without runs

This feels easy at first, but later it becomes almost impossible to analyze data by execution unit.

Examples:

- metrics exist, but you cannot tell which experiment they belong to,
- events exist, but you cannot tell which run produced the error.

### 3. Treating artifacts as file paths only

If you do that, run, stage, producer, hash, and other metadata get separated too easily.

In the end, the artifact becomes just "a file that cannot be explained."

### 4. Treating relations as note strings only

If lineage is not stored as its own model, later queries and visualization become much harder.

Example:

- leaving only a description such as `"derived from previous model"`

Humans can read this, but systems cannot reason over it well.

### 5. Treating all team metadata like core fields

If every team-specific field is promoted to the core schema, the same meaning eventually appears under different names. In those cases, an extension namespace is usually the better choice.

## The Best Way To Read This Page

Instead of trying to memorize everything in one pass, it helps to read this page through three questions:

- what does Spine treat as a first-class entity,
- why are those entities split apart,
- how far does my system need to model.

If you can answer those three, this page has done its job.

## What To Read After This Page

If this page explained "why the structure looks like this," the next pages explain "what each part of that structure looks like in practice."

- execution units and environment: [Context Models](./context-models.md)
- events, metrics, and traces: [Observability Records](./observability-records.md)
- artifacts and relations: [Artifacts And Lineage](./artifacts-and-lineage.md)

The most natural next page is usually [Context Models](./context-models.md).
