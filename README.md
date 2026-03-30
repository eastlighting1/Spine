# Spine

[![Actions status](https://github.com/eastlighting1/Spine/actions/workflows/ci.yml/badge.svg)](https://github.com/eastlighting1/Spine/actions/workflows/ci.yml)

`Spine` is a canonical contract library for ML observability systems.

Korean README: [README.ko.md](./README.ko.md)

It gives teams a shared model for execution context, observability records, artifacts, lineage, validation, deterministic serialization, and compatibility-aware reading. Instead of letting each producer invent its own payload shape, Spine gives you one contract for building, validating, serializing, and re-reading the same kinds of objects consistently.

The repository includes a GitHub Actions workflow for linting, type-checking, tests, dependency auditing, package builds, and repository-level security checks.

## Why Spine

ML systems usually drift in the same places:

- run and project identity,
- metric and event payload shape,
- timestamp normalization,
- artifact metadata,
- lineage and provenance representation,
- legacy payload handling.

Spine exists to stop that drift at the model layer.

With Spine, you can model:

- execution context with `Project`, `Run`, `StageExecution`, `OperationContext`, and `EnvironmentSnapshot`,
- observability records with `StructuredEventRecord`, `MetricRecord`, and `TraceSpanRecord`,
- durable outputs with `ArtifactManifest`,
- semantic relationships with `LineageEdge` and `ProvenanceRecord`,
- contract enforcement through validation and deterministic serialization,
- legacy upgrade paths through explicit compatibility readers.

## Core Ideas

Spine is easiest to understand through one simple shape:

```text
Project
  -> Run
    -> StageExecution
      -> OperationContext
        -> RecordEnvelope + Payload

Run / Stage
  -> ArtifactManifest

Refs between objects
  -> LineageEdge
  -> ProvenanceRecord
```

The library is built around a few strong defaults:

- use `StableRef` instead of ad hoc identity strings inside models,
- keep execution context separate from observed facts,
- validate objects right after construction,
- serialize into deterministic canonical payloads,
- treat migration as an explicit compatibility path, not silent magic.

## Installation

For local development with `uv`:

```bash
uv run --with-editable . python
```

To verify imports:

```bash
uv run --with-editable . python -c "import spine; print(spine.__file__)"
```

To run tests:

```bash
uv run pytest tests
```

## Quick Example

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
        unit="ratio",
    ),
)
validate_metric_record(metric).raise_for_errors()

print(to_json(metric))
```

The basic usage loop is:

1. build canonical objects,
2. validate them,
3. serialize them only at system boundaries.

## What You Get

- Canonical models for context, records, artifacts, lineage, and provenance.
- Strict validation for refs, timestamps, enum values, and schema boundaries.
- Deterministic JSON-compatible serialization for fixtures, storage, hashing, and transport.
- Current-schema deserializers that parse and validate raw payloads.
- Compatibility readers that upgrade supported legacy payloads into current canonical objects.
- Governed extensions through namespaced `ExtensionFieldSet` and `ExtensionRegistry`.

## Documentation

- English guide: [docs/en/README.md](./docs/en/README.md)
- Korean guide: [docs/ko/README.md](./docs/ko/README.md)
- English API reference: [docs/en/api-reference.md](./docs/en/api-reference.md)
- Korean API reference: [docs/ko/api-reference.md](./docs/ko/api-reference.md)

If you are new to the project, the fastest path is:

1. [Getting Started](./docs/en/getting-started.md)
2. [Understanding Spine Models](./docs/en/understanding-spine-models.md)
3. [Context Models](./docs/en/context-models.md)
4. [Observability Records](./docs/en/observability-records.md)
5. [Artifacts And Lineage](./docs/en/artifacts-and-lineage.md)

## Repository Layout

- `src/spine`: public package and implementation
- `examples`: runnable example flows
- `tests`: model and serialization tests
- `docs/en`: English guide
- `docs/ko`: Korean guide

## Current Status

This repository is currently at an early stage, but the core contract surface is already in place:

- canonical object modeling,
- validation,
- deterministic serialization,
- compatibility-aware reading,
- extension namespace governance.

The included example and current test suite both run successfully with `uv`.
