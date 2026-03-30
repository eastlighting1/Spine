# Examples And Tests Results

[사용자 가이드 홈](./README.md)

이 문서는 `examples` 폴더와 `tests` 폴더를 실제로 실행한 결과를 정리한 실행 기록입니다. 실행은 `uv run` 기준으로 수행했습니다.

## 실행 대상

### examples

- `examples/basic_training_flow.py`

### tests

- `tests/test_spine_models.py`
- `tests/test_spine_serialization.py`

## 실행 명령

예제 실행:

```powershell
uv run python examples/basic_training_flow.py
```

테스트 실행:

```powershell
uv run pytest tests
```

## examples 실행 결과

### 대상

- `examples/basic_training_flow.py`

### 결과

- 실행 성공
- 총 5개의 canonical JSON payload 출력
- 출력 순서:
  1. `Project`
  2. `Run`
  3. `StructuredEventRecord`
  4. `MetricRecord`
  5. `ArtifactManifest`

### 관찰 포인트

- 모든 출력 JSON은 key 순서가 안정적으로 정렬되어 있음
- `extensions`는 빈 배열로 직렬화됨
- `RecordEnvelope` 안의 `correlation_refs`는 `null` 값 포함 상태로 출력됨
- metric payload에는 `aggregation_scope`, `summary_basis`, `tags`, `unit` 같은 canonical 필드가 함께 포함됨
- artifact payload에는 `attributes`, `hash_value`, `size_bytes`, `stage_execution_ref`가 모두 포함됨

### 실제 출력

```json
{"created_at":"2026-03-30T09:00:00Z","description":"Image classification experiments.","extensions":[],"name":"NovaVision","project_ref":"project:nova","schema_version":"1.0.0","tags":{"team":"research","track":"vision"}}
{"description":null,"ended_at":null,"extensions":[],"name":"baseline-resnet50","project_ref":"project:nova","run_ref":"run:train-20260330-01","schema_version":"1.0.0","started_at":"2026-03-30T09:05:00Z","status":"running"}
{"envelope":{"completeness_marker":"complete","correlation_refs":{"session_id":null,"trace_id":null},"degradation_marker":"none","extensions":[],"observed_at":"2026-03-30T09:07:00Z","operation_context_ref":null,"producer_ref":"scribe.python.local","record_ref":"record:event-epoch-1-start","record_type":"structured_event","recorded_at":"2026-03-30T09:07:00Z","run_ref":"run:train-20260330-01","schema_version":"1.0.0","stage_execution_ref":"stage:train"},"payload":{"attributes":{},"event_key":"training.epoch.started","level":"info","message":"Epoch 1 started.","origin_marker":"explicit_capture","subject_ref":null}}
{"envelope":{"completeness_marker":"complete","correlation_refs":{"session_id":null,"trace_id":null},"degradation_marker":"none","extensions":[],"observed_at":"2026-03-30T09:08:30Z","operation_context_ref":"op:step-42","producer_ref":"scribe.python.local","record_ref":"record:metric-step-42","record_type":"metric","recorded_at":"2026-03-30T09:08:30Z","run_ref":"run:train-20260330-01","schema_version":"1.0.0","stage_execution_ref":"stage:train"},"payload":{"aggregation_scope":"step","metric_key":"training.loss","slice_ref":null,"subject_ref":null,"summary_basis":null,"tags":{"device":"cuda:0"},"unit":"ratio","value":0.4821,"value_type":"scalar"}}
{"artifact_kind":"checkpoint","artifact_ref":"artifact:checkpoint-epoch-1","attributes":{"dtype":"float16","framework":"pytorch"},"created_at":"2026-03-30T09:20:00Z","extensions":[],"hash_value":"sha256:abc123","location_ref":"file://artifacts/checkpoints/epoch_1.ckpt","producer_ref":"scribe.python.local","run_ref":"run:train-20260330-01","schema_version":"1.0.0","size_bytes":184223744,"stage_execution_ref":"stage:train"}
```

## tests 실행 결과

### 실행 명령

```powershell
uv run pytest tests
```

### 결과 요약

- 실행 성공
- 총 13개 테스트 수집
- 총 13개 테스트 통과
- 실패 0
- 소요 시간: `0.03s`

### 테스트 세부 결과

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

### 해석

- 모델 계층 검증 테스트와 직렬화 테스트가 모두 통과함
- 현재 예제와 테스트 기준으로 canonical model 생성, validation, serialization 경로는 정상 동작함
- fixture 기반 serialization 관련 회귀가 깨지지 않은 상태로 보임

## 결론

현재 기준으로 `examples`와 `tests`는 모두 정상 실행됩니다.

- example: `1/1` 성공
- tests: `13/13` 통과

Spine의 기본 사용 흐름과 canonical serialization 경로는 현 상태에서 안정적으로 동작하고 있습니다.
