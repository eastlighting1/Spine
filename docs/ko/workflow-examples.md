# 워크플로 예제

[사용자 가이드 홈](./README.md)

Spine을 처음 프로젝트에 넣을 때 가장 막막한 부분은 보통 "객체를 어떤 순서로 만들면 되지?"입니다. 이 문서는 그 질문에 답하기 위한 워크플로 예제 문서입니다.

필드 정의를 외우기보다, `Project -> Run -> Stage -> Record -> Artifact` 흐름으로 객체를 조립하는 감각을 먼저 잡는 데 초점을 두고 읽으면 좋습니다.

## 기본 학습 플로우

프로젝트에 포함된 기본 예제는 [`examples/basic_training_flow.py`](C:/Users/eastl/MLObservability/Spine/examples/basic_training_flow.py)입니다.

흐름:

1. `Project` 생성
2. `Run` 생성
3. `StageExecution` 생성
4. `StructuredEventRecord` 생성
5. `MetricRecord` 생성
6. `ArtifactManifest` 생성

이 순서는 우연이 아니라 Spine의 모델 계층을 그대로 반영합니다.

- 먼저 컨텍스트를 만들고
- 그 컨텍스트 안에서 레코드를 만들고
- 마지막에 결과물과 관계를 붙이는 구조입니다

이 흐름은 Spine의 거의 모든 사용 사례에 반복됩니다. 학습이든 평가든 배포든, 보통은 "맥락 -> 관측 -> 결과물" 순서가 가장 안정적입니다.

## 단계별 예시

```python
from spine import (
    ArtifactManifest,
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    Run,
    StableRef,
    StageExecution,
    StructuredEventPayload,
    StructuredEventRecord,
    validate_artifact_manifest,
    validate_metric_record,
    validate_project,
    validate_run,
    validate_stage_execution,
    validate_structured_event_record,
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

stage = StageExecution(
    stage_execution_ref=StableRef("stage", "train"),
    run_ref=run.run_ref,
    stage_name="train",
    status="running",
    started_at="2026-03-30T09:06:00Z",
)
validate_stage_execution(stage).raise_for_errors()

event = StructuredEventRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "event-epoch-1-start"),
        record_type="structured_event",
        recorded_at="2026-03-30T09:07:00Z",
        observed_at="2026-03-30T09:07:00Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=stage.stage_execution_ref,
        operation_context_ref=None,
    ),
    payload=StructuredEventPayload(
        event_key="training.epoch.started",
        level="info",
        message="Epoch 1 started.",
    ),
)
validate_structured_event_record(event).raise_for_errors()

metric = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-step-42"),
        record_type="metric",
        recorded_at="2026-03-30T09:08:30Z",
        observed_at="2026-03-30T09:08:30Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=stage.stage_execution_ref,
        operation_context_ref=StableRef("op", "step-42"),
    ),
    payload=MetricPayload(
        metric_key="training.loss",
        value=0.4821,
        value_type="scalar",
    ),
)
validate_metric_record(metric).raise_for_errors()

artifact = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=run.run_ref,
    stage_execution_ref=stage.stage_execution_ref,
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
    hash_value="sha256:abc123",
    size_bytes=184223744,
)
validate_artifact_manifest(artifact).raise_for_errors()
```

이 예제를 아주 짧게 다시 쓰면 다음과 같습니다.

1. 프로젝트와 실행 컨텍스트를 만든다
2. stage 안에서 event와 metric을 남긴다
3. 실행 결과 artifact를 등록한다
4. 각 단계에서 validation으로 계약 위반을 바로 막는다

즉 예제의 본질은 코드 조각 나열이 아니라, Spine을 "실행을 구조화한 뒤 사실을 붙이는 방식"으로 쓰고 있다는 점입니다.

## 이 예제를 어떻게 읽어야 하나

### 1. 컨텍스트가 먼저다

레코드부터 만들지 않고 `Project -> Run -> StageExecution`을 먼저 만드는 이유는, 이후의 모든 레코드와 artifact가 이 컨텍스트를 참조하기 때문입니다.

### 2. envelope가 맥락을 잇는다

`MetricRecord`와 `StructuredEventRecord`는 내용은 다르지만 같은 run/stage를 참조합니다. 이 연결점이 `RecordEnvelope`입니다.

### 3. artifact는 결과물로 붙는다

artifact는 독립 객체처럼 보이지만, 실제로는 같은 run/stage의 결과물입니다.

이 세 관점을 합치면 Spine 조립의 기본 원리가 보입니다.

- context object는 이후 객체들이 기대는 뼈대이고
- record는 그 뼈대 위에 붙는 관측 사실이며
- artifact는 실행이 남긴 결과물입니다

## 예제를 읽는 포인트

- 컨텍스트 모델은 먼저 만들고 재사용합니다.
- 레코드는 envelope로 실행 맥락을 연결합니다.
- artifact는 run/stage와 연결해 두어야 이후 lineage 분석이 쉬워집니다.
- 각 단계에서 즉시 validation을 수행하는 패턴이 가장 안전합니다.

## 실제 코드에서는 보통 어떻게 나뉘나

실무 코드에서는 이 예제가 보통 한 함수 안에 그대로 들어가진 않습니다. 대신 대략 다음처럼 역할이 나뉩니다.

- run bootstrap 단계에서 `Project`, `Run`
- stage 진입 시점에서 `StageExecution`
- step/request 단위에서 event, metric, trace
- 완료 시점에서 artifact 및 lineage

즉 예제를 "한 번에 다 만든다"기보다, 실행 생애주기 전반에 걸쳐 Spine 객체를 점진적으로 조립하는 방식으로 읽는 편이 좋습니다.

많은 경우 실제 시스템 코드는 다음처럼 흩어져 있습니다.

- scheduler나 runner가 `Run`을 시작하고
- stage executor가 `StageExecution`을 만들며
- trainer나 service handler가 record를 남기고
- artifact writer가 결과물을 등록합니다

즉 예제는 이 분산된 책임을 한 화면에 압축해 놓은 요약본이라고 보면 이해가 쉽습니다.

## 실무에서 흔한 조립 순서

Spine을 실제 producer 코드에 넣을 때는 대개 다음 순서가 자연스럽습니다.

1. run 시작 시 `Project`, `Run` 확인 또는 생성
2. stage 시작 시 `StageExecution` 생성
3. step/request 단위가 필요하면 `OperationContext` 생성
4. event/metric/trace 기록
5. artifact 생성
6. 필요하면 lineage 연결

즉, Spine은 "실행을 구조화한 뒤 관측을 붙이는 방식"으로 쓰는 것이 자연스럽습니다.

## 시나리오별로 보면 어떻게 달라지나

### 1. 학습 파이프라인

현재 예제가 가장 가깝게 보여 주는 경우입니다.

- `Project`
- `Run`
- `StageExecution(train)`
- epoch/step event
- loss/throughput metric
- checkpoint artifact

이 경우 핵심은 반복 실행과 결과물 추적입니다.

### 2. 평가 파이프라인

평가에서는 보통 다음이 자연스럽습니다.

- 기존 model artifact 또는 run 맥락 확인
- `StageExecution(evaluate)` 생성
- 평가 시작/완료 event
- accuracy, f1, latency 같은 metric
- report artifact 생성

즉 학습과 구조는 비슷하지만, 산출물의 종류와 metric 해석이 달라집니다.

### 3. 온라인 추론 흐름

추론에서는 보통 객체 수명이 더 짧고 request 단위 맥락이 중요합니다.

- 장기 run 또는 서비스 run 맥락
- request/step 단위 `OperationContext`
- 요청 event, latency metric, trace span
- 필요하면 결과 report나 drift signal artifact

이 경우엔 stage보다 operation context와 correlation 정보가 더 중요해지는 경우가 많습니다.

즉 같은 Spine이라도 시나리오에 따라 강조점이 달라집니다.

## 두 번째 짧은 예시: request 중심 추론 흐름

학습 예제와 대비해서 보면, 온라인 추론은 보통 operation context와 짧은 시간 구간이 더 중요합니다.

```python
from spine import (
    MetricPayload,
    MetricRecord,
    OperationContext,
    RecordEnvelope,
    Run,
    StableRef,
    TraceSpanPayload,
    TraceSpanRecord,
    validate_metric_record,
    validate_operation_context,
    validate_run,
    validate_trace_span_record,
)

run = Run(
    run_ref=StableRef("run", "serving-20260330"),
    project_ref=StableRef("project", "nova"),
    name="online-inference",
    status="running",
    started_at="2026-03-30T09:00:00Z",
)
validate_run(run).raise_for_errors()

op = OperationContext(
    operation_context_ref=StableRef("op", "request-0001"),
    run_ref=run.run_ref,
    stage_execution_ref=None,
    operation_name="predict",
    observed_at="2026-03-30T09:10:00Z",
)
validate_operation_context(op).raise_for_errors()

trace = TraceSpanRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "trace-request-0001"),
        record_type="trace_span",
        recorded_at="2026-03-30T09:10:01Z",
        observed_at="2026-03-30T09:10:01Z",
        producer_ref="gateway.inference.local",
        run_ref=run.run_ref,
        stage_execution_ref=None,
        operation_context_ref=op.operation_context_ref,
    ),
    payload=TraceSpanPayload(
        span_id="span-0001",
        trace_id="trace-0001",
        parent_span_id=None,
        span_name="predict.request",
        started_at="2026-03-30T09:10:00Z",
        ended_at="2026-03-30T09:10:01Z",
        status="ok",
        span_kind="request",
    ),
)
validate_trace_span_record(trace).raise_for_errors()

latency = MetricRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "metric-request-0001-latency"),
        record_type="metric",
        recorded_at="2026-03-30T09:10:01Z",
        observed_at="2026-03-30T09:10:01Z",
        producer_ref="gateway.inference.local",
        run_ref=run.run_ref,
        stage_execution_ref=None,
        operation_context_ref=op.operation_context_ref,
    ),
    payload=MetricPayload(
        metric_key="inference.latency",
        value=152,
        value_type="integer",
        unit="ms",
    ),
)
validate_metric_record(latency).raise_for_errors()
```

이 예시가 보여 주는 포인트는 다음과 같습니다.

- 장기 서비스 run 하나 아래에 request 단위 operation context를 둔다
- 같은 request에 속한 trace와 metric을 같은 `operation_context_ref`로 묶는다
- stage가 없어도 Spine 조립은 여전히 자연스럽다

즉 Spine은 학습 파이프라인에만 맞춘 모델이 아니라, request 중심 시스템에도 같은 원리로 적용됩니다.

## 예제가 일부러 생략하는 것

이 문서는 조립 순서를 설명하는 데 집중하기 때문에, 일부 요소는 단순화되어 있습니다.

- `OperationContext` 생성 흐름
- `TraceSpanRecord`
- `LineageEdge` / `ProvenanceRecord`
- extension 부착
- compatibility reader 경로

이 요소들이 중요하지 않다는 뜻이 아니라, 기본 예제의 진입 장벽을 낮추기 위해 핵심 흐름만 먼저 보여 주는 것입니다.

반대로 말하면, 실제 시스템에 Spine을 넣을 때는 이 생략된 부분을 어떤 순서로 도입할지 정하는 것도 중요합니다.

보통은:

1. context + 핵심 metric/event부터 시작하고
2. artifact를 붙이고
3. 필요해지면 operation context와 trace를 넣고
4. 마지막에 lineage, extension, compatibility 같은 고급 경로를 붙이는 편이 자연스럽습니다

즉 Spine 도입도 대개 한 번에 완성하는 것이 아니라 단계적으로 깊어집니다.

## 좋은 producer 코드 패턴

Spine을 실제 producer에 넣을 때는 다음 패턴이 보통 안정적입니다.

### 작은 helper로 context 재사용

`run_ref`, `stage_execution_ref`, `producer_ref`를 반복해서 쓰게 되므로, envelope 생성 helper나 artifact 생성 helper를 두면 코드가 훨씬 깔끔해집니다.

### 객체를 만든 자리에서 바로 validation

실패를 뒤로 미루지 않으면, 어느 단계에서 계약이 깨졌는지 찾기 쉬워집니다.

### 외부 경계에서만 serialization

내부에서는 가능하면 Spine object를 유지하고, 저장/전송 직전에만 `to_payload()` 또는 `to_json()`을 적용하는 편이 안전합니다.

### producer 책임을 나누되 ref는 일관되게 재사용

여러 모듈이 함께 record를 만들더라도 `run_ref`, `stage_execution_ref`, `operation_context_ref`를 같은 값으로 재사용해야 나중에 분석이 연결됩니다. Spine 조립에서 가장 흔한 실패는 "객체는 많지만 서로 맥락이 끊긴 상태"입니다.

## 이 문서를 읽을 때 잡아야 할 핵심 직관

아주 짧게 정리하면 다음과 같습니다.

- Spine 조립은 보통 `Project -> Run -> Stage -> Record/Artifact` 순서로 읽는다
- context를 먼저 만들고 record와 artifact는 그 맥락에 붙인다
- validation은 각 단계에서 바로 수행하는 편이 안전하다
- 실제 시스템에서는 이 흐름이 학습, 평가, 추론 시나리오마다 조금씩 변주된다

## 예제 다음 단계

이 예제를 이해했다면 다음으로는:

- 타입 의미를 더 깊게 보려면 [컨텍스트 모델](./context-models.md), [관측 레코드](./observability-records.md), [산출물과 계보](./artifacts-and-lineage.md)
- payload 변환 흐름을 보려면 [직렬화와 스키마](./serialization-and-schema.md)
- 구버전 입력 처리를 보려면 [호환성 및 마이그레이션](./compatibility-and-migrations.md)
