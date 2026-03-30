# Serialization And Schema

[User Guide Home](./README.md)

If you want to store a Spine object as a file or send it to another service, it eventually has to cross a boundary where it becomes a JSON-compatible payload. This page explains that serialization boundary, and the deserialization boundary that reads it back into a current-schema object.

The core questions in this page are:

- why deterministic serialization matters,
- what the difference is between `to_payload()` and `to_json()`,
- why a deserializer is more than a dict conversion helper,
- what schema version means at the serialization and reading boundary.

If you are new to Spine, it is best to read this page not as "JSON utility documentation" but as "what rules stay intact when a Spine object leaves the system and later comes back in."

## Why Deterministic Serialization Matters

If the same object produces JSON with different key orders each time, the following become harder:

- payload diffs,
- golden fixture tests,
- cache key generation,
- hash calculation,
- reproducibility comparisons.

Spine is designed so that the same object produces stable output.

That property matters for more than formatting aesthetics. Once serialization is stable, you can rely on the idea that "objects with the same meaning produce the same payload," which makes fixture comparison, caching, hashing, and regression testing much easier to build around it.

## Why Serialization Is Its Own Layer

If Spine objects only ever lived inside Python memory, serialization might not stand out very much. But the moment data crosses a system boundary, the situation changes.

- you may need to store it in a file,
- send it to another service,
- compare it against fixtures,
- keep it as a log or audit record.

At that point, what you need is not just "some function that turns it into a dict." You need a boundary that exposes the current canonical contract safely to the outside world. That is the role of Spine's serialization layer.

The deserialization layer works in the opposite direction. It is the entrance through which values from the outside world come back into the Spine contract. If that entrance is loose, raw payload confusion leaks into internal models. If it is strict, uncertainty from external input is blocked at the edge.

## `to_payload()`

`to_payload()` converts a Spine object into a JSON-compatible dict.

```python
from spine import to_payload

payload = to_payload(metric)
```

Conversion rules:

- `StableRef` becomes a `"kind:value"` string,
- dataclasses become dicts keyed by field name,
- tuples become JSON-friendly structures,
- dicts are key-sorted.

So `to_payload()` is the step that turns "a model object" into "a structure that can be stored or transmitted."

More concretely, `to_payload()` has these properties:

- every `StableRef` becomes a string ref,
- dataclasses are recursively expanded by field name,
- tuples become JSON-friendly lists,
- dicts are emitted in sorted key order.

So it is more accurate to think of `to_payload()` not as a generic dump, but as the step that lowers a canonical object into a JSON-compatible canonical shape.

The important point is that this does not flatten Python objects arbitrarily. Spine emits refs, nested dataclasses, tuples, and metadata dicts in the exact shape expected by the current canonical schema. That is why `to_payload()` output can serve directly as the reference shape for fixtures or API payloads.

## `to_json()`

`to_json()` encodes the result of `to_payload()` as a stable JSON string.

```python
from spine import to_json

encoded = to_json(metric)
```

This is especially useful when you need:

- a string payload before storage,
- fixture comparison,
- a stable string for signing or hashing,
- log output.

The current implementation is effectively close to `json.dumps(..., sort_keys=True, separators=(",", ":"))`, so the result is a stable JSON string with sorted keys and no unnecessary whitespace. That makes it more suitable for machine comparison and storage boundaries than for human-readable pretty JSON.

So the concern of `to_json()` is not presentation beauty. It is canonicality. If the same object is serialized again later, you want the same string so that hashing and fixture comparison remain meaningful.

## The Difference Between `to_payload()` And `to_json()`

### `to_payload()`

- returns a dict,
- good for internal programmatic processing,
- easier to manipulate downstream.

### `to_json()`

- returns a string,
- better for transmission, storage, and output,
- gives you a single unambiguous comparison target.

In practice, the natural pattern is usually:

- internal pipelines: `to_payload()`,
- external boundaries or persistence: `to_json()`.

In one line:

- `to_payload()` keeps the structure as Python data,
- `to_json()` fixes that structure into one deterministic string representation.

## Serialization Example

```python
from spine import (
    MetricPayload,
    MetricRecord,
    RecordEnvelope,
    StableRef,
    to_json,
    to_payload,
)

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
    ),
)

payload = to_payload(metric)
encoded = to_json(metric)
```

`payload` becomes a dict roughly like this:

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": null,
    "trace_id": null
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-30T09:08:30Z",
  "operation_context_ref": "op:step-42",
  "payload": {
    "aggregation_scope": "step",
    "metric_key": "training.loss",
    "slice_ref": null,
    "subject_ref": null,
    "summary_basis": null,
    "tags": {},
    "unit": null,
    "value": 0.4821,
    "value_type": "scalar"
  },
  "producer_ref": "scribe.python.local",
  "record_ref": "record:metric-step-42",
  "record_type": "metric",
  "recorded_at": "2026-03-30T09:08:30Z",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

And `encoded = to_json(metric)` returns the same content as a stable JSON string without extra spaces.

So the key point of serialization is this: preserve meaning without losing information, while producing a consistent representation that can cross a system boundary safely.

## What The End-To-End Flow Looks Like

The most practical way to read this page is to think of a Spine object as moving through the following path:

1. application code builds a canonical object,
2. `to_payload()` or `to_json()` creates the external representation,
3. that payload crosses a boundary such as storage, network, or fixture files,
4. later `deserialize_*()` reads it back into a canonical object,
5. at that point the schema, ref, timestamp, and enum contract is checked again.

So serialization and deserialization are not just I/O helpers. They are the round-trip path through which the Spine contract leaves the system and later re-enters it.

## Deserialization

To read payloads in the current schema, use the `deserialize_*` family of functions.

Examples:

- `deserialize_project`
- `deserialize_run`
- `deserialize_artifact_manifest`
- `deserialize_metric_record`
- `deserialize_trace_span_record`

Example:

```python
from spine import deserialize_project

project = deserialize_project(
    {
        "project_ref": "project:nova",
        "name": "NovaVision",
        "created_at": "2026-03-30T09:00:00Z",
        "schema_version": "1.0.0",
    }
)
```

The key difference here is that the input is a raw dict. The deserializer does not trust that raw payload. It only returns a canonical object after parsing refs, building the object, and validating it.

That difference is very important. Values created by `to_payload()` came from inside Spine as canonical payloads. Values accepted by `deserialize_*()` come from the outside world and are untrusted input. So even though the two look like inverse operations, their trust models are completely different.

## What The Deserializer Does

A deserializer is not just a function that turns a dict into a dataclass. Internally it usually does the following:

1. read fields from the raw payload,
2. parse ref strings into `StableRef`,
3. construct the Spine object,
4. run validation,
5. raise `SerializationError` on validation failure.

So the deserializer performs both "reading" and "contract checking."

From the current implementation's perspective, the flow is roughly:

1. required refs are read via `_parse_ref(...)`,
2. if `StableRef.parse(...)` fails, a `SerializationError` is raised immediately,
3. the rest of the fields are assembled into an object in current-schema shape,
4. the validator is called to check contract violations,
5. validation failures are wrapped again as `SerializationError`.

So the deserializer is closer to "current schema boundary enforcement" than to a mere field mapper.

Seen from this angle, it is not just a thin parser plus validator. It is an entrypoint that acts as a gatekeeper for the current schema.

## Deserialization Failure

The following can raise `SerializationError`:

- missing required refs,
- malformed ref strings,
- validation failures,
- values that do not satisfy the current schema.

For example, if a current-schema payload uses `created_at` without a trailing `Z`, deserialization fails.

More broadly, failures usually fall into three groups:

- structural failure: missing required fields or required refs,
- parsing failure: ref strings are not in `kind:value` form,
- contract failure: validation rules are violated.

These are all grouped under `SerializationError` because what matters most is that the boundary failed to read an external payload into a current canonical object.

For example, these are different concrete causes:

- `project_ref` is missing entirely,
- `project_ref` is written as `project-nova` instead of a proper ref string,
- `created_at` lacks `Z` and is rejected by validation.

The causes differ, but from the caller's perspective they all mean the same thing: "this payload could not be safely read as a current-schema object."

## What Schema Version Means

Schema version is extremely important at the serialization and reading boundary.

- is this already a current-schema payload,
- can the current reader consume it directly,
- or should it go through a compatibility path first.

So schema version is the switch that tells you which contract should be used to interpret the payload.

Even if a field name still exists, the meaning may change when schema version changes. That is why Spine favors "check which version contract this is first" over "it looks similar enough, just read it."

This is the most important idea in the whole page. Schema version is not just extra metadata. It chooses the interpretation rules themselves. Even if two JSON shapes look similar, you should not assume they are the same object when the version contract differs.

If you only handle current-schema input, use a deserializer. If you must accept legacy payloads too, consider a compatibility reader.

## The Intuition For Serializer And Deserializer Together

The two layers move in opposite directions, but their roles are not perfectly symmetrical.

- the serializer is the boundary that sends canonical objects outward,
- the deserializer is the boundary that brings external representation inward.

But the inward path is more dangerous, so the deserializer is stricter. When you serialize, you can already assume the object is canonical. Incoming payloads do not deserve that assumption.

So the safest pattern is usually:

- keep objects inside the application,
- use `to_payload()`, `to_json()`, and `deserialize_*()` only at boundaries,
- never pass raw dicts directly into business logic.

If you follow that pattern, internal logic can assume it always receives canonical objects. If raw dicts reach the inside of the system, every call site has to re-think ref parsing, schema version, and optional field interpretation, and the code becomes fragile very quickly.

## When To Use A Deserializer

- when you are confident the input is already in the current schema,
- when contract violations should fail immediately,
- when the ingestion path is tightly controlled.

By contrast, a normal deserializer is not enough when:

- producer versions are mixed,
- older schema payloads still exist in storage,
- you are in a transition period with field renames or timestamp normalization.

So a normal deserializer is close to saying "I only accept the current contract," while a compatibility reader is closer to saying "I will translate older contracts into the current one."

For legacy inputs, see [Compatibility And Migrations](./compatibility-and-migrations.md).

## Recommended Pattern

- keep Spine objects inside the application,
- convert to payload or JSON only at external boundaries,
- do not pass raw dicts straight into business logic; make them go through deserializers first.

## Common Mistakes

### 1. Editing `to_payload()` results as if they were arbitrary dicts

If you start mutating serialized output freely in the middle of the pipeline, the canonical shape expected by deserializers and downstream consumers can drift apart.

This often starts as a shortcut in tests, where people patch small parts of payloads to make fixtures pass quickly. The tests may pass, but data can slowly diverge from the actual schema contract.

### 2. Passing raw dicts directly into business logic

When this happens, schema, version, and ref-format errors move deeper into the system and fail later in much less obvious ways.

This is one of the most common mistakes in libraries that have a serialization boundary. Once boundary validation is skipped, issues that could have been blocked at the entrance start leaking into the codebase as confusing downstream bugs.

### 3. Feeding legacy payloads directly into the current deserializer

It may appear to work partially, but the payload can still be interpreted incorrectly. Inputs like this should go through the compatibility reader path.

### 4. Confusing deterministic JSON with human-friendly pretty JSON

Spine's `to_json()` prioritizes stability and comparability over visual formatting. If you need a prettier display, that is usually better handled in a separate presentation layer.

## Why This Layer Matters In Operations

When the serialization and schema boundary is solid, the following become easier:

- fixture-based regression testing,
- contract stability between producers and consumers,
- long-term re-readability of stored payloads,
- understanding rollout impact during schema changes.

When the boundary is loose, problems like these appear:

- each service emits slightly different payload shapes,
- the same object produces different JSON across runs,
- current and legacy versions mix silently,
- failures happen deep inside the system instead of at the boundary.

So this page is not merely about how to call serialization helpers. It explains one of the most important boundaries where the Spine contract touches the outside world.

## The Core Intuition To Keep From This Page

In very short form:

- `to_payload()` turns a canonical object into a JSON-compatible canonical shape,
- `to_json()` fixes that shape as a deterministic string,
- `deserialize_*()` does not read raw payloads blindly; it parses and validates before lifting them back into canonical objects,
- schema version decides which contract should be used at this boundary.

In one sentence:

"Spine's serialization layer fixes how objects leave the system, and its deserialization layer makes sure they can come back in only through that contract."

## Next Documents

- legacy payload upgrades: [Compatibility And Migrations](./compatibility-and-migrations.md)
- validation rules: [Validation Rules](./validation-rules.md)
