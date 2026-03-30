# 검증 규칙

[사용자 가이드 홈](./README.md)

Spine 객체는 파이썬 코드로는 쉽게 만들 수 있지만, 그렇다고 바로 유효한 canonical object가 되는 것은 아닙니다. 이 문서는 객체가 Spine 계약을 만족하는지 확인하는 validation 규칙을 설명합니다.

즉, validation은 단순 타입 체크가 아니라 계약 집행입니다. 이 단계가 중요한 이유는 다음과 같습니다.

- 잘못된 ref kind를 조기에 발견
- 잘못된 timestamp 형식을 조기에 차단
- enum/status 값 오염 방지
- serialization 직전 실패가 아니라 생성 지점에서 실패 유도

조금 더 본질적으로 말하면 validation은 "객체를 만들 수 있는가"를 묻는 단계가 아니라 "이 객체를 Spine 계약의 일부로 믿어도 되는가"를 묻는 단계입니다.

파이썬에서는 잘못된 값이 들어간 dataclass 객체도 얼마든지 만들어질 수 있습니다. 하지만 Spine이 필요한 이유는 그런 객체를 canonical contract로 승격시키기 전에 한 번 더 걸러 내는 데 있습니다. validation은 바로 그 경계에 서 있습니다.

## 왜 validation이 별도 계층인가

겉으로 보면 객체 생성 시점에 모든 걸 막는 편이 더 단순해 보일 수 있습니다. 하지만 Spine은 validation을 별도 계층으로 둠으로써 다음 두 가지를 동시에 얻습니다.

- 모델 객체 자체는 단순하고 조립 가능하게 유지
- 계약 집행은 명시적인 validation 단계에서 일관되게 수행

이 분리는 실무에서 꽤 중요합니다.

예를 들어:

- producer 코드에서는 객체를 단계적으로 조립한 뒤 마지막에 검증할 수 있고
- migration 도구에서는 일부러 불완전한 객체를 읽은 뒤 어떤 규칙이 깨졌는지 보고서로 수집할 수 있으며
- deserializer는 객체 생성 후 validation을 공통 경로로 재사용할 수 있습니다

즉 validator를 별도 계층으로 두면 "객체 표현"과 "계약 집행"을 분리하면서도, 모든 입구에서 같은 규칙을 적용할 수 있습니다.

## ValidationReport

validator는 `ValidationReport`를 반환합니다.

```python
from spine import validate_project

report = validate_project(project)
```

구성:

- `valid`: 전체 성공 여부
- `issues`: 실패한 항목 목록

`issues`의 각 항목은 대체로 다음 두 정보를 가집니다.

- `path`: 어떤 필드에서 문제가 났는가
- `message`: 왜 실패했는가

즉 validation report는 단순히 "성공/실패"만 알려주는 값이 아니라, 어떤 계약을 어겼는지 구조적으로 설명하는 결과입니다.

즉시 예외를 발생시키고 싶다면:

```python
report.raise_for_errors()
```

이 방식은 fail-fast 패턴에 잘 맞습니다.

예를 들어 실패가 누적되면 개념적으로는 이런 모양이 됩니다.

```text
valid = False
issues = [
  {path: "run_ref", message: "kind must be 'run'"},
  {path: "started_at", message: "timestamp must be ISO-8601 UTC with trailing Z"},
]
```

이 구조 덕분에 producer 코드에서는 바로 예외를 던질 수 있고, UI나 배치 점검 도구에서는 여러 문제를 한 번에 보여줄 수도 있습니다.

이게 중요한 이유는 validation 실패가 단순 boolean이 아니기 때문입니다. 운영에서는 "실패했다"보다 "어디가 반복적으로 깨지는가"가 더 중요할 때가 많습니다. `ValidationReport`는 그 패턴을 수집하기 위한 최소 단위이기도 합니다.

## validation이 다루는 것과 다루지 않는 것

validation이 다루는 것:

- 계약상 허용되는 필드 값
- ref kind 일치 여부
- timestamp 정규 형식
- 시간 순서 무결성
- record type / payload 타입 일관성
- 기본 무결성 조건

validation이 직접 다루지 않는 것:

- 실제 외부 리소스 존재 여부
- artifact 경로가 실제로 있는지
- ref가 다른 저장소에 실제로 존재하는지
- 비즈니스 의미상의 "정답 여부"

즉, validation은 "계약상 유효한 구조인가"를 보는 단계이지, 전체 시스템 통합 검증을 대체하는 것은 아닙니다.

이 경계를 분명히 두는 것이 중요합니다. validation이 강력하다고 해서 그것이 "운영상 맞는 데이터"까지 보장하는 것은 아닙니다. Spine validator는 어디까지나 canonical contract를 집행하는 층입니다.

예를 들어 validator는:

- `run_ref.kind == "run"` 인지는 확인하지만
- 그 run이 실제 저장소에 존재하는지는 확인하지 않습니다

- timestamp가 정규 형식인지는 확인하지만
- 그 시각이 비즈니스적으로 타당한 운영 일정인지는 확인하지 않습니다

즉 validation은 의미를 모두 판정하는 신탁이 아니라, 계약을 지키는 최소한의 문지기입니다.

## 무엇을 검증하나

현재 validation은 크게 다음 규칙을 봅니다.

- ref kind가 기대한 종류인지
- enum/status 값이 허용 집합에 속하는지
- timestamp가 UTC `Z` 정규 형식인지
- 종료 시각이 시작 시각보다 뒤인지
- `recorded_at >= observed_at`인지
- 음수 `size_bytes` 같은 기본 무결성 오류가 없는지
- 현재 `schema_version`과 일치하는지

조금 더 요약하면 Spine validation은 다음 네 범주를 검사합니다.

- 형태: 필수 필드가 비어 있지 않은가
- 참조: `StableRef.kind`가 기대와 맞는가
- 시간: timestamp 형식과 선후관계가 맞는가
- 의미 표식: status, type, marker, assertion mode 같은 값이 허용 집합 안에 있는가

이 네 범주는 Spine 전체 모델에 반복적으로 나타나는 공통 패턴이기도 합니다. 그래서 validation 문서를 읽을 때는 개별 타입 규칙을 외우기보다, "Spine은 ref, 시간, enum, schema 경계에 특히 엄격하다"는 감각을 먼저 잡는 편이 좋습니다.

## 타입별 validation 직관

### Project

확인 포인트:

- `project_ref.kind == "project"`
- `name`이 비어 있지 않음
- `created_at` 정규 형식
- `schema_version` 일치

### Run

확인 포인트:

- `run_ref.kind == "run"`
- `project_ref.kind == "project"`
- 허용 status인지
- `started_at` 유효한지
- `ended_at`가 있으면 시간 순서가 맞는지

### StageExecution

확인 포인트:

- `stage_execution_ref.kind == "stage"`
- `run_ref.kind == "run"`
- `stage_name` 비어 있지 않음
- status 허용값
- 시간 순서

### OperationContext

확인 포인트:

- `operation_context_ref.kind == "op"`
- `run_ref.kind == "run"`
- `stage_execution_ref`가 있으면 `kind == "stage"`
- `operation_name`이 비어 있지 않음
- `observed_at` 정규 형식

### EnvironmentSnapshot

확인 포인트:

- `environment_snapshot_ref.kind == "env"`
- `run_ref.kind == "run"`
- `captured_at` 정규 형식
- `python_version` 비어 있지 않음
- `platform` 비어 있지 않음

### RecordEnvelope

확인 포인트:

- `record_ref.kind == "record"`
- `run_ref.kind == "run"`
- `stage_execution_ref`가 있으면 `kind == "stage"`
- `operation_context_ref`가 있으면 `kind == "op"`
- `recorded_at`, `observed_at` 형식
- `recorded_at >= observed_at`
- marker 허용값

### MetricRecord

확인 포인트:

- `record_type == "metric"`
- `metric_key` 비어 있지 않음
- `value_type` 허용값

### TraceSpanRecord

확인 포인트:

- `record_type == "trace_span"`
- `span_id`, `trace_id` 비어 있지 않음
- `started_at <= ended_at`

### ArtifactManifest

확인 포인트:

- `artifact_ref.kind == "artifact"`
- `artifact_kind` 비어 있지 않음
- `run_ref.kind == "run"`
- `size_bytes >= 0` if present

### LineageEdge

확인 포인트:

- `relation_ref.kind == "relation"`
- `relation_type`이 허용 집합에 속함
- `recorded_at` 정규 형식
- `origin_marker` 비어 있지 않음
- `confidence_marker` 비어 있지 않음

### ProvenanceRecord

확인 포인트:

- `provenance_ref.kind == "provenance"`
- `relation_ref.kind == "relation"`
- `assertion_mode` 허용값
- `asserted_at` 정규 형식

즉 validation 범위는 context와 record뿐 아니라 artifact, lineage, provenance 계층 전체를 덮습니다.

## `schema_version` 검사는 무엇을 의미하나

Spine validator는 대부분의 canonical object에 대해 현재 `schema_version`과 정확히 일치하는지를 확인합니다.

이 말은 곧:

- 현재 schema 객체라면 validator를 통과해야 하고
- 구버전 payload라면 일반 validator나 deserializer에 바로 넣는 대신
- compatibility reader를 통해 현재 schema로 올린 뒤 검증해야 한다는 뜻입니다

즉 `schema_version` 검사는 버전 경계를 흐리지 않게 만드는 장치입니다.

이 규칙이 중요한 이유는, version mismatch가 가장 교묘한 오염을 만들기 쉽기 때문입니다. 완전히 깨지면 오히려 알아차리기 쉽지만, 구버전 payload가 부분적으로만 읽히면 더 위험합니다. Spine은 이런 "대충 읽히는 상태"를 피하기 위해 현재 schema 검사를 엄격하게 둡니다.

## validator, deserializer, compatibility reader는 어떻게 다른가

세 경로는 비슷해 보이지만 역할이 분명히 다릅니다.

### validator

이미 메모리 위에 있는 canonical object가 계약을 지키는지 검사합니다.

질문으로 바꾸면:

- "이 객체를 Spine object로 인정해도 되는가"

### deserializer

현재 schema payload를 읽어 canonical object로 만들고, 그 뒤 validation까지 수행합니다.

질문으로 바꾸면:

- "이 현재 버전 payload를 안전하게 Spine object로 읽을 수 있는가"

### compatibility reader

구버전 payload를 받아 현재 schema로 올린 뒤, 필요한 매핑과 정규화를 기록하면서 읽습니다.

질문으로 바꾸면:

- "이 과거 버전 payload를 어떤 보정을 거쳐 현재 계약으로 가져올 수 있는가"

즉 세 경로를 한 줄로 요약하면:

- validator: 검사
- deserializer: 현재 schema 읽기 + 검사
- compatibility reader: 구버전 업그레이드 읽기 + 검사

이 구분을 이해하면 외부 입력을 어디로 넣어야 하는지도 명확해집니다.

## 흔한 실패 사례

### `Z` 없는 timestamp

```python
Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00",
)
```

이 경우 계약상 timestamp 형식을 어기므로 실패합니다.

### 잘못된 ref kind

```python
Run(
    run_ref=StableRef("project", "oops"),
    project_ref=StableRef("project", "nova"),
    name="bad-run",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)
```

`run_ref`는 반드시 `run` kind여야 합니다.

실무에서 이런 오류가 무서운 이유는, 일단 저장된 뒤에는 소비자가 그 ref를 잘못된 종류의 객체로 해석할 수 있기 때문입니다. validation은 이런 오염을 입구에서 막습니다.

### envelope와 payload 타입 불일치

`MetricRecord`를 만들면서 envelope의 `record_type`을 `"structured_event"`로 넣으면 실패합니다.

이 오류는 단순 오타가 아니라, consumer가 payload를 어떻게 읽어야 할지 결정하지 못하게 만드는 구조 오류입니다.

### 시각 역전

trace span에서 `started_at > ended_at`이면 실패합니다.

이런 오류가 누적되면 duration 계산, 병목 분석, SLA 집계까지 모두 왜곡될 수 있습니다. 시간 필드 검증은 형식 체크를 넘어서 downstream 분석을 보호하는 역할도 합니다.

### 기록 시각이 관측 시각보다 빠름

```python
RecordEnvelope(
    record_ref=StableRef("record", "metric-1"),
    record_type="metric",
    recorded_at="2026-03-30T09:08:29Z",
    observed_at="2026-03-30T09:08:30Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=None,
    operation_context_ref=None,
)
```

이 경우 시간 의미론상 부자연스럽기 때문에 실패합니다.

### 지원하지 않는 relation type

`LineageEdge`에 허용되지 않은 `relation_type`을 넣으면 실패합니다.

이 규칙은 lineage vocabulary가 제멋대로 확산되는 것을 막아 줍니다.

### 잘못된 assertion mode

`ProvenanceRecord`에서 `assertion_mode`가 `explicit`, `imported`, `inferred` 중 하나가 아니면 실패합니다.

이 규칙이 있어야 provenance의 신뢰 해석이 일관됩니다.

## 왜 이런 실패를 일찍 막아야 하나

validation 오류는 대개 "지금 객체 하나가 틀렸다"에서 끝나지 않습니다. 방치하면 더 큰 구조 오염으로 번집니다.

예:

- 잘못된 ref kind는 relation 연결을 깨뜨리고
- 잘못된 timestamp는 시계열과 duration 분석을 왜곡하며
- 잘못된 `record_type`은 payload 해석 자체를 흔들고
- 잘못된 schema version은 migration 경계를 무너뜨립니다

즉 validation은 로컬 오류를 잡는 도구이면서 동시에 시스템 전체의 의미 일관성을 지키는 도구입니다.

## validation을 언제 호출해야 하나

### 1. 객체 생성 직후

가장 권장되는 패턴입니다.

```python
metric = MetricRecord(...)
validate_metric_record(metric).raise_for_errors()
```

### 2. serialization 직전

생성 이후 객체를 여러 단계 거쳐 조립했다면 직렬화 전 한 번 더 확인할 수 있습니다.

### 3. deserialization 이후

현재 deserializer는 내부적으로 validation을 수행하지만, 별도 ingestion 단계에서 추가 규칙을 적용하고 싶다면 후속 검증을 둘 수 있습니다.

실제로 Spine의 현재 deserializer는 객체를 만든 뒤 validator를 호출하고, 실패하면 `SerializationError`로 감싸서 올립니다. 따라서 외부 payload를 읽을 때는 보통:

1. deserializer 또는 compatibility reader로 읽고
2. 필요하면 도메인별 추가 검증을 더하고
3. 이후 저장/전송 단계로 넘기는 흐름이 자연스럽습니다

즉 validator를 직접 호출하는 경로와 deserializer 내부에서 간접적으로 호출되는 경로가 함께 존재합니다.

실무적으로는 다음처럼 생각하면 편합니다.

- 내가 이미 객체를 만들고 있다면 validator를 직접 호출
- 내가 외부 payload를 읽고 있다면 deserializer 또는 compatibility reader 사용
- 내가 시스템별 추가 규칙까지 보고 싶다면 Spine validation 뒤에 도메인 validation을 한 층 더 둠

## fail-fast vs accumulate

Spine의 `ValidationReport`는 두 패턴을 모두 지원합니다.

### fail-fast

```python
validate_project(project).raise_for_errors()
```

장점:

- 빠르게 실패
- 흐름이 단순
- producer 코드에서 사용하기 좋음
- 오염된 객체가 이후 단계로 넘어가기 전에 막기 쉬움

### accumulate

```python
report = validate_project(project)
if not report.valid:
    for issue in report.issues:
        ...
```

장점:

- 여러 오류를 한 번에 수집
- UI, 배치 리포트, migration 도구에 적합
- 어떤 규칙 위반이 반복되는지 패턴을 보기 좋음

실무에서는 producer 내부 코드에는 fail-fast가, migration/ingestion 진단 도구에는 accumulate가 더 잘 맞는 경우가 많습니다.

### 어떤 경우에 어느 패턴이 더 자연스러운가

`fail-fast`가 더 잘 맞는 경우:

- producer SDK
- request 처리 중 즉시 거절해야 하는 경로
- 테스트에서 첫 실패를 바로 보고 싶을 때

`accumulate`가 더 잘 맞는 경우:

- 배치 import 점검
- migration 품질 리포트
- 관리자 UI에서 다수의 입력 문제를 한 번에 보여줄 때

## validation이 운영에 중요한 이유

validation은 단순 개발 편의 기능이 아닙니다. 운영 품질을 지키는 첫 번째 방어선입니다.

validation이 없으면:

- 잘못된 timestamp가 저장됨
- 잘못된 ref kind가 퍼짐
- record type과 payload 의미가 어긋남
- 구버전/비정규 payload가 조용히 섞임

이 문제들은 처음엔 사소해 보여도, 나중에 대시보드와 lineage, 분석 결과를 전부 오염시킬 수 있습니다.

특히 validation이 없는 시스템은 "에러가 없는 것처럼 보이는데 결과가 이상한" 상태로 오래 가기 쉽습니다. hard failure보다 silent corruption이 더 위험한 이유가 여기에 있습니다.

이게 validation 문서에서 가장 중요한 메시지일 수 있습니다. Spine validation의 목적은 단순히 더 엄격해지는 것이 아니라, 고통의 시점을 앞당기는 것입니다. 나중에 대시보드와 분석 결과가 틀어진 뒤 발견하는 것보다, 객체를 만든 자리에서 바로 실패하는 편이 훨씬 싸고 안전합니다.

## 추천 패턴

- 객체 생성 직후 검증
- serialization 직전 검증
- migration 도구에서는 report 누적 처리
- 외부 입력은 deserializer 또는 compatibility reader를 통해만 수용

## 이 문서를 읽을 때 잡아야 할 핵심 직관

아주 짧게 정리하면 다음과 같습니다.

- validator는 객체 생성 성공 여부가 아니라 계약 준수 여부를 본다
- `ValidationReport`는 실패 이유를 구조적으로 수집한다
- deserializer도 내부적으로 validation에 의존한다
- validation은 저장 전 마지막 장식이 아니라 시스템 입구의 방어선이다

조금 더 압축하면 Spine validation은 결국 다음 한 문장으로 기억해도 됩니다.

"잘못된 데이터를 나중에 해석으로 복구하려 하지 말고, 애초에 계약 위반 상태로 시스템 안에 들어오지 못하게 한다."

## 다음 문서

- payload 생성과 읽기는 [직렬화와 스키마](./serialization-and-schema.md)
- 레거시 입력 처리 방식은 [호환성 및 마이그레이션](./compatibility-and-migrations.md)
