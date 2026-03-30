# Compatibility And Migrations

[User Guide Home](./README.md)

Once a project has been running for a while, the period where only the current schema exists is usually shorter than people expect. This page explains the compatibility readers used to lift older payloads into the current Spine contract safely, and the migration mindset around them.

This page answers questions like:

- why a separate path is needed in addition to the normal deserializer,
- what a compatibility reader returns,
- in which situations the migration path should be used.

The key point is not just "it can read old versions too." If you are new to Spine, the most important thing to understand here is what must be recorded when historical payloads are brought into the current contract. Spine treats compatibility not as hidden convenience, but as an auditable upgrade path.

## Why A Separate Compatibility Path Is Needed

In real systems, payloads do not stay on the current schema forever.

Examples:

- an older producer is still alive,
- historical payloads stored long ago need to be read again,
- old field names still remain in team-to-team transfers.

If you use only the current-schema deserializer in that situation, two bad outcomes appear:

- it breaks too easily,
- or worse, it is read incorrectly in a silent way.

Compatibility readers offer an explicit upgrade path between those two extremes.

Spine does not aim for automatic magic here. It acknowledges that legacy payloads may differ from the current schema, and chooses to bring them forward while recording which fields changed and how.

## Readers Currently Provided

- `read_compat_project`
- `read_compat_artifact_manifest`

As the schema expands, more readers may be added later.

In the current implementation, explicit compatibility paths are provided for project and artifact manifest inputs. In other words, Spine is closer to "show exactly which compatibility paths are supported" than to "silently support every type forever."

## CompatibilityResult

A compatibility reader returns:

- `value`: the object converted into the current schema,
- `source_schema_version`: the original payload version,
- `notes`: descriptions of which field mappings and upgrades happened.

This structure matters because "it was read successfully" is not enough by itself. It is equally important to know what normalization happened during the read.

Put differently, `CompatibilityResult` answers three questions:

- what was read: `value`,
- what version it originally was: `source_schema_version`,
- what transformations were needed to bring it into the current contract: `notes`.

That is what lets the compatibility path behave more like a migration audit trail than a simple loader.

Each note is usually easiest to understand as:

- `path`: where the mapping or transformation happened,
- `message`: what upgrade or mapping took place.

## Example: Reading A Legacy Project

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

In this case, the reader:

- maps `ref` -> `project_ref`,
- maps `created` -> `created_at`,
- normalizes the timestamp,
- upgrades the schema version.

Conceptually, the result looks something like:

```text
value = Project(...)
source_schema_version = "0.9.0"
notes = [
  {path: "ref", message: "Mapped legacy 'ref' to 'project_ref'."},
  {path: "created", message: "Mapped legacy 'created' to 'created_at'."},
  {path: "schema_version", message: "Upgraded payload from 0.9.0 to 1.0.0."},
]
```

## Example: Reading A Legacy Artifact

```python
from spine import read_compat_artifact_manifest

result = read_compat_artifact_manifest(
    {
        "schema_version": "0.9.0",
        "artifact_ref": "artifact:checkpoint-01",
        "artifact_kind": "checkpoint",
        "created_at": "2026-03-30T09:20:00Z",
        "producer_ref": "sdk.python.local",
        "run_ref": "run:run-01",
        "stage_execution_ref": "stage:train",
        "location_ref": "file://artifacts/checkpoint.ckpt",
        "hash": "sha256:abc123",
    }
)
```

In this case, the reader:

- maps legacy `hash` to `hash_value`,
- emits an upgrade note for the schema version.

So on the artifact path, concrete field transforms such as renames become especially visible. Later, when you want to find which producers still emit old field names, those notes become direct operational clues.

## Deserializer vs Compatibility Reader

### deserializer

- assumes the current schema,
- is stricter,
- raises `SerializationError` on validation failure.

### compatibility reader

- can accept older schemas,
- performs explicit field mappings,
- returns upgrade notes,
- raises `CompatibilityError` for unsupported versions.

In one line:

- the deserializer is the door that accepts only the current contract,
- the compatibility reader is the door that translates an older contract into the current one.

Keeping those two separate is important. That is what prevents the current-schema boundary from blurring with the migration boundary.

## When To Use A Compatibility Reader

- when producer versions are mixed,
- when historical payloads need to be read,
- when old and new field names coexist during migration,
- when you need to record which automatic adjustments were applied.

If all input is already on the current schema, a normal deserializer is the better fit.

## What A Compatibility Reader Actually Does

Based on the current implementation, a compatibility reader usually follows this sequence:

1. read the payload's `schema_version`,
2. check whether that version is supported,
3. map legacy field names to current field names,
4. normalize values such as timestamps into current canonical form,
5. construct a current-schema object,
6. validate it again with the current validator,
7. record every adjustment in `notes`.

So even the compatibility path still aims for the same endpoint: a current canonical object. The difference is that it has one extra step up front to reconcile version differences.

## End-To-End, What Does Migration Look Like

In practice, the most natural way to think about migration is:

1. an old producer or historical store emits a legacy payload,
2. the compatibility reader checks the version,
3. legacy fields and formats are normalized into the current contract,
4. a current canonical object is built,
5. the current validator confirms that contract again,
6. every upgrade is recorded in `notes`,
7. from that point onward, downstream code handles only current-schema objects.

The key point here is that compatibility should not spread through the whole system. It should end at one boundary point. Once the data is inside, the safest pattern is to let everything see only current-schema objects.

## When Should You Consider Migration To Have Started

In practice, if any of the following are true, you are already in a migration state:

- some producers use new field names while others still use old names,
- timestamp formats differ by producer generation,
- historical payloads need to be re-read by the current analysis system,
- schema rollout cannot finish in one cutover and old and new versions must coexist for a while.

At that point, "let's just try the current deserializer first" usually creates more long-term confusion. Once you are in migration, it is much safer to document a migration path and preserve compatibility notes.

## How To Read Migration Operationally

Compatibility notes are more than extra logs. They can act like sensors for rollout state.

For example:

- only one producer keeps emitting `ref -> project_ref` notes,
- only one artifact path keeps emitting `hash -> hash_value` notes,
- timestamp normalization notes concentrate in one pipeline.

Patterns like those show exactly where an older contract still remains. So the compatibility layer is not just a reader. It is also a migration observability tool.

## Rollout Strategies

In practice, teams usually end up choosing one of the following three strategies.

### 1. strict cutover

Reject all legacy input after a certain point in time.

Advantages:

- simple operations,
- a very clear current-schema boundary.

Disadvantages:

- if producer rollout is not perfectly synchronized, this can cause incidents.

### 2. bounded compatibility

Run compatibility readers only for a bounded period.

Advantages:

- fits realistic rollouts well,
- allows migration state to be tracked through notes.

Disadvantages:

- if no end condition is managed, it easily becomes technical debt.

### 3. long-tail historical support

Continue reading old versions for a long time because of backfills or audit demands.

Advantages:

- long-term stored data stays usable.

Disadvantages:

- compatibility rules can become complex,
- the reader can turn into a version museum.

Spine's current direction usually fits the second strategy best: operate compatibility explicitly for as long as needed, then retire it gradually using notes and fixtures as evidence.

## Migration Operations Tips

- If you log compatibility notes, it becomes much easier to track which legacy producers are still alive.
- Fields that trigger many upgrades can serve as indicators of rollout status.
- If you need to keep compatibility paths for a long time, it is usually best to keep fixtures versioned too.

The following principles also help:

- keep compatibility rules small and explicit by version whenever possible,
- define a retirement point inside the team instead of treating indefinite compatibility as the default,
- connect note patterns to the migration backlog.

So compatibility is closer to an operational mechanism for safe transition than to a permanent feature.

## When To Remove A Compatibility Path

This question matters too. Compatibility paths are useful, but if they stay forever they can become a museum of old contracts rather than an implementation of the current one.

You can usually consider shrinking or removing a compatibility path when:

- there are no more legacy producers,
- historical backfill is complete,
- compatibility notes occur rarely enough,
- related fixtures and rollout documents have been cleaned up.

So the healthy attitude is not "more compatibility is always safer." It is "operate compatibility explicitly only while it is needed."

Practically, it is better to define clear exit conditions ahead of time rather than rely on the vague feeling that "it probably is not needed anymore."

Examples:

- compatibility notes have been nearly absent for 30 days,
- all official producers have shipped the current schema,
- historical reprocessing has ended,
- fixtures are already reorganized around the current schema.

Without criteria like those, temporary compatibility paths turn into permanent ones.

## Common Mistakes

### 1. Sending legacy input directly to the deserializer

This may break, or worse, it may appear to work while being interpreted incorrectly.

### 2. Not recording which mappings occurred in the compatibility path

If you only look at success or failure, it is hard to tell how far migration has really progressed.

### 3. Mixing too many schema versions into one reader without structure

Version-specific rules are much easier to maintain when they stay explicit.

### 4. Ignoring compatibility notes and only checking success

If reads succeed but upgrades keep happening constantly, migration is not finished yet.

### 5. Using the compatibility reader as the normal entrance for current-schema payloads

Once that happens, the boundary between current contracts and migration contracts blurs, and it becomes harder to know which inputs are truly current.

### 6. Relying on "it happens to parse" instead of explicit migration rules

If you assume two contracts are the same just because some fields happen to line up, you create the most dangerous kind of silent misunderstanding.

## What To Do After It Has Been Lifted Into The Current Schema

The goal of a compatibility reader is not to spread migration state across the whole system. Its goal is to produce a current-schema object.

So the usual pattern is:

- obtain the current object from the compatibility reader,
- then keep business logic, validation-result handling, and serialization boundaries working only in current-schema terms whenever possible.

In other words, migration should not become the system's default internal state. It should behave like translation work that ends at the boundary.

## The Core Intuition To Keep From This Page

In very short form:

- a compatibility reader is an explicit translation layer that lifts legacy input into a current-schema object,
- knowing what was upgraded is as important as knowing that the read succeeded,
- during migration, the compatibility path can be safer than a strict deserializer,
- compatibility should be a traceable and retireable operational path, not permanent magic.

## Next Documents

- reading current-schema payloads: [Serialization And Schema](./serialization-and-schema.md)
- extension policy: [Extensions And Custom Fields](./extensions-and-custom-fields.md)
