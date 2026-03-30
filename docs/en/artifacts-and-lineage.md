# Artifacts And Lineage

[User Guide Home](./README.md)

Spine is not only a library for events and metrics emitted during execution. It can also model execution outputs such as model checkpoints, evaluation reports, and feature snapshots, along with the relationships between them. This page explains `ArtifactManifest`, `LineageEdge`, and `ProvenanceRecord`.

On a first read, two ideas matter most:

1. an artifact is not just file metadata; it is an execution output,
2. lineage should be stored as its own model, not left as a free-form explanation string.

## Why Artifacts And Lineage Are Their Own Layer

A system can function for a while with only metrics and events. But ML systems quickly raise questions like:

- which run produced this checkpoint,
- which stage created this report,
- from which dataset or prior artifact was this model derived,
- was this relationship explicit or inferred.

To answer those, file paths or description strings are not enough. That is why Spine gives artifacts and relationships their own model layer.

Put more directly:

- observability records capture "what happened during execution,"
- artifacts capture "what durable result remained after execution,"
- lineage captures "where that result came from."

In ML systems, reproducibility, deployment traceability, and evaluation comparison usually become difficult because the third axis is missing. Files may exist, but if their links to data, executions, and prior outputs are not structured, the system ends up relying on human memory and external operating documents.

## ArtifactManifest

`ArtifactManifest` represents outputs such as model checkpoints, evaluation reports, feature snapshots, or exported datasets.

Major fields:

- `artifact_ref`
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

Example:

```python
from spine import ArtifactManifest, StableRef

checkpoint = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=StableRef("stage", "train"),
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
    hash_value="sha256:abc123",
    size_bytes=184223744,
    attributes={"framework": "pytorch", "dtype": "float16"},
)
```

The payload shape looks roughly like this:

```json
{
  "artifact_kind": "checkpoint",
  "artifact_ref": "artifact:checkpoint-epoch-1",
  "attributes": {
    "dtype": "float16",
    "framework": "pytorch"
  },
  "created_at": "2026-03-30T09:20:00Z",
  "extensions": [],
  "hash_value": "sha256:abc123",
  "location_ref": "file://artifacts/checkpoints/epoch_1.ckpt",
  "producer_ref": "scribe.python.local",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "size_bytes": 184223744,
  "stage_execution_ref": "stage:train"
}
```

### Why ArtifactManifest Is More Than File Metadata

In Spine, an artifact is not just a file pointer. It is an object that also explains:

- which execution created it,
- which stage produced it,
- who produced it,
- where it is stored,
- what integrity information it has.

So an artifact is not just "a file somewhere." It is an explainable execution output.

One reason this separate model helps is that location and identity stay decoupled. A file can move or storage can change, but "what artifact this was" should remain stable.

### Questions ArtifactManifest Answers

- which run created it,
- which stage produced it,
- where it is stored,
- what its checksum and size are,
- what kind of artifact it is.

### How To Think About `artifact_kind`

`artifact_kind` describes the role of the artifact.

Examples:

- `checkpoint`
- `report`
- `dataset`
- `feature_snapshot`

This matters because it helps consumers decide what kind of output they are interpreting.

It is usually best to keep the `artifact_kind` vocabulary narrow inside a team. If you start mixing `checkpoint`, `model_checkpoint`, `training_checkpoint`, and `ckpt`, consumers end up reinterpreting the same class of output in many ways.

A better pattern is:

- keep a small set of stable kinds,
- put finer distinctions in `attributes`,
- add a new kind only when it has really become a shared meaning.

### When To Use `attributes`

This field holds additional metadata attached to the artifact.

Examples:

- `framework: pytorch`
- `dtype: float16`
- `split: validation`

But it is usually better not to push every important meaning into `attributes`. Core structure should stay in top-level fields.

A useful practical split is:

- top-level fields: structure almost every consumer must understand,
- `attributes`: supplemental metadata that may vary by artifact kind.

For example, where the artifact is and which execution produced it should be top-level, while framework or data split are more naturally stored in `attributes`.

### `location_ref`, `hash_value`, `size_bytes`

These three fields are what make an artifact operationally useful.

#### `location_ref`

This points to where the artifact currently lives.

Examples:

- `file://...`
- an object storage URI,
- an internal registry address.

The important point is that `location_ref` is not the artifact's identity itself. Location may change; `artifact_ref` should remain as stable as possible.

#### `hash_value`

This is useful for integrity checks and identity comparison.

For example, two checkpoints with the same name may still be different artifacts if the hash differs. Conversely, if a location changes but the hash is identical, you can quickly confirm the binary is the same.

#### `size_bytes`

At first glance this may look like an unimportant detail, but it is often useful operationally.

Examples:

- tracking storage cost,
- detecting strange artifact output,
- catching abnormally small results early.

Together, these three fields help answer "where is it, is it the same thing, and is its size normal."

## LineageEdge

`LineageEdge` expresses the semantic relationship between two refs.

Major fields:

- `relation_ref`
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

Allowed relation types:

- `generated_from`
- `consumed_by`
- `produced_by`
- `packaged_from`
- `reported_by`
- `evaluated_on`
- `deployed_from`
- `used`
- `derived_from`
- `observed_in`

### What LineageEdge Represents

In simple terms, it expresses "what semantic connection exists between A and B."

Example interpretations:

- a checkpoint artifact was `generated_from` a dataset,
- a metric report was `reported_by` a run,
- a serving model was `deployed_from` a training artifact.

Example code:

```python
from spine import LineageEdge, StableRef

edge = LineageEdge(
    relation_ref=StableRef("relation", "checkpoint-from-dataset"),
    relation_type="generated_from",
    source_ref=StableRef("artifact", "dataset-train-v3"),
    target_ref=StableRef("artifact", "checkpoint-epoch-1"),
    recorded_at="2026-03-30T09:21:00Z",
    origin_marker="pipeline_declared",
    confidence_marker="high",
    operation_context_ref=StableRef("op", "train-step"),
    evidence_refs=("record:trace-forward-001", "artifact:report-eval-01"),
)
```

As a payload, it looks roughly like this:

```json
{
  "confidence_marker": "high",
  "evidence_refs": [
    "record:trace-forward-001",
    "artifact:report-eval-01"
  ],
  "extensions": [],
  "operation_context_ref": "op:train-step",
  "origin_marker": "pipeline_declared",
  "recorded_at": "2026-03-30T09:21:00Z",
  "relation_ref": "relation:checkpoint-from-dataset",
  "relation_type": "generated_from",
  "schema_version": "1.0.0",
  "source_ref": "artifact:dataset-train-v3",
  "target_ref": "artifact:checkpoint-epoch-1"
}
```

### Why A Relation Is Its Own Model

You could leave only a string description like this:

```text
"this model was derived from dataset-x"
```

That is acceptable for human reading, but poor for system reasoning and querying.

By contrast, keeping it as `LineageEdge` gives you:

- structured source and target,
- normalized relation type,
- easier lineage queries and visualization.

An even more important difference is that a relation is an interpretation that may later be recalculated or refined. The artifact itself is usually a more stable fact, while the relationship between artifacts can evolve as rules change or new evidence appears. That is why separating artifact and lineage is much more flexible over time.

### How To Think About Source And Target

Direction matters for each relation.

Examples:

- `generated_from`: the target is generated from the source,
- `deployed_from`: the target is deployed from the source.

So when designing lineage, it is important to keep direction consistent, not just the relation type.

If that consistency is missing, the same relationship will have to be read left-to-right in some edges and right-to-left in others, which quickly makes lineage graphs confusing. In practice, it helps to agree on the sentence form for each relation type.

Examples:

- `target generated_from source`
- `target deployed_from source`
- `target evaluated_on source`

Once that rule is fixed, it becomes much easier to assign source and target consistently for new edges.

### How To Choose A Relation Type

The relation type should reveal not just that two objects are connected, but what that connection means.

For example, even if you want to record a relationship between a checkpoint and a dataset, the right type can differ:

- if the checkpoint is a training result, `generated_from`,
- if the dataset was simply read and used, `used`,
- if an evaluation was performed against a dataset, `evaluated_on`.

So relation type is not just a label. It is the core semantic field that determines later query behavior and interpretation.

### `origin_marker`, `confidence_marker`, `evidence_refs`

These three fields are what make lineage more than a simple connecting line. They turn it into an interpretable claim.

#### `origin_marker`

This shows how the relationship was created.

Examples:

- explicitly declared in pipeline code,
- imported from an external catalog,
- generated by a post-processing analyzer.

#### `confidence_marker`

This expresses how strongly the relationship should be trusted.

If explicit and inferred lineage are treated as equally trustworthy, operational decisions can become unstable. That is why confidence is more important than it first appears.

For example:

- a `generated_from` relationship emitted directly by the pipeline might be `high`,
- one inferred by log correlation might be `medium`,
- one produced by a weak heuristic might be `low`.

Even if the exact vocabulary is not fully fixed in the schema, teams should usually keep a consistent confidence vocabulary internally.

#### `evidence_refs`

These are additional refs that support the relationship.

Examples:

- the trace span that produced the relationship,
- a report artifact that explains the relationship,
- another record that proves the relationship.

So `LineageEdge` captures the conclusion "model B came from dataset A," while `evidence_refs` gives you a way to follow why that conclusion was made.

The important point is that evidence does not replace lineage itself. Even if you keep many evidence refs, consumers still need a structured relation. Spine's model keeps the relation explicit first, then uses evidence as a supporting layer.

## ProvenanceRecord

`ProvenanceRecord` is the type that explains the basis and formation context of a lineage assertion.

Major fields:

- `provenance_ref`
- `relation_ref`
- `formation_context_ref`
- `policy_ref`
- `evidence_bundle_ref`
- `assertion_mode`
- `asserted_at`
- `schema_version`
- `extensions`

Allowed assertion modes:

- `explicit`
- `imported`
- `inferred`

If `LineageEdge` says "what is the relationship," then `ProvenanceRecord` says "why was that relationship judged to be true."

### What Assertion Mode Means

- `explicit`: declared directly by a system or user,
- `imported`: brought in from an external system,
- `inferred`: derived by a rule or analysis.

This distinction matters a great deal. Even for the same lineage, explicit and inferred relationships may deserve different trust and interpretation.

Example code:

```python
from spine import ProvenanceRecord, StableRef

provenance = ProvenanceRecord(
    provenance_ref=StableRef("provenance", "prov-checkpoint-from-dataset"),
    relation_ref=StableRef("relation", "checkpoint-from-dataset"),
    formation_context_ref=StableRef("op", "lineage-builder"),
    policy_ref="policy:lineage-min-confidence-v1",
    evidence_bundle_ref="bundle:evidence-checkpoint-01",
    assertion_mode="inferred",
    asserted_at="2026-03-30T09:21:05Z",
)
```

In payload form, that looks like:

```json
{
  "asserted_at": "2026-03-30T09:21:05Z",
  "assertion_mode": "inferred",
  "evidence_bundle_ref": "bundle:evidence-checkpoint-01",
  "extensions": [],
  "formation_context_ref": "op:lineage-builder",
  "policy_ref": "policy:lineage-min-confidence-v1",
  "provenance_ref": "provenance:prov-checkpoint-from-dataset",
  "relation_ref": "relation:checkpoint-from-dataset",
  "schema_version": "1.0.0"
}
```

`ProvenanceRecord` matters because a lineage edge alone only says "there is a relationship." It does not preserve which policy, which formation context, or which evidence bundle led to that decision.

### `formation_context_ref`, `policy_ref`, `evidence_bundle_ref`

These three fields make provenance operationally useful.

#### `formation_context_ref`

This points to the workflow that formed the provenance.

Examples:

- a lineage builder job,
- a catalog import job,
- an audit reconciliation step.

#### `policy_ref`

This explains which rule or policy allowed the relationship to be accepted.

Once this exists, it becomes much easier to ask later why one relationship was accepted while another was rejected under a specific policy.

#### `evidence_bundle_ref`

This is useful when many pieces of evidence need to be pointed to as one bundle. If individual `evidence_refs` are relation-level hints, the bundle is more like a provenance-level pointer to "the set of evidence used for this judgment."

## Patterns For Using Artifact And Lineage Together

For example, if a training run produces a checkpoint artifact and you want to say that checkpoint was derived from a particular dataset:

1. create the checkpoint with `ArtifactManifest`,
2. create a dataset -> checkpoint relationship with `LineageEdge`,
3. if needed, add the basis with `ProvenanceRecord`.

This pattern becomes useful later for lineage visualization, audit trails, and reproducibility analysis.

If you turn the same flow into questions:

- artifact: "what was created,"
- lineage edge: "what came from what,"
- provenance: "why was that judged to be true."

Separating the three lets you recalculate relationships or change confidence policies later without disturbing artifact identity itself.

### Real Scenario 1. Training Pipeline

In a training pipeline, the following combination is common:

1. register the training dataset artifact,
2. create the checkpoint artifact,
3. create the evaluation report artifact,
4. add `generated_from` from dataset -> checkpoint,
5. express checkpoint -> report with `reported_by` or another appropriate evaluation relationship,
6. add provenance if the relationship is policy-based or inferred.

With that structure, it becomes easy to follow "which model produced this report, and which data produced that model."

### Real Scenario 2. Deployment Flow

For deployment, the important questions often become:

- which artifact is the source of the currently serving model,
- what training result did that artifact come from,
- was the deployment relationship explicitly declared or imported from another system.

In that case, the natural pattern is:

1. register the deployment target artifact,
2. add `deployed_from` between the source model artifact and deployed target,
3. record whether it was imported or explicit in provenance.

### Real Scenario 3. Inference Result Analysis

Artifact and lineage are also useful in inference systems.

Examples:

- which model version supplied the basis for a feature snapshot,
- which serving model a given report was generated against,
- which dataset snapshot a drift analysis result was computed on.

So this layer is not only for training pipelines. It is a shared tracking layer that extends into deployment and analysis.

## How Far Should You Introduce Lineage

### Minimal level

Manage artifacts only, without lineage yet.

Good fit when:

- you are just starting artifact tracking,
- relationship-query needs are still small.

### Operational level

Keep only the major relationships between core artifacts as `LineageEdge`.

Good fit for:

- dataset -> model,
- model -> report,
- model -> deployed artifact.

The key at this stage is not to model everything. Start with the relationships you know you will need to ask about later.

### Audit / reproducibility level

Operate `LineageEdge` and `ProvenanceRecord` together.

Good fit when:

- you must explain where relationships came from,
- you must distinguish imported lineage from inferred lineage,
- policy-driven analysis is needed.

At this level, the important question is no longer only "what does the graph say" but also "why should we trust this graph."

## Common Mistakes In Artifact And Lineage Modeling

### 1. Treating an artifact as only a path string

This makes it easy to lose run, stage, producer, and hash information.

### 2. Leaving relationships only as prose

That keeps the system from understanding lineage structurally.

### 3. Not distinguishing inferred relationships from explicit ones

Later, it becomes difficult to separate confidence levels.

### 4. Using `artifact_kind` as uncontrolled free text

If kind becomes effectively arbitrary text, consumers have a hard time interpreting it consistently.

### 5. Letting source and target direction vary arbitrarily by relation

Even if the relation type is the same, inconsistent edge direction makes lineage queries and visualization much more confusing.

### 6. Failing to preserve evidence and provenance all the way through

At first, the relation alone may look sufficient. But as soon as auditability or reproducibility matters, you lose the ability to explain why the relation was trusted.

### 7. Treating artifact identity and location as the same thing

The moment a file path or object storage key changes, the same artifact can be mistaken for a different one.

### 8. Trying to model every relation in fine detail too early

Lineage is important, but if you try to make the entire graph perfect from day one, operations often stall. A more realistic path is to stabilize the core relationships first, then expand provenance and evidence later.

## The Core Intuition To Keep From This Page

In very short form:

- `ArtifactManifest`: the identity and execution context of an output,
- `LineageEdge`: the semantic connection between outputs,
- `ProvenanceRecord`: the reason and evidence behind that connection.

If you keep those three layers separate, later location changes, relationship recalculation, or policy updates can happen without shaking the model too much.

## Why This Layer Matters In Operations

Once artifact and lineage structure is solid, questions like these become possible:

- which model came from which dataset,
- which artifact is the source of the currently deployed model,
- which relationships are imported and which are inferred,
- what evidence and policy support a specific artifact relationship.

So this is not just supporting metadata. It is the foundation for reproducibility, auditability, and lineage visualization.

## Next Documents

- execution context: [Context Models](./context-models.md)
- events, metrics, and traces: [Observability Records](./observability-records.md)
