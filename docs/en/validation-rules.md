# Validation Rules

[User Guide Home](./README.md)

Spine objects are easy to construct in Python, but that does not automatically make them valid canonical objects. This page explains the validation rules that check whether an object satisfies the Spine contract.

In other words, validation is not just type checking. It is contract enforcement. This step matters because it catches things like:

- wrong ref kinds early,
- invalid timestamp formats early,
- polluted enum and status values,
- failures at the construction point instead of only right before serialization.

More fundamentally, validation is not asking "can this object be created." It is asking "can this object be trusted as part of the Spine contract."

In Python, it is easy to create a dataclass object that contains bad values. The reason Spine matters is that it gives you one more gate before those objects are promoted into the canonical contract. Validation is that gate.

## Why Validation Is Its Own Layer

At first glance, it may seem simpler to block everything directly at object construction time. But by keeping validation as its own layer, Spine gets two things at once:

- model objects stay simple and composable,
- contract enforcement happens consistently in an explicit validation step.

This separation is very useful in practice.

For example:

- producer code can assemble an object step by step and validate at the end,
- migration tools can intentionally read incomplete objects and collect reports on which rules are broken,
- deserializers can reuse validation as a shared path after object construction.

So making validators their own layer lets Spine separate "object representation" from "contract enforcement" while still applying the same rules at every entry point.

## ValidationReport

Validators return a `ValidationReport`.

```python
from spine import validate_project

report = validate_project(project)
```

It contains:

- `valid`: overall success or failure,
- `issues`: the list of violated rules.

Each issue generally contains at least two things:

- `path`: which field failed,
- `message`: why it failed.

So a validation report is not just a success/failure flag. It is a structured result that explains which part of the contract was violated.

If you want to raise immediately:

```python
report.raise_for_errors()
```

That works well for a fail-fast pattern.

Conceptually, an accumulated failure looks like this:

```text
valid = False
issues = [
  {path: "run_ref", message: "kind must be 'run'"},
  {path: "started_at", message: "timestamp must be ISO-8601 UTC with trailing Z"},
]
```

Because of this structure, producer code can raise immediately, while UIs or batch inspection tools can show many issues together.

That matters because validation failure is not just a boolean event. In operations, "which fields keep breaking repeatedly" is often more important than simply "did this one object fail."

## What Validation Does And Does Not Cover

Validation does cover:

- allowed field values under the contract,
- ref kind matching,
- normalized timestamp format,
- temporal ordering rules,
- record type / payload type consistency,
- basic integrity conditions.

Validation does not directly cover:

- whether an external resource really exists,
- whether an artifact path is reachable,
- whether a ref really exists in some external store,
- whether a value is semantically correct for your business domain.

So validation checks whether the structure is contract-valid. It is not a replacement for full system integration checks.

It is important to keep this boundary clear. A strong validator does not guarantee "operationally correct data." Spine validators enforce the canonical contract and nothing more.

For example, a validator:

- checks whether `run_ref.kind == "run"`,
- but does not verify that the run already exists in storage.

It:

- checks whether a timestamp has normalized format,
- but does not decide whether that time is meaningful in your business schedule.

So validation is not an oracle for all meaning. It is the minimum gatekeeper that protects the contract.

## What Gets Validated

Current validation focuses on rules such as:

- whether the ref kind matches the expected kind,
- whether enum and status values are inside the allowed set,
- whether timestamps are normalized UTC `Z` strings,
- whether an end time comes after a start time,
- whether `recorded_at >= observed_at`,
- whether there are basic integrity violations such as negative `size_bytes`,
- whether `schema_version` matches the current schema.

In a more compressed form, Spine validation checks four broad categories:

- shape: are required fields blank,
- references: does `StableRef.kind` match expectation,
- time: do timestamps have valid format and ordering,
- semantic markers: are status, type, marker, and assertion-mode values inside allowed vocabularies.

Those four categories repeat across the whole model. So when you read validation rules, it helps to remember the higher-level intuition first: Spine is especially strict at ref, time, enum, and schema boundaries.

## Per-Type Validation Intuition

### Project

Checks include:

- `project_ref.kind == "project"`
- `name` is not blank
- `created_at` has normalized format
- `schema_version` matches

### Run

Checks include:

- `run_ref.kind == "run"`
- `project_ref.kind == "project"`
- status is allowed
- `started_at` is valid
- if `ended_at` exists, time ordering is valid

### StageExecution

Checks include:

- `stage_execution_ref.kind == "stage"`
- `run_ref.kind == "run"`
- `stage_name` is not blank
- status is allowed
- time ordering is valid

### OperationContext

Checks include:

- `operation_context_ref.kind == "op"`
- `run_ref.kind == "run"`
- if `stage_execution_ref` exists, `kind == "stage"`
- `operation_name` is not blank
- `observed_at` has normalized format

### EnvironmentSnapshot

Checks include:

- `environment_snapshot_ref.kind == "env"`
- `run_ref.kind == "run"`
- `captured_at` has normalized format
- `python_version` is not blank
- `platform` is not blank

### RecordEnvelope

Checks include:

- `record_ref.kind == "record"`
- `run_ref.kind == "run"`
- if `stage_execution_ref` exists, `kind == "stage"`
- if `operation_context_ref` exists, `kind == "op"`
- `recorded_at` and `observed_at` format
- `recorded_at >= observed_at`
- marker values are allowed

### MetricRecord

Checks include:

- `record_type == "metric"`
- `metric_key` is not blank
- `value_type` is allowed

### TraceSpanRecord

Checks include:

- `record_type == "trace_span"`
- `span_id` and `trace_id` are not blank
- `started_at <= ended_at`

### ArtifactManifest

Checks include:

- `artifact_ref.kind == "artifact"`
- `artifact_kind` is not blank
- `run_ref.kind == "run"`
- `size_bytes >= 0` if present

### LineageEdge

Checks include:

- `relation_ref.kind == "relation"`
- `relation_type` is inside the allowed set
- `recorded_at` has normalized format
- `origin_marker` is not blank
- `confidence_marker` is not blank

### ProvenanceRecord

Checks include:

- `provenance_ref.kind == "provenance"`
- `relation_ref.kind == "relation"`
- `assertion_mode` is allowed
- `asserted_at` has normalized format

So validation covers not only context and records, but also artifacts, lineage, and provenance.

## What The `schema_version` Check Means

For most canonical objects, Spine validators check that `schema_version` matches the current schema exactly.

That means:

- current-schema objects should pass the validator,
- legacy payloads should not be sent directly into normal validators or deserializers,
- instead, they should be upgraded through a compatibility reader and then validated.

So the `schema_version` check is what keeps version boundaries from blurring.

This matters because version mismatch often creates the most subtle type of corruption. A totally broken payload is easier to notice. A partially readable legacy payload is often more dangerous. Spine avoids that "it sort of works" state by making the current-schema check strict.

## How Validators, Deserializers, And Compatibility Readers Differ

These three paths can look similar, but their roles are different.

### validator

This checks whether an already-created canonical object respects the contract.

As a question:

- "can this object be accepted as a Spine object"

### deserializer

This reads a current-schema payload into a canonical object, then validates it.

As a question:

- "can this current-version payload be safely read as a Spine object"

### compatibility reader

This accepts a legacy payload, upgrades it to the current schema, records normalization and mapping notes, and then validates it.

As a question:

- "through what transformations can this historical payload be brought into the current contract"

In one line:

- validator: check
- deserializer: read current schema + check
- compatibility reader: upgrade legacy payload + check

Once that distinction is clear, it also becomes clear where each kind of external input should enter the system.

## Common Failure Cases

### Timestamp without trailing `Z`

```python
Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00",
)
```

This fails because it violates the contract timestamp format.

### Wrong ref kind

```python
Run(
    run_ref=StableRef("project", "oops"),
    project_ref=StableRef("project", "nova"),
    name="bad-run",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)
```

`run_ref` must have kind `run`.

This is dangerous operationally because once such a ref is stored, consumers may begin interpreting it as the wrong object type. Validation blocks that pollution at the entrance.

### Envelope and payload type mismatch

If you build a `MetricRecord` but set `record_type="structured_event"` in the envelope, validation fails.

This is not a minor typo. It is a structural error that makes it impossible for a consumer to know how the payload should be read.

### Reversed time order

If a trace span has `started_at > ended_at`, validation fails.

If errors like this accumulate, duration calculations, bottleneck analysis, and SLA aggregation all become distorted. So time validation protects downstream analysis, not just formatting.

### Recorded time earlier than observed time

```python
RecordEnvelope(
    record_ref=StableRef("record", "metric-1"),
    record_type="metric",
    recorded_at="2026-03-30T09:08:29Z",
    observed_at="2026-03-30T09:08:30Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=None,
    operation_context_ref=None,
)
```

This fails because it breaks the expected time semantics.

### Unsupported relation type

Validation fails if `LineageEdge` receives a `relation_type` outside the allowed vocabulary.

This prevents lineage vocabulary from drifting arbitrarily.

### Invalid assertion mode

If `assertion_mode` on `ProvenanceRecord` is not one of `explicit`, `imported`, or `inferred`, validation fails.

That rule is what keeps provenance trust interpretation consistent.

## Why These Failures Should Be Blocked Early

Validation failures rarely end with "one object is wrong." If left alone, they often spread into larger structural corruption.

Examples:

- wrong ref kinds break relationship links,
- bad timestamps distort time-series and duration analysis,
- wrong `record_type` destabilizes payload interpretation itself,
- wrong schema versions collapse migration boundaries.

So validation is both a local error detector and a system-wide defense for semantic consistency.

## When To Call Validation

### 1. Right after object construction

This is the most strongly recommended pattern.

```python
metric = MetricRecord(...)
validate_metric_record(metric).raise_for_errors()
```

### 2. Right before serialization

If an object has been assembled through several steps after construction, it can be useful to verify it again just before serialization.

### 3. After deserialization

Current deserializers already perform validation internally, but if your ingestion path needs additional domain checks, you can add another validation stage afterward.

In practice, Spine's current deserializers create an object, call a validator, and wrap failures in `SerializationError`. So for external payloads, the natural flow is:

1. read with a deserializer or compatibility reader,
2. add domain-specific validation if needed,
3. then move into storage or transmission.

So both paths exist:

- direct validator calls when you already have a model object,
- indirect validator calls inside deserializers and compatibility readers.

The practical rule of thumb is:

- if you are already building objects yourself, call validators directly,
- if you are reading external payloads, use deserializers or compatibility readers,
- if your system has extra business rules, layer domain validation after Spine validation.

## fail-fast vs accumulate

Spine's `ValidationReport` supports both patterns.

### fail-fast

```python
validate_project(project).raise_for_errors()
```

Advantages:

- fails quickly,
- keeps control flow simple,
- works well in producer code,
- makes it easier to stop bad objects before they continue downstream.

### accumulate

```python
report = validate_project(project)
if not report.valid:
    for issue in report.issues:
        ...
```

Advantages:

- collects many errors at once,
- fits UI, batch report, and migration tools,
- makes repeated rule-violation patterns easier to inspect.

In practice, fail-fast usually fits producer code, while accumulate fits migration and ingestion diagnostics better.

### When Each Pattern Is More Natural

`fail-fast` tends to fit better for:

- producer SDKs,
- request paths that should reject immediately,
- tests where you want to see the first failure right away.

`accumulate` tends to fit better for:

- batch import inspection,
- migration quality reports,
- admin UIs that need to show multiple input problems at once.

## Why Validation Matters In Operations

Validation is not just a developer convenience. It is the first defense line for operational quality.

Without validation:

- bad timestamps get stored,
- wrong ref kinds spread,
- record type and payload meaning drift apart,
- legacy or non-normalized payloads mix in silently.

These may look minor at first, but later they can pollute dashboards, lineage, and analysis results.

Systems without validation often drift into the worst state: "nothing looks broken, but the results are strange." That is why silent corruption is more dangerous than a hard failure.

This may be the most important message in the page. The purpose of Spine validation is not simply to be stricter. It is to move the pain earlier. Failing at the point of object construction is much cheaper and safer than discovering broken meaning after dashboards and analyses have already been built on top of it.

## Recommended Pattern

- validate right after object creation,
- validate again before serialization,
- accumulate reports in migration tooling,
- accept external input only through deserializers or compatibility readers.

## The Core Intuition To Keep From This Page

In short:

- a validator does not ask whether object construction succeeded; it asks whether the contract is respected,
- `ValidationReport` collects failure reasons structurally,
- deserializers also depend on validation internally,
- validation is not the last decorative step before storage; it is the defensive wall at the system boundary.

If you want to compress it even further, Spine validation can be remembered in one sentence:

"Do not try to recover from bad data later through interpretation; block contract-violating data before it enters the system at all."

## Next Documents

- payload production and reading: [Serialization And Schema](./serialization-and-schema.md)
- legacy input handling: [Compatibility And Migrations](./compatibility-and-migrations.md)
