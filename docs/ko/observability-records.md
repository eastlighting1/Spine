# 관측 레코드

[사용자 가이드 홈](./README.md)

Spine에서 실제로 가장 자주 만들게 되는 객체는 대개 event, metric, trace record입니다. 이 문서는 세 타입을 어떻게 구분하고 어떤 공통 구조 위에 올려야 하는지 설명합니다.

이 문서의 핵심은 다음 두 가지입니다.

1. 모든 레코드는 `RecordEnvelope + Payload` 구조를 가진다.
2. event, metric, trace는 서로 다른 내용을 담지만 같은 맥락 모델 위에서 해석된다.

이 문서를 읽고 나면 다음 정도는 바로 판단할 수 있어야 합니다.

- event, metric, trace를 언제 각각 써야 하는가
- envelope가 payload와 어떻게 역할을 나누는가
- 같은 run/stage/op 안에서 레코드가 어떻게 연결되는가
- 관측 레코드를 잘못 모델링하면 어떤 문제가 생기는가

## 왜 관측 레코드가 별도 계층인가

컨텍스트 모델은 "어디에서 무슨 실행이 있었는가"를 설명합니다. 반면 관측 레코드는 "그 실행 중 무엇을 관측했는가"를 설명합니다.

즉:

- 컨텍스트: 배경
- 레코드: 실제 관측 사실

이 둘을 분리하면 다음이 쉬워집니다.

- 같은 run에 속한 event와 metric을 함께 보기
- 같은 stage에서 나온 trace와 metric 비교
- 공통 메타데이터를 재사용하면서 레코드 타입을 늘리기
- ingestion 레이어에서 공통 규칙을 적용하기

Spine은 이 분리를 통해 "어떤 데이터가 있는가"와 "그 데이터가 어디에 속하는가"를 따로 모델링합니다.

## 레코드를 하나의 객체로 합치지 않는 이유

처음에는 다음처럼 하나의 느슨한 레코드 타입으로 모든 것을 담고 싶어질 수 있습니다.

```json
{
  "type": "metric",
  "name": "training.loss",
  "value": 0.4821,
  "run": "train-20260330-01",
  "timestamp": "2026-03-30T09:08:30Z"
}
```

하지만 시간이 지나면 금방 문제가 생깁니다.

- event에는 `value`가 없음
- trace에는 `started_at`/`ended_at`가 필요함
- 공통 필드 이름이 점점 늘어남
- 같은 의미의 필드가 타입마다 조금씩 다르게 생김

Spine은 이 혼란을 피하기 위해 공통 부분은 envelope로 빼고, 타입별 의미는 payload로 나눕니다.

## 공통 구조: RecordEnvelope + Payload

Spine의 레코드는 모두 다음 형태를 따릅니다.

```text
RecordEnvelope
  + Payload
```

이 구조의 목적은 메타데이터와 실제 관측 내용을 분리하는 것입니다.

- envelope: 언제, 어디서, 누가 기록했는가
- payload: 실제로 무엇을 관측했는가

이 구조는 단순한 코드 스타일이 아니라, 관측 데이터의 일관성과 확장성을 위한 핵심 설계입니다.

## RecordEnvelope

모든 레코드가 공유하는 메타데이터 구조입니다.

주요 필드:

- `record_ref`
- `record_type`
- `recorded_at`
- `observed_at`
- `producer_ref`
- `run_ref`
- `stage_execution_ref`
- `operation_context_ref`
- `correlation_refs`
- `completeness_marker`
- `degradation_marker`
- `schema_version`
- `extensions`

## envelope가 담당하는 역할

envelope는 payload를 둘러싼 사실을 담습니다.

- 어떤 producer가 만들었는가
- 어느 실행에 속하는가
- 어느 stage나 operation에 속하는가
- 실제 관측과 기록 시각이 어떻게 다른가
- 데이터 품질 상태는 어떤가

즉, envelope는 "payload를 어떻게 읽어야 하는가"를 알려주는 컨텍스트 메타데이터입니다.

같은 payload라도 envelope가 달라지면 해석은 크게 달라질 수 있습니다.

예:

- 같은 `training.loss=0.48`이라도
  - run A의 값인지
  - run B의 값인지
  - train stage인지 evaluate stage인지
  - step별 값인지 epoch 집계값인지

는 전혀 다른 의미를 가집니다.

## `record_ref`와 `record_type`

### `record_ref`

각 레코드의 식별자입니다. 일반적으로 `StableRef("record", "...")` 형태를 사용합니다.

예:

- `record:event-epoch-1-start`
- `record:metric-step-42`
- `record:trace-forward-001`

### `record_type`

이 레코드의 payload를 어떻게 읽어야 하는지를 나타냅니다.

현재 주요 값:

- `structured_event`
- `metric`
- `trace_span`

Spine validation은 레코드 객체 종류와 envelope의 `record_type`이 일치하는지 검사합니다.

예:

- `MetricRecord`인데 `record_type="structured_event"`이면 실패

## `recorded_at`와 `observed_at`

핵심 구분:

- `observed_at`: 실제 현상이 발생한 시점
- `recorded_at`: 해당 현상이 시스템에 기록된 시점

현재 validation은 `recorded_at >= observed_at`를 기대합니다.

둘이 분리되는 대표 사례:

- 비동기 배치 수집
- 버퍼 flush
- 재시도 후 기록
- sidecar exporter
- collector가 뒤늦게 업로드함

이 두 필드를 분리하면 다음이 가능해집니다.

- ingestion delay 측정
- 실제 시간축과 저장 시간축 분리
- 늦게 도착한 데이터도 올바르게 재배치

즉, 이 둘은 비슷한 타임스탬프가 아니라 서로 다른 시간 의미를 가집니다.

## `producer_ref`

`producer_ref`는 어떤 시스템/라이브러리/에이전트가 이 레코드를 만들었는지 나타냅니다.

예:

- `scribe.python.local`
- `sdk.python.local`
- `collector.inference.gateway`

이 필드는 디버깅 시 꽤 중요합니다. 같은 레코드 타입이라도 producer마다 품질과 의미 차이가 있을 수 있기 때문입니다.

예:

- 어떤 producer는 step 단위 metric을 남기고
- 어떤 producer는 epoch 집계값만 남길 수 있음

## `run_ref`, `stage_execution_ref`, `operation_context_ref`

이 세 필드는 레코드가 어느 실행 맥락에 속하는지 결정합니다.

- `run_ref`: 어느 run인가
- `stage_execution_ref`: 어느 stage인가
- `operation_context_ref`: 어느 세부 작업인가

이 연결 덕분에 다음 같은 분석이 쉬워집니다.

- 같은 run의 모든 metric 조회
- train stage에서 난 error event만 모으기
- `op:step-42`에 해당하는 trace와 metric 함께 보기

이 필드를 비워 두면 레코드 자체는 남더라도 운영적 해석 가능성이 크게 떨어집니다.

## CorrelationRefs

외부 추적 체계와 연결하기 위한 보조 필드입니다.

구성:

- `trace_id`
- `session_id`

예를 들어 추론 요청 단위 트레이스를 외부 tracing system과 맞추고 싶을 때 유용합니다.

이 필드가 있으면 Spine 내부 레코드와 외부 추적 id를 연결할 수 있습니다.

특히 다음 경우에 유용합니다.

- OpenTelemetry trace와 내부 metric 연동
- API session 단위 grouping
- 동일 사용자 세션의 event/metric 묶기

실무에서는 envelope의 `run/stage/op` 맥락이 Spine 내부 구조를 연결하고, `correlation_refs`가 외부 추적 체계와의 접점을 만들어 준다고 보면 이해하기 쉽습니다.

예를 들어:

- `run_ref`, `stage_execution_ref`로 "이 레코드가 어느 실행에 속하는가"를 추적하고
- `correlation_refs.trace_id`로 외부 tracing backend의 span/trace와 맞추고
- `correlation_refs.session_id`로 같은 사용자 요청 흐름을 다시 묶을 수 있습니다

즉 `correlation_refs`는 없어도 레코드는 성립하지만, 분산 시스템에서 Spine 바깥의 관측 도구와 연결하려면 사실상 매우 중요한 연결 축입니다.

## completeness_marker

허용값:

- `complete`
- `partial`
- `unknown`

이 값은 데이터가 완전한지, 일부만 수집됐는지, 상태가 불명확한지를 표현합니다.

예:

- 일부 필드만 수집된 metric
- 다운스트림 exporter가 일부 payload를 생략한 event
- trace 연속성은 있으나 일부 속성이 누락된 span

누가 이 값을 세팅하는가를 실무적으로 보면:

- producer가 처음부터 "일부만 캡처했다"는 사실을 아는 경우 producer가 직접 표시할 수 있고
- collector나 compatibility layer가 후처리 과정에서 일부 손실을 감지했다면 그 단계에서 표시할 수도 있습니다

중요한 점은 이 값이 "payload가 비어 있다"는 뜻이 아니라, payload를 해석할 때 완전성에 주의를 기울여야 한다는 신호라는 점입니다.

## degradation_marker

허용값:

- `none`
- `partial_failure`
- `capture_gap`
- `compatibility_upgrade`

이 값은 수집 과정에서 데이터 품질 저하가 있었는지를 나타냅니다.

예:

- collector 내부 오류로 속성이 일부 빠짐
- trace 연속성이 일부 깨짐
- compatibility reader를 거쳐 현재 스키마로 업그레이드됨

이 두 marker는 "값은 존재하지만 품질은 완전하지 않을 수 있다"는 현실을 모델에 반영합니다.

운영 관점에서는 이 값을 단순 메타데이터로 두지 말고 실제 필터 조건으로 쓰는 편이 좋습니다.

예:

- `degradation_marker != "none"` 인 레코드만 따로 모아 수집 품질 이상을 추적
- `completeness_marker == "partial"` 인 metric은 집계에서 제외하거나 별도 표기
- `compatibility_upgrade`가 자주 보이면 아직 남아 있는 구버전 producer를 점검

## StructuredEventRecord

이벤트성 로그를 구조화해 담는 타입입니다.

payload 필드:

- `event_key`
- `level`
- `message`
- `subject_ref`
- `attributes`
- `origin_marker`

허용 level:

- `debug`
- `info`
- `warning`
- `error`
- `critical`

예시:

```python
from spine import RecordEnvelope, StableRef, StructuredEventPayload, StructuredEventRecord

event = StructuredEventRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "event-epoch-1-start"),
        record_type="structured_event",
        recorded_at="2026-03-30T09:07:00Z",
        observed_at="2026-03-30T09:07:00Z",
        producer_ref="scribe.python.local",
        run_ref=StableRef("run", "train-20260330-01"),
        stage_execution_ref=StableRef("stage", "train"),
        operation_context_ref=None,
    ),
    payload=StructuredEventPayload(
        event_key="training.epoch.started",
        level="info",
        message="Epoch 1 started.",
        attributes={"epoch": 1},
    ),
)
```

fixture에 가까운 payload 형태로 보면 다음과 같습니다.

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": "session-train-01",
    "trace_id": "trace-train-01"
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-30T09:07:00Z",
  "operation_context_ref": null,
  "payload": {
    "attributes": {
      "epoch": 1
    },
    "event_key": "training.epoch.started",
    "level": "info",
    "message": "Epoch 1 started.",
    "origin_marker": "explicit_capture",
    "subject_ref": null
  },
  "producer_ref": "scribe.python.local",
  "record_ref": "record:event-epoch-1-start",
  "record_type": "structured_event",
  "recorded_at": "2026-03-30T09:07:00Z",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

### event가 적합한 경우

- 상태 전이 알림
- 경고/오류 이벤트
- 사람이 읽을 수 있는 중요한 상태 메시지
- 운영상 의미 있는 사실 기록

적합한 예:

- `training.epoch.started`
- `dataset.load.failed`
- `model.registration.completed`
- `drift.alert.triggered`

덜 적합한 예:

- 단순 숫자형 측정값
- span duration 같은 시간 구간 정보

### event payload를 어떻게 써야 하나

#### `event_key`

기계적으로 분류 가능한 이벤트 이름입니다. 검색/분류/집계에 적합해야 합니다.

#### `message`

사람이 읽을 수 있는 설명입니다.

#### `attributes`

이벤트에 붙는 보조 정보입니다.

예:

```python
attributes={"epoch": 1, "worker": "trainer-0"}
```

실무적으로는 `event_key`는 구조적이고, `message`는 설명적이며, `attributes`는 세부 정보를 담는 편이 가장 좋습니다.

#### `origin_marker`

이 event가 어떻게 포착되었는지를 나타내는 힌트입니다.

예를 들어:

- 애플리케이션 코드가 명시적으로 남긴 이벤트인지
- 다른 로그/시스템 상태에서 유도된 이벤트인지

같은 event라도 생성 방식이 다르면 신뢰도와 해석 방식이 달라질 수 있기 때문에, origin 정보는 운영 분석에서 의외로 유용합니다.

## MetricRecord

수치형 관측값을 표현합니다.

payload 필드:

- `metric_key`
- `value`
- `value_type`
- `unit`
- `aggregation_scope`
- `subject_ref`
- `slice_ref`
- `tags`
- `summary_basis`

예시:

```python
from spine import MetricPayload, MetricRecord, RecordEnvelope, StableRef

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
        unit="ratio",
        aggregation_scope="step",
        tags={"device": "cuda:0"},
        summary_basis="raw_step_observation",
    ),
)
```

fixture 기반 payload 예시:

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": null,
    "trace_id": "trace-train-01"
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-29T10:16:02Z",
  "operation_context_ref": "op:step-42",
  "payload": {
    "aggregation_scope": "step",
    "metric_key": "training.loss",
    "slice_ref": null,
    "subject_ref": null,
    "summary_basis": "raw_step_observation",
    "tags": {
      "device": "cuda:0"
    },
    "unit": "ratio",
    "value": 0.4821,
    "value_type": "scalar"
  },
  "producer_ref": "sdk.python.local",
  "record_ref": "record:metric-step-42",
  "record_type": "metric",
  "recorded_at": "2026-03-29T10:16:02Z",
  "run_ref": "run:run-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

### metric이 적합한 경우

- loss, accuracy, latency, throughput
- 자원 사용량
- 평가 점수
- drift score, calibration error, queue depth
- success ratio, error count

### MetricPayload 안의 세부 필드를 어떻게 보나

#### `metric_key`

metric의 의미를 나타내는 이름입니다.

예:

- `training.loss`
- `gpu.memory.used`
- `inference.latency.p95`

#### `value`

실제 숫자입니다.

#### `value_type`

이 값이 어떤 방식으로 해석돼야 하는지를 나타냅니다.

현재 허용값:

- `scalar`
- `integer`
- `float`

#### `unit`

단위를 명시합니다.

예:

- `ratio`
- `ms`
- `bytes`

#### `aggregation_scope`

이 값이 어떤 범위에서 계산되었는지를 나타냅니다.

예:

- step
- batch
- epoch
- run

#### `tags`

추가 분류 정보입니다.

예:

```python
tags={"device": "cuda:0", "split": "validation"}
```

#### `summary_basis`

값이 어떤 방식으로 만들어졌는지를 설명합니다.

예:

- raw step observation
- batch mean
- epoch aggregate

즉, metric은 단순 숫자가 아니라 "어떤 방식으로 관측된 숫자인가"를 설명하는 구조입니다.

## TraceSpanRecord

시간 구간(span)을 표현하는 타입입니다.

payload 필드:

- `span_id`
- `trace_id`
- `parent_span_id`
- `span_name`
- `started_at`
- `ended_at`
- `status`
- `span_kind`
- `attributes`
- `linked_refs`

언제 적합한가:

- 모델 호출 latency 추적
- 외부 API 호출 분석
- pipeline 단계별 병목 분석
- request 단위 실행 경로 분석
- parent-child 구조가 중요한 실행 흐름

validation은 `started_at <= ended_at`를 검사합니다.

### trace가 적합한 경우

- "얼마나 오래 걸렸는가"가 핵심일 때
- parent-child 호출 구조가 중요할 때
- 단일 값보다 시간 구간이 중요할 때

예:

- `model.forward`
- `feature.lookup`
- `http.request`
- `vector.search`

### TraceSpanPayload의 핵심 필드

#### `span_id`

현재 span 식별자

#### `trace_id`

전체 trace 식별자

#### `parent_span_id`

상위 span과의 연결

#### `started_at`, `ended_at`

시간 구간 정의

#### `span_kind`

span의 성격을 나타냄

예:

- model call
- network call
- internal stage

#### `linked_refs`

추가적인 참조 연결

이 구조는 단순 duration metric 하나보다 훨씬 풍부한 실행 정보를 담을 수 있습니다.

예시:

```python
from spine import RecordEnvelope, StableRef, TraceSpanPayload, TraceSpanRecord

trace = TraceSpanRecord(
    envelope=RecordEnvelope(
        record_ref=StableRef("record", "trace-forward-001"),
        record_type="trace_span",
        recorded_at="2026-03-30T09:08:31Z",
        observed_at="2026-03-30T09:08:31Z",
        producer_ref="scribe.python.local",
        run_ref=StableRef("run", "train-20260330-01"),
        stage_execution_ref=StableRef("stage", "train"),
        operation_context_ref=StableRef("op", "step-42"),
    ),
    payload=TraceSpanPayload(
        span_id="span-forward-001",
        trace_id="trace-train-01",
        parent_span_id="span-step-42",
        span_name="model.forward",
        started_at="2026-03-30T09:08:30Z",
        ended_at="2026-03-30T09:08:31Z",
        status="ok",
        span_kind="model_call",
        attributes={"device": "cuda:0", "batch_size": 32},
        linked_refs=("artifact:checkpoint-epoch-1",),
    ),
)
```

payload 형태는 대략 다음처럼 보입니다.

```json
{
  "completeness_marker": "complete",
  "correlation_refs": {
    "session_id": null,
    "trace_id": "trace-train-01"
  },
  "degradation_marker": "none",
  "extensions": [],
  "observed_at": "2026-03-30T09:08:31Z",
  "operation_context_ref": "op:step-42",
  "payload": {
    "attributes": {
      "batch_size": 32,
      "device": "cuda:0"
    },
    "ended_at": "2026-03-30T09:08:31Z",
    "linked_refs": [
      "artifact:checkpoint-epoch-1"
    ],
    "parent_span_id": "span-step-42",
    "span_id": "span-forward-001",
    "span_kind": "model_call",
    "span_name": "model.forward",
    "started_at": "2026-03-30T09:08:30Z",
    "status": "ok",
    "trace_id": "trace-train-01"
  },
  "producer_ref": "scribe.python.local",
  "record_ref": "record:trace-forward-001",
  "record_type": "trace_span",
  "recorded_at": "2026-03-30T09:08:31Z",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "stage_execution_ref": "stage:train"
}
```

trace를 읽을 때는 단순 duration 숫자만 보는 것보다 다음을 함께 보는 편이 좋습니다.

- 어느 상위 span 아래에서 실행됐는가
- 어떤 operation context와 연결되는가
- span 자체 상태와 linked ref가 무엇인가

그래야 병목 분석, 실패 전파 분석, 외부 요청 흐름 재구성이 쉬워집니다.

## event, metric, trace는 경쟁 관계가 아니다

실무에서는 셋 중 하나만 선택하는 경우보다 셋을 함께 쓰는 경우가 많습니다. 같은 실행을 바라보더라도 event, metric, trace는 서로 다른 질문에 답하기 때문입니다.

예를 들어 하나의 학습 step 안에서도 다음 세 레코드는 모두 동시에 의미가 있습니다.

- epoch가 시작되었다는 사실은 event
- 그 시점의 loss 값은 metric
- `model.forward` 호출이 얼마나 걸렸는지는 trace span

즉, 이 셋은 대체 관계가 아니라 보완 관계입니다. 같은 실행을 더 입체적으로 설명하기 위해 서로 다른 관점의 레코드를 함께 남기는 것이 자연스럽습니다.

다르게 말하면:

- event는 "무슨 일이 있었는가"를 말합니다.
- metric은 "값이 얼마였는가"를 말합니다.
- trace는 "얼마나 걸렸고 어떤 흐름으로 실행되었는가"를 말합니다.

## 어떤 레코드를 언제 써야 하나

레코드 타입을 고를 때 가장 좋은 기준은 "나중에 이 데이터를 어떤 방식으로 읽고 싶은가"입니다. 지금 쓰기 편한 타입을 고르기보다, 나중에 어떤 질문에 답해야 하는지 기준으로 선택하는 편이 훨씬 낫습니다.

### 한 문장으로 구분하는 빠른 기준

문서형으로 아주 짧게 정리하면 다음처럼 생각하면 됩니다.

- "무슨 일이 발생했는가"가 핵심이면 event
- "값이 얼마인가"가 핵심이면 metric
- "얼마나 걸렸고 어떤 흐름이었는가"가 핵심이면 trace

하지만 이건 어디까지나 첫 판단 기준일 뿐이고, 실제로는 세 타입을 함께 쓰는 경우가 많습니다.

## 관측 레코드 조합 예시

같은 학습 루프를 예로 들면, 아래 세 레코드는 서로 다른 목적을 갖습니다.

### 예시 1. epoch 시작

```text
training.epoch.started
```

이건 상태 전이이므로 event가 적합합니다.

### 예시 2. step loss

```text
training.loss = 0.4821
```

이건 수치 비교와 시계열 분석 대상이므로 metric이 적합합니다.

### 예시 3. forward pass duration

```text
model.forward started_at=... ended_at=...
```

이건 시간 구간과 실행 경로가 중요하므로 trace span이 적합합니다.

즉, 같은 한 번의 실행 안에서도 관측 대상의 성격에 따라 레코드 타입이 달라집니다.

## 관측 레코드 모델링에서 흔한 실수

이 섹션은 특히 중요합니다. 대부분의 운영 데이터는 "기술적으로 저장은 되지만 나중에 읽기 어렵게" 망가지는 경우가 많기 때문입니다.

### 1. 모든 걸 metric으로 보내기

이건 가장 흔한 실수 중 하나입니다. 상태 전이 이벤트까지 숫자로 억지로 표현하면 겉으로는 단순해 보이지만 의미가 크게 약해집니다.

예를 들어:

```text
training.epoch.started=1
```

이 값은 숫자처럼 보이지만 실제로는 이벤트에 가깝습니다. 이런 데이터를 metric으로 남기면 다음 문제가 생깁니다.

- event 검색이 어려워짐
- 사람이 읽는 의미가 흐려짐
- 잘못된 집계가 발생하기 쉬움

### 2. event에 수치형 핵심 관측값을 넣기

반대로 수치형 핵심 관측값을 사람이 읽는 메시지 안에만 넣는 경우도 많습니다.

예를 들어:

```text
"training loss is 0.4821"
```

이런 메시지는 눈으로 읽기엔 편하지만, 나중에 평균을 내거나, 시계열로 그리거나, 임계치를 넘는 구간만 찾는 데는 적합하지 않습니다. 이런 데이터는 metric으로 구조화하는 편이 맞습니다.

### 3. trace를 시작/종료 event 두 개로 대체하기

"시작 이벤트"와 "종료 이벤트"만 남기면 대충 duration 계산은 할 수 있을 것 같지만, 실제로는 trace가 주는 중요한 구조를 잃게 됩니다.

특히 다음 정보가 약해집니다.

- parent-child 관계
- 중첩 span 구조
- linked span
- trace 단위 grouping

시간 구간 자체가 중요하다면 trace span을 쓰는 편이 훨씬 낫습니다.

### 4. envelope 맥락을 비워 두기

run/stage/op 연결이 빠지면 레코드 자체는 남아도 운영적 해석 가능성이 크게 떨어집니다.

예를 들어 metric 하나가 있어도 다음을 모르면 해석이 급격히 어려워집니다.

- 어느 run인가
- 어느 stage인가
- 어느 operation context인가

초기에는 귀찮아 보여도, 가능한 한 run 정도는 항상 채우는 편이 좋습니다.

### 5. `record_type`과 payload 의미를 맞추지 않기

객체 타입과 envelope의 `record_type`이 어긋나면 validation이 실패합니다. 이건 단순한 문법 오류라기보다, 시스템이 레코드를 어떻게 읽어야 할지 결정할 수 없게 만드는 구조 오류입니다.

예:

- `MetricRecord`인데 `record_type="structured_event"`

이 경우 consumer는 이 payload를 metric으로 읽어야 할지 event로 읽어야 할지 일관되게 판단할 수 없습니다.

### 6. `producer_ref`를 무시하기

같은 metric이라도 producer가 다르면 의미나 품질이 다를 수 있습니다. producer 정보는 나중에 데이터 품질 디버깅에 매우 유용합니다.

예를 들어:

- 어떤 producer는 raw step metric을 남기고
- 어떤 producer는 epoch aggregate만 남기며
- 어떤 producer는 일부 필드를 생략할 수 있습니다

이 차이를 구분하지 않으면 같은 metric key를 두고도 서로 다른 의미가 섞일 수 있습니다.

## 좋은 레코드 설계를 위한 실무 가이드

레코드를 설계할 때는 다음 질문을 먼저 던지는 것이 좋습니다.

### 이 데이터를 나중에 집계할 것인가

그렇다면 대체로 metric 쪽이 더 적합합니다.

### 사람이 메시지로 읽는 것이 중요한가

그렇다면 event 쪽이 더 적합합니다.

### 호출 구조와 시간 구간이 중요한가

그렇다면 trace span이 더 적합합니다.

### 이 데이터가 어느 실행 맥락에 속하는지 꼭 알아야 하는가

거의 항상 그렇기 때문에, 최소한 `run_ref`는 채우는 편이 좋습니다.

### 외부 trace/session 체계와 연결해야 하는가

그렇다면 `correlation_refs`를 적극적으로 쓰는 편이 좋습니다.

## 관측 레코드가 이후 분석에서 중요한 이유

관측 레코드 구조가 잘 잡혀 있으면 다음 같은 질의를 자연스럽게 할 수 있습니다.

- 특정 run의 모든 error event 수집
- train stage의 latency metric만 집계
- 특정 request의 trace와 metric을 함께 조회
- `degradation_marker != none`인 레코드만 추출
- 같은 trace_id를 공유하는 event/metric/span 묶기

즉, 레코드 구조는 단지 저장 포맷이 아니라 운영 분석의 기본 단위입니다.

## 이 페이지를 읽은 뒤

관측 레코드는 늘 컨텍스트와 함께 읽혀야 하며, 종종 artifact와 lineage와도 연결됩니다.

- 상위 컨텍스트는 [컨텍스트 모델](./context-models.md)
- artifact와 relation은 [산출물과 계보](./artifacts-and-lineage.md)

다음으로는 [산출물과 계보](./artifacts-and-lineage.md)를 읽으면 Spine의 나머지 절반이 이어집니다.
