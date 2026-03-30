# Extensions And Custom Fields

[User Guide Home](./README.md)

Once Spine is introduced into a real team, there are almost always team-specific metadata fields that the standard model does not yet capture. This page explains what should go into extensions and what should not.

If you are new to the library, the most accurate way to understand extensions is not as "free fields" but as "a controlled extension point that lets teams add their own meaning without breaking the shared contract."

## Why Extensions Exist

In real systems, standard fields alone are rarely enough to represent every useful meaning.

Examples:

- team-specific owner information,
- internal priority,
- deployment approval state,
- internal policy classification.

But if fields like these are added to the top level without constraint, the shared contract collapses quickly. Spine avoids that by separating extensions into their own structure.

So an extension is not a replacement space for the core schema. It is a buffer layer that protects the core schema while still making room for practical local needs.

## ExtensionFieldSet

This is the actual unit of extension data attached to an object.

```python
from spine import ExtensionFieldSet

ext = ExtensionFieldSet(
    namespace="ml.team",
    fields={
        "owner": "research-platform",
        "priority": "high",
    },
)
```

Rules:

- the namespace must contain `.`,
- fields are internally key-sorted.

So an extension is not a totally free dict. It assumes at least a minimum amount of governance.

In payload form, it usually looks like this:

```json
{
  "namespace": "ml.team",
  "fields": {
    "owner": "research-platform",
    "priority": "high"
  }
}
```

And this value can be attached to the `extensions` field of many canonical objects such as `Project`, `Run`, `StageExecution`, `RecordEnvelope`, `ArtifactManifest`, `LineageEdge`, and `ProvenanceRecord`. In other words, an extension is not specific to a single type. It is a governed metadata unit that can be attached across Spine as a whole.

For example, attached to an artifact:

```python
from spine import ArtifactManifest, ExtensionFieldSet, StableRef

artifact = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=StableRef("stage", "train"),
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
    extensions=(
        ExtensionFieldSet(
            namespace="ml.team",
            fields={"owner": "research-platform", "priority": "high"},
        ),
    ),
)
```

So an extension is not a special side structure for one type. It is an additional semantic layer attached in the same way across the shared model.

## ExtensionRegistry

This is the registry used to manage namespace ownership.

```python
from spine import ExtensionRegistry

registry = ExtensionRegistry()
registry.register("ml.team", owner="research-platform")
```

Major methods:

- `register(namespace, owner)`
- `is_registered(namespace)`
- `owner_for(namespace)`

Trying to re-register a namespace that already belongs to another owner raises `ExtensionError`.

In the current code, the registry is an explicit utility for managing namespace ownership. It tracks who owns which namespace, but it is closer to a governance foundation tool than to a global policy engine that automatically enforces every extension attachment at runtime. That description is based on the current implementation.

## When To Use An Extension

- when you need team-specific metadata not yet present in the standard schema,
- when a field is not yet stable or general enough for the core schema,
- when you want ownership and namespace boundaries to stay explicit.

For example:

- internal team owner,
- internal operational priority,
- internal tags for experiment classification.

Fields like these are natural extension candidates.

In practice, these questions help:

- is this information important only to our team,
- is it not yet stable enough to promote into the shared schema,
- is it acceptable if only some consumers understand it.

If the answer is close to yes for all three, an extension is usually a good fit.

## When To Avoid Extensions

- when the meaning is already expressible as a standard field,
- when every consumer must understand it as core meaning,
- when a better model already exists, such as a relation or artifact field.

So an extension is the space for "meaning not yet standardized," not a shortcut around the core model.

Examples:

- putting another execution identifier in an extension even though `run_ref` already exists,
- storing a lineage explanation only in an extension when a lineage relation is really needed,
- hiding a critical state in an extension that every consumer must understand.

Patterns like those are not healthy extension usage. They are closer to dodging the core schema.

## How Extension, Attribute, And Tag Differ

This question comes up frequently in practice. The simplest way to think about it is this.

### core field

This is part of the central Spine contract.

- every consumer should understand it,
- the validator and schema give it direct meaning.

### object-specific metadata

This is type-local supporting information, such as artifact `attributes` or project `tags`.

- it is interpreted only inside that type's own context,
- it does not carry a separate namespace.

### extension

This is a namespace-based, team-level extension that can attach across multiple types.

- it is useful when ownership needs to stay separate,
- it is a good place for meaning that is still too early for the core schema.

So a useful deciding question is: "is this just natural supporting metadata inside one object type, or does it need a team-level namespace across the model."

## Recommended Operating Style

### 1. Choose namespaces by organization or domain

Examples:

- `ml.team`
- `serving.platform`
- `risk.policy`

It is usually best to choose namespaces that still make sense years later. Once temporary project names or individual names become namespaces, ownership becomes unclear over time and cleanup becomes expensive.

### 2. Operate it as an extension first, then promote if needed

This is safer than putting it directly into the core schema.

In that sense, an extension often acts as an incubation space. If usage spreads and the meaning stabilizes, it can become a core schema promotion candidate. Otherwise, it can remain team-local.

### 3. Do not duplicate the same meaning across many namespaces

If owner information is scattered across multiple namespaces, the standardization benefit quickly disappears.

## Intuition For Designing Extensions

Good extensions usually have these qualities:

- you can guess who owns them just by seeing the namespace,
- field names are consistent inside that namespace,
- they do not strongly collide with the core schema,
- consumers that do not understand them can still interpret the object reasonably well.

Bad extensions tend to look like this:

- namespaces are too broad or too vague,
- the same meaning is repeated across multiple namespaces,
- core relationship or identity meaning is bypassed through extensions,
- there is no promotion or cleanup criterion even after long use.

## When To Promote An Extension Into The Core Schema

Promotion is worth considering when:

- multiple teams use the same meaning in the same way,
- most consumers now need to understand the field commonly,
- it is no longer a team exception but part of the shared contract,
- differences between extension namespaces are starting to create more confusion than clarity.

So an extension is not only a permanent storage area. It can also be an incubation space for future core-schema candidates.

## Healthy Patterns For Extensions In Operations

The following patterns are usually stable.

### Keep namespace ownership explicit

If nobody knows who defines and can change the field semantics, an extension turns into a shared junk drawer very quickly.

### Document the field vocabulary briefly

For example, if a team uses `ml.team.priority`, it is best to define the allowed vocabulary like `high/medium/low` explicitly inside the team.

### Design consumer fallback behavior

Consumers that do not understand a namespace should still behave reasonably. Extensions are safest when they are "extra information if known" rather than "critical information without which the object breaks."

### Decide promotion or retirement criteria in advance

If you already know whether an extension will later become a core field candidate or disappear with a certain project, it is much easier to prevent extension sprawl.

## Common Mistakes

### 1. Using extensions as a free-field storage box

Once that happens, the namespace exists in name only and there is effectively no governance left.

### 2. Choosing namespaces that are too short or too vague

Ownership becomes unclear and collisions become more likely later.

### 3. Putting core meaning only into extensions

If every consumer must understand the information, it may belong more naturally in the core schema.

### 4. Managing namespaces only by convention without a registry

This may survive in a tiny team, but as organizations grow it quickly leads to ownership conflicts and duplicate definitions.

### 5. Putting meaning into extensions that breaks consumers if they do not understand it

Extensions are closer to auxiliary meaning. If a consumer cannot function without one, that is usually a sign the field is a core-field candidate.

## The Core Intuition To Keep From This Page

In very short form:

- an extension is a governed escape hatch that accepts team-specific meaning without breaking the shared contract,
- the namespace is the key mechanism for ownership and conflict prevention,
- an extension is not a replacement for the core schema, and may instead become the stage before promotion into it,
- good extension practice is closer to governance design than to simply adding fields.

## Next Documents

- practical assembly flows: [Workflow Examples](./workflow-examples.md)
- type structure details: [Context Models](./context-models.md), [Observability Records](./observability-records.md), [Artifacts And Lineage](./artifacts-and-lineage.md)
