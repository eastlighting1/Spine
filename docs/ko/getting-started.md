# 시작하기

[사용자 가이드 홈](./README.md)

이 문서는 Spine을 처음 사용하는 사용자를 위한 가장 실용적인 출발점입니다. 목표는 다음 세 가지입니다.

1. 로컬에서 Spine을 import할 수 있는 상태를 만든다.
2. 최소한의 `Project -> Run -> MetricRecord` 흐름을 손으로 만들어본다.
3. validation과 serialization이 어떤 역할을 하는지 감을 잡는다.

이 페이지를 다 읽고 나면 적어도 "Spine 객체를 어떻게 만들고 어디서 검증하고 어떤 형태로 밖으로 내보내는지"는 바로 구현할 수 있어야 합니다.

## Spine이 해결하는 문제

Spine은 ML 옵저버빌리티 시스템 사이에서 공유되는 데이터 계약을 통일하기 위한 라이브러리입니다. 이 라이브러리가 없으면 팀마다 다음이 모두 달라지기 쉽습니다.

- metric payload 필드 이름
- run id 규칙
- artifact metadata 구조
- timestamp 형식
- lineage 표현 방식

이 상태에서는 수집, 적재, 검색, lineage 분석, 재현성 확인이 모두 어려워집니다.

Spine은 이를 줄이기 위해 다음을 제공합니다.

- 정해진 데이터 모델
- 엄격한 validation
- 안정적인 JSON serialization
- 현재 스키마 deserializer
- 구버전 payload를 위한 compatibility reader

짧게 말하면, Spine은 "ML 관측 데이터를 아무렇게나 흘려보내지 말고, 공통 계약으로 묶자"는 라이브러리입니다.

## 먼저 알아둘 핵심 개념

Spine의 가장 중요한 특징은 단순 dict를 다루는 대신, 의미가 있는 도메인 객체를 먼저 만든다는 점입니다.

가장 기본적인 흐름은 다음과 같습니다.

```text
Project
  -> Run
    -> StageExecution
      -> RecordEnvelope + Payload
```

이 구조를 먼저 이해하면 이후의 문서가 훨씬 쉬워집니다.

- `Project`: 프로젝트나 모델군 같은 최상위 단위
- `Run`: 실제 한 번 수행된 실행
- `StageExecution`: run 내부의 단계
- `RecordEnvelope + Payload`: 실제 관측 데이터

처음에는 `Project`, `Run`, `MetricRecord`만 다뤄도 충분합니다.

## 설치와 실행

### 로컬에서 바로 실행하기

로컬 개발 환경에서 가장 간단한 실행 방식은 `uv` 기반 editable 설치입니다.

```bash
uv run --with-editable . python
```

이 명령은 현재 작업 중인 소스를 그대로 import 가능하게 해줍니다.

### 테스트 실행

테스트를 실행할 때는 다음 명령을 사용합니다.

```bash
uv run --with-editable . --with pytest python -m pytest -q
```

처음 환경을 확인할 때는 이 명령이 가장 빠른 sanity check입니다.

라이브러리 코드와 테스트를 함께 타입 검사하려면 다음 명령을 사용합니다.

```bash
uv run mypy src tests
```

### import 확인

설치 뒤에 최소한 아래 명령이 되는지 확인해 두는 것이 좋습니다.

```bash
uv run --with-editable . python -c "import spine; print(spine.__file__)"
```

이 명령이 성공하면 현재 워크스페이스의 `spine` 패키지를 정상적으로 보고 있다는 뜻입니다.

## 기본 import

대부분의 사용자는 루트 패키지 `spine`만 import하면 됩니다.

```python
from spine import (
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    Run,
    StableRef,
    validate_metric_record,
    validate_project,
    validate_run,
)
```

일단 시작할 때는 아래 정도만 기억하면 됩니다.

- 모델 생성은 `Project`, `Run`, `MetricRecord`
- 식별자는 `StableRef`
- 검증은 `validate_*`
- 출력은 `to_payload()`, `to_json()`

외부 사용자 입장에서는 `spine`이 public API 경계입니다. `spine.models...` 같은 내부 모듈 import는 확장이나 라이브러리 자체 개발이 아닌 이상 피하는 편이 좋습니다.

## Spine 객체를 만들 때의 기본 규칙

Spine을 처음 쓸 때 가장 많이 헷갈리는 부분은 세 가지입니다.

### 1. 식별자는 raw string 대신 `StableRef`

좋은 예:

```python
StableRef("project", "nova")
StableRef("run", "train-20260330-01")
```

피해야 할 예:

```python
"project:nova"
"run-20260330-01"
```

payload 수준에서는 문자열이 맞지만, 모델 내부에서는 `StableRef`를 쓰는 편이 검증과 의미 표현에 훨씬 좋습니다.

### 2. timestamp는 UTC `Z` 형식

좋은 예:

```text
2026-03-30T09:00:00Z
```

피해야 할 예:

```text
2026-03-30T09:00:00
2026/03/30 09:00:00
```

현재 validation은 주요 필드가 이 정규 형식을 따르는지 검사합니다.

### 3. 만든 직후 validation

Spine의 생성자는 자동으로 validation을 수행하지 않습니다. 객체를 만든 뒤 바로 validation을 수행하는 패턴이 가장 안전합니다.

```python
report = validate_project(project)
report.raise_for_errors()
```

이 패턴을 쓰면 serialization 시점이나 저장 직전에 뒤늦게 깨지는 일을 줄일 수 있습니다.

## 첫 번째 객체 만들기: Project

가장 흔한 시작점은 `Project`입니다. 프로젝트는 장기적으로 유지되는 논리 단위입니다.

```python
from spine import Project, StableRef, validate_project

project = Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00Z",
    description="Image classification project.",
    tags={"team": "research", "track": "vision"},
)

validate_project(project).raise_for_errors()
```

여기서 필드 의미는 다음 정도만 먼저 이해하면 충분합니다.

- `project_ref`: 프로젝트 식별자
- `name`: 사람이 읽는 이름
- `created_at`: 생성 시각
- `description`: 설명
- `tags`: 간단한 메타데이터

`tags`, `attributes`, `packages`, `environment_variables` 같은 메타데이터 mapping은 생성 시 정렬되고 read-only로 고정됩니다. 입력으로는 일반 dict를 넘겨도 되지만, 모델에 저장된 값은 수정 가능한 dict가 아니라 읽기 전용 뷰로 생각하는 편이 맞습니다.

### 왜 `Project`가 필요한가

처음엔 "metric만 보내면 되지 않나?" 싶을 수 있습니다. 하지만 `Project`가 있어야 다음 질문에 답하기 쉬워집니다.

- 이 run은 어떤 제품/실험 계열에 속하는가
- 어떤 팀이 관리하는가
- 어떤 종류의 워크로드인가

## 두 번째 객체 만들기: Run

`Run`은 실제 한 번 수행된 실행 단위입니다.

```python
from spine import Run, validate_run

run = Run(
    run_ref=StableRef("run", "train-20260330-01"),
    project_ref=project.project_ref,
    name="baseline-resnet50",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)

validate_run(run).raise_for_errors()
```

처음에는 다음 네 필드만 확실히 이해하면 됩니다.

- `run_ref`: 실행 식별자
- `project_ref`: 어떤 project에 속하는지
- `status`: 실행 상태
- `started_at`: 실행 시작 시각

허용 status는 현재 다음 중 하나입니다.

- `created`
- `running`
- `completed`
- `failed`
- `cancelled`

## 세 번째 객체 만들기: 첫 번째 레코드

Spine의 실제 관측 데이터는 대부분 레코드 형태로 남습니다. 처음에는 `MetricRecord`를 만드는 것이 가장 쉽습니다.

Spine 레코드는 공통적으로 다음 구조를 따릅니다.

```text
RecordEnvelope + Payload
```

즉:

- envelope: 실행 맥락과 메타데이터
- payload: 실제 metric 값

## 첫 번째 MetricRecord 만들기

```python
from spine import (
    MetricPayload,
    MetricRecord,
    RecordEnvelope,
    StableRef,
    validate_metric_record,
)

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
        tags={"device": "cuda:0"},
    ),
)

validate_metric_record(metric).raise_for_errors()
```

### envelope에서 먼저 볼 필드

- `record_ref`: 레코드 식별자
- `record_type`: `"metric"`
- `recorded_at`: 시스템이 기록한 시각
- `observed_at`: 실제 측정 시각
- `producer_ref`: 어떤 producer가 만들었는지
- `run_ref`: 어느 run에 속하는지

### payload에서 먼저 볼 필드

- `metric_key`: metric 이름
- `value`: 측정값
- `value_type`: 값의 타입
- `unit`: 단위
- `tags`: 보조 메타데이터

현재 metric validation은 `value`가 `value_type`과 일치하는지도 검사합니다. 따라서 `integer`는 `int`, `float`는 `float`여야 하고, boolean 값은 허용되지 않습니다.

### 왜 envelope와 payload를 나누나

metric, event, trace는 실제 내용은 다르지만 "언제, 어디서, 누가 만든 기록인가"라는 메타데이터는 공유합니다. Spine은 그 공통 부분을 `RecordEnvelope`로 묶어서 재사용합니다.

## 첫 번째 직렬화

객체를 만들고 validation이 통과했다면 payload나 JSON으로 직렬화할 수 있습니다.

```python
from spine import to_json, to_payload

payload = to_payload(metric)
encoded = to_json(metric)
```

두 함수의 차이:

- `to_payload()`: JSON 호환 dict
- `to_json()`: 안정적인 JSON 문자열

예를 들어 `to_payload(metric)` 결과는 대략 다음처럼 생깁니다.

```python
{
    "record_ref": "record:metric-step-42",
    "record_type": "metric",
    "recorded_at": "2026-03-30T09:08:30Z",
    "observed_at": "2026-03-30T09:08:30Z",
    "producer_ref": "scribe.python.local",
    "run_ref": "run:train-20260330-01",
    "stage_execution_ref": None,
    "operation_context_ref": None,
    "correlation_refs": {
        "trace_id": None,
        "session_id": None,
    },
    "completeness_marker": "complete",
    "degradation_marker": "none",
    "schema_version": "1.0.0",
    "extensions": [],
    "payload": {
        "metric_key": "training.loss",
        "value": 0.4821,
        "value_type": "scalar",
        "unit": "ratio",
        "aggregation_scope": "step",
        "subject_ref": None,
        "slice_ref": None,
        "tags": {"device": "cuda:0"},
        "summary_basis": None,
    },
}
```

여기서 중요한 점은:

- `StableRef`가 문자열 `"kind:value"`로 바뀜
- dict key 순서가 안정적으로 유지됨
- 나중에 저장/전송/비교하기 쉬운 형태가 됨

## 전체를 한 번에 보는 최소 예제

아래 예제는 Project, Run, MetricRecord를 한 번에 만드는 가장 작은 흐름입니다.

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
    ),
)
validate_metric_record(metric).raise_for_errors()

print(to_json(metric))
```

이 코드는 Spine 사용의 핵심 루프를 그대로 보여줍니다.

1. 객체를 만든다.
2. 검증한다.
3. 직렬화한다.

## 다음으로 해볼 것

이 페이지까지 따라왔다면 다음 순서가 좋습니다.

1. `StageExecution`까지 포함한 흐름을 보고 싶다면 [워크플로 예제](./workflow-examples.md)
2. Spine이 왜 이런 구조를 갖는지 알고 싶다면 [Spine 모델 이해하기](./understanding-spine-models.md)
3. 각 타입의 필드 정의를 자세히 보려면 [컨텍스트 모델](./context-models.md), [관측 레코드](./observability-records.md), [산출물과 계보](./artifacts-and-lineage.md)
4. validation 실패를 어떻게 읽고 처리할지는 [검증 규칙](./validation-rules.md)

## 관련 파일

- 기본 예제 코드: [`examples/basic_training_flow.py`](C:/Users/eastl/MLObservability/Spine/examples/basic_training_flow.py)
- 패키지 진입점: [`src/spine/__init__.py`](C:/Users/eastl/MLObservability/Spine/src/spine/__init__.py)
