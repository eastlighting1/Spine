# Examples And Tests Results

[User Guide Home](./README.md)

This page is an execution record that summarizes the actual results from running the `examples` folder and the `tests` folder. All commands were executed with `uv run`.

## Targets Executed

### examples

- `examples/basic_training_flow.py`

### tests

- `tests/test_spine_models.py`
- `tests/test_spine_serialization.py`

## Commands Used

Example run:

```powershell
uv run python examples/basic_training_flow.py
```

Test run:

```powershell
uv run pytest tests
```

## Example Run Result

### Target

- `examples/basic_training_flow.py`

### Result

- execution succeeded,
- a total of 5 canonical JSON payloads were printed,
- output order:
  1. `Project`
  2. `Run`
  3. `StructuredEventRecord`
  4. `MetricRecord`
  5. `ArtifactManifest`

### Observations

- every output JSON has a stable key order,
- `extensions` are serialized as empty arrays,
- `correlation_refs` inside `RecordEnvelope` are emitted with explicit `null` values,
- metric payloads include canonical fields such as `aggregation_scope`, `summary_basis`, `tags`, and `unit`,
- artifact payloads include `attributes`, `hash_value`, `size_bytes`, and `stage_execution_ref`.

### Actual Output

```json
{"created_at":"2026-03-30T09:00:00Z","description":"Image classification experiments.","extensions":[],"name":"NovaVision","project_ref":"project:nova","schema_version":"1.0.0","tags":{"team":"research","track":"vision"}}
{"description":null,"ended_at":null,"extensions":[],"name":"baseline-resnet50","project_ref":"project:nova","run_ref":"run:train-20260330-01","schema_version":"1.0.0","started_at":"2026-03-30T09:05:00Z","status":"running"}
{"envelope":{"completeness_marker":"complete","correlation_refs":{"session_id":null,"trace_id":null},"degradation_marker":"none","extensions":[],"observed_at":"2026-03-30T09:07:00Z","operation_context_ref":null,"producer_ref":"scribe.python.local","record_ref":"record:event-epoch-1-start","record_type":"structured_event","recorded_at":"2026-03-30T09:07:00Z","run_ref":"run:train-20260330-01","schema_version":"1.0.0","stage_execution_ref":"stage:train"},"payload":{"attributes":{},"event_key":"training.epoch.started","level":"info","message":"Epoch 1 started.","origin_marker":"explicit_capture","subject_ref":null}}
{"envelope":{"completeness_marker":"complete","correlation_refs":{"session_id":null,"trace_id":null},"degradation_marker":"none","extensions":[],"observed_at":"2026-03-30T09:08:30Z","operation_context_ref":"op:step-42","producer_ref":"scribe.python.local","record_ref":"record:metric-step-42","record_type":"metric","recorded_at":"2026-03-30T09:08:30Z","run_ref":"run:train-20260330-01","schema_version":"1.0.0","stage_execution_ref":"stage:train"},"payload":{"aggregation_scope":"step","metric_key":"training.loss","slice_ref":null,"subject_ref":null,"summary_basis":null,"tags":{"device":"cuda:0"},"unit":"ratio","value":0.4821,"value_type":"scalar"}}
{"artifact_kind":"checkpoint","artifact_ref":"artifact:checkpoint-epoch-1","attributes":{"dtype":"float16","framework":"pytorch"},"created_at":"2026-03-30T09:20:00Z","extensions":[],"hash_value":"sha256:abc123","location_ref":"file://artifacts/checkpoints/epoch_1.ckpt","producer_ref":"scribe.python.local","run_ref":"run:train-20260330-01","schema_version":"1.0.0","size_bytes":184223744,"stage_execution_ref":"stage:train"}
```

## Test Run Result

### Command

```powershell
uv run pytest tests
```

### Summary

- execution succeeded,
- 13 tests were collected,
- 13 tests passed,
- 0 failures,
- elapsed time: `0.03s`.

### Detailed Test Output

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\eastl\MLObservability\Spine
configfile: pyproject.toml
collected 13 items

tests\test_spine_models.py ......                                        [ 46%]
tests\test_spine_serialization.py .......                                [100%]

============================= 13 passed in 0.03s ==============================
```

### Interpretation

- both model-layer validation tests and serialization tests passed,
- based on the current example and test suite, canonical model creation, validation, and serialization flows are working as expected,
- fixture-based serialization regressions do not appear to be broken.

## Conclusion

At the current state, both `examples` and `tests` run successfully.

- example: `1/1` succeeded,
- tests: `13/13` passed.

Spine's basic usage flow and canonical serialization path are operating stably in the current repository state.
