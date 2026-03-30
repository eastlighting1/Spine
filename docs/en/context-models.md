# Context Models

[User Guide Home](./README.md)

Once you start using Spine in practice, you usually need to decide "which execution did this value come from" before you even create a metric or event. This page explains the context models that represent that execution background.

Most observability data eventually points to context such as `Project`, `Run`, `StageExecution`, or `OperationContext`. Because of that, once you understand this layer first, the record and artifact pages become much easier to read.

The goals of this page are:

1. understand the role differences between `Project`, `Run`, `StageExecution`, `OperationContext`, and `EnvironmentSnapshot`,
2. decide how far context should be modeled in different systems,
3. understand how context models connect to later interpretation of records, artifacts, and lineage.

## What The Context Layer Does

Most other Spine objects express "what happened." The context layer expresses "where did it happen."

If you only look at a metric, you may know something like this:

- `training.loss = 0.4821`

In practice, you usually need much more:

- which project does this metric belong to,
- which run does it belong to,
- did it come from the train stage or the evaluate stage,
- is it step 42 or an epoch average,
- can it be compared together with environment differences.

All of those questions require background information rather than just the value itself. The context layer structures that background.

## Why It Helps To Understand Context First

Even without context models, you can still store one metric, one event, or one trace span. But in real systems, questions like these appear quickly:

- which experiment produced this value,
- can it be compared to another run in the same project,
- in which stage did the problem happen,
- is the issue at the step level or the run level,
- did environment differences change the result.

All of these ask for the background of the value, not just the value itself. Spine's context models are how that background is structured.

## The Full Context Picture

The most common connection shape looks like this:

```text
Project
  -> Run
    -> StageExecution
      -> OperationContext
    -> EnvironmentSnapshot
```

This is effectively a way of narrowing execution scope step by step.

- `Project`: long-lived and logical scope
- `Run`: one concrete execution scope
- `StageExecution`: a large phase scope inside an execution
- `OperationContext`: a finer work-unit scope inside a phase
- `EnvironmentSnapshot`: the environment scope surrounding that execution

Seen from this angle, context models are not just a list of types. They are a scope hierarchy.

## Project

`Project` is the highest logical unit. In practice it usually represents a model family, service family, experiment track, or ML product line.

Major fields:

- `project_ref`: canonical project reference
- `name`: human-readable name
- `created_at`: project-level creation time
- `description`: description
- `tags`: lightweight metadata
- `schema_version`
- `extensions`

Example:

```python
from spine import Project, StableRef

project = Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00Z",
    description="Image classification project.",
    tags={"team": "research", "track": "vision"},
)
```

Serialized payload example:

```json
{
  "created_at": "2026-03-29T10:15:21Z",
  "description": "Image classification project.",
  "name": "NovaVision",
  "project_ref": "project:nova",
  "schema_version": "1.0.0",
  "tags": {
    "team": "research",
    "track": "vision"
  }
}
```

### How To Think About Project

If you define `Project` too narrowly, runs get scattered unnecessarily. If you define it too broadly, executions with very different meaning get mixed together.

These criteria are usually a good guide:

- is this the same product or model family,
- are these runs something you want to compare as one logical group,
- can they share common tags and description.

Good examples:

- `NovaVision`
- `fraud-detection`
- `ranking-v2`

Less useful examples:

- `train-20260330-01`
- `epoch-1`

Names like those usually belong more naturally to `Run` or `OperationContext`.

### Questions Project Answers

- which product or experiment track does this run belong to,
- do I want to inspect runs together at the project level,
- where should team- or domain-level metadata live.

### What Project Validation Usually Checks

The current validation logic mostly checks the following:

- `project_ref.kind == "project"`
- `name` is not blank
- `created_at` follows normalized UTC `Z` format
- `schema_version` matches the current schema

Practical tips:

- `Project` should be a long-lived identifier.
- Put batch execution names in `Run`, and product or experiment family names in `Project`.
- It is usually best to keep only the tags you will really search or group by.

## Run

`Run` is one real execution. It can represent a training job, evaluation job, batch inference execution, or data generation pipeline run.

Major fields:

- `run_ref`
- `project_ref`
- `name`
- `status`
- `started_at`
- `ended_at`
- `description`
- `schema_version`
- `extensions`

Allowed statuses:

- `created`
- `running`
- `completed`
- `failed`
- `cancelled`

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

### Why Run Matters

In Spine, `Run` is effectively the most frequently referenced context object.

Most records and artifacts eventually belong to a run.

Examples:

- which run does this metric belong to,
- in which run did this event happen,
- which run produced this artifact,
- which run does this environment snapshot describe.

That is why a run is the basic unit on the execution time axis.

### The Difference Between Run Name And Run Ref

In practice, it is best to separate these two:

- `run_ref`: a stable system identifier
- `name`: a human-readable execution name

Example:

- `run_ref = run:train-20260330-01`
- `name = baseline-resnet50`

This gives you both stable internal identity and user-friendly readability.

### What To Think About When Designing A Run

- should a retried job be treated as the same run or a different run,
- should one day of batch inference be grouped as one run,
- should evaluation runs and training runs be separate.

These decisions directly affect operational queries and lineage interpretation.

### Questions Run Answers

- did this execution succeed or fail,
- when did it start and end,
- which project does it belong to,
- which records and artifacts belong to the same execution.

### What Run Validation Usually Checks

- `run_ref.kind == "run"`
- `project_ref.kind == "project"`
- `status` is inside the allowed set
- `started_at` is valid
- if `ended_at` exists, the time order is correct

Practical tips:

- It is usually worth making the run name immediately understandable to humans.
- Keep `run_ref` as the system identifier and `name` as the user-facing label.
- In many operational screens, run is the first thing people search for.

## StageExecution

`StageExecution` is the structure that splits one run into larger phases.

Common examples:

- `extract`
- `prepare`
- `train`
- `evaluate`
- `deploy`

Major fields:

- `stage_execution_ref`
- `run_ref`
- `stage_name`
- `status`
- `started_at`
- `ended_at`
- `order_index`
- `schema_version`
- `extensions`

### Does Every System Need StageExecution

Not always. But it helps a lot if any of the following are true:

- the run clearly has internal phases,
- you want to inspect metrics by stage,
- you want to separate failure causes by stage,
- you want to trace artifact creation at the phase level.

For example, if a training pipeline looks like this, stage separation is natural:

```text
prepare -> train -> evaluate -> register
```

### Questions StageExecution Answers

- in which phase did the failure happen,
- is this artifact the output of train or evaluate,
- what are the stage-level latency and success rates,
- what is the time order between stages.

### Relationship Between `stage_name` And `stage_execution_ref`

In practice, it is best to give them different jobs:

- `stage_name`: the human-readable phase name
- `stage_execution_ref`: the stable reference you can link to

The same stage name may appear across many runs, so separating name and ref keeps the model more stable.

### What StageExecution Validation Usually Checks

- `stage_execution_ref.kind == "stage"`
- `run_ref.kind == "run"`
- `stage_name` is not blank
- `status` is valid
- the time order is correct

This becomes especially useful when:

- you want to separate metrics by phase inside one run,
- you want to track which stage produced an artifact,
- you want stage-level SLA, failure-rate, or latency reporting.

## OperationContext

`OperationContext` is a finer-grained unit of work inside a stage.

Common examples:

- `epoch-1`
- `step-42`
- `batch-000123`
- `feature-join`
- `request-abc123`

Major fields:

- `operation_context_ref`
- `run_ref`
- `stage_execution_ref`
- `operation_name`
- `observed_at`
- `schema_version`
- `extensions`

### When To Introduce OperationContext

Not every system needs it from the beginning. But it becomes valuable when:

- metrics or traces are emitted heavily at the step, batch, or request level,
- you want to separate finer work units inside the same stage,
- you need to know which detailed unit produced a particular error or delay.

Examples:

- tracking training loss per step,
- tracking inference latency per request,
- tracking error events per feature-join operation.

### Questions OperationContext Answers

- at which step did this metric happen,
- which request does this trace span belong to,
- during which detailed operation did this event occur.

### What Goes Wrong When You Overuse OperationContext

If every internal function call becomes an operation, the model can become too noisy.

A good standard is:

- is this worth separating operationally,
- is it worth connecting metrics, traces, and events at this unit,
- are you likely to search or aggregate by this unit later.

This model becomes especially powerful when used with records. For example, if a `MetricRecord` points its `operation_context_ref` to `op:step-42`, you know exactly which work unit produced that metric.

## EnvironmentSnapshot

`EnvironmentSnapshot` is the model for preserving the execution environment itself.

Major fields:

- `environment_snapshot_ref`
- `run_ref`
- `captured_at`
- `python_version`
- `platform`
- `packages`
- `environment_variables`
- `schema_version`
- `extensions`

### Why Environment Is A Separate Model

You may not inspect environment information as often as metrics or artifacts. But when incidents or reproducibility issues appear, it quickly becomes one of the most valuable pieces of data.

Examples:

- a package version difference changed the result,
- a Python version difference changed serialization behavior,
- an environment variable difference changed input resolution.

So environment data is quiet most of the time, but extremely valuable when something goes wrong.

### Questions EnvironmentSnapshot Answers

- which Python version did this run use,
- which packages were installed,
- were there environment variable differences,
- what changed between two runs' environments.

### When You Really Should Capture EnvironmentSnapshot

It is strongly recommended when:

- reproducibility matters in training systems,
- deployment or inference systems frequently suffer from environment drift,
- auditability matters.

Why this model matters:

- reproducibility analysis,
- tracing failures caused by environment differences,
- checking package-version drift.

## How To Combine Context Models

In practice, not every level is always needed.

### Minimal combination

- `Project`
- `Run`

This is enough to build a basic structure that groups metrics and artifacts by run.

### Operational combination

- `Project`
- `Run`
- `StageExecution`

This is enough for most stage-level operational analysis.

### Fine-grained tracking combination

- `Project`
- `Run`
- `StageExecution`
- `OperationContext`

This structure supports step- or request-level tracking.

### Reproducibility combination

- the structure above
- `EnvironmentSnapshot`

This lets you answer "which execution ran in which environment."

## Modeling Decision Tree

If you want a simple decision process, the following sequence helps.

### 1. Do you want to group multiple executions under one logical identity

If yes, you need `Project`.

### 2. Do you need a distinct execution unit with a time axis

In most cases, you need `Run`.

### 3. Are there meaningful phases inside the execution

If yes, it is usually worth introducing `StageExecution`.

### 4. Do you need step, batch, or request granularity

If yes, consider `OperationContext`.

### 5. Can environment differences affect outcomes

If yes, it is usually worth keeping `EnvironmentSnapshot`.

## Common Context Modeling Mistakes

### 1. Using Project And Run as if they meant the same thing

Example:

- putting dates and execution numbers directly into the project name

That mixes a long-lived group with a short-lived execution.

### 2. Stuffing everything into one Run without StageExecution

This feels simple at first, but later it becomes hard to inspect prepare, train, and evaluate separately.

### 3. Overusing OperationContext at unnecessary granularity

If every internal function call becomes an operation, the model gets too noisy. Operation should usually exist only for units that are operationally worth separating.

### 4. Never capturing EnvironmentSnapshot

Things still work without it at first, but the moment reproducibility issues appear, it often becomes the most regretted missing data.

### 5. Mixing up readable names and stable identifiers

If `name` and `*_ref` are treated as the same thing, user-facing labels and system identity eventually get mixed together.

## How Context Affects The Rest Of The Docs

Context models become the interpretation baseline for every other model.

- Records point into this context.
- Artifacts are created inside this context.
- Lineage expresses relationships on top of this context.

If the context model is shaky, the meaning in the rest of the guide becomes shaky too.

## After Reading This Page

The next pages explain the actual observations and outputs that sit on top of context.

- record structure: [Observability Records](./observability-records.md)
- artifacts and lineage: [Artifacts And Lineage](./artifacts-and-lineage.md)

Usually the most natural next page is [Observability Records](./observability-records.md).
