# Spine 모델 이해하기

[사용자 가이드 홈](./README.md)

Spine을 처음 보면 가장 먼저 드는 질문은 보통 "왜 객체가 이렇게 많이 나뉘어 있지?"입니다. 이 문서는 그 질문에 답하기 위한 개념 문서입니다.

`시작하기`가 바로 손으로 객체를 만들어보는 문서라면, 이 페이지는 어떤 객체를 언제 써야 하는지 판단 기준을 잡는 문서입니다.

이 문서의 목표는 다음과 같습니다.

1. Spine의 모델 계층을 머릿속에 하나의 그림으로 정리하기
2. 왜 비슷해 보이는 객체를 굳이 분리했는지 납득하기
3. 실제로 어떤 수준까지 모델링해야 하는지 판단 기준 얻기
4. 흔한 모델링 실수를 미리 피하기

이 문서를 읽고 나면, 개별 타입의 필드를 전부 외우지 않아도 Spine의 설계 방향은 분명히 이해할 수 있어야 합니다.

## Spine을 이해하는 핵심 질문

Spine을 이해할 때 가장 중요한 질문은 "무슨 로그를 남기느냐"가 아니라 "무슨 엔터티와 관계를 계약으로 고정하느냐"입니다.

일반적인 관측 시스템은 종종 다음 수준에서 멈춥니다.

- JSON 로그 한 줄
- metric name과 value
- trace span 한 개

하지만 ML 시스템에서는 이 정도로는 충분하지 않습니다. 나중에 반드시 다음 질문이 생깁니다.

- 이 metric은 어느 run에서 나왔는가
- 이 artifact는 어떤 stage에서 생성됐는가
- 이 관계는 명시적으로 선언된 것인가, 추론된 것인가
- 이 payload는 현재 스키마인가, 구버전 스키마인가
- 이 기록은 완전한가, 일부만 수집됐는가
- 이 실행은 어떤 프로젝트나 모델 계열에 속하는가
- 환경이 달라서 결과가 달라졌는가
- 어느 수준까지를 "같은 실행"이라고 봐야 하는가

Spine은 바로 이런 질문에 답할 수 있게 모델 구조를 미리 나눠 둔 라이브러리입니다.

## Spine이 해결하려는 문제를 더 구체적으로 보면

Spine이 없다면 팀은 보통 다음 중 하나를 하게 됩니다.

### 1. 모든 것을 로그 문자열에 밀어넣는다

예:

```text
2026-03-30T09:08:30Z training.loss=0.4821 run=train-20260330-01 stage=train step=42
```

이 방식은 사람이 읽기엔 쉽지만, 계약이 없어서 다음이 어렵습니다.

- 필드 누락 탐지
- 타입 검증
- 하위 호환 처리
- lineage와 provenance 표현

### 2. 모든 것을 느슨한 JSON dict로 둔다

예:

```json
{
  "type": "metric",
  "name": "training.loss",
  "value": 0.4821,
  "run": "train-20260330-01"
}
```

이 방식은 처음에는 유연해 보이지만, 시간이 지나면 같은 의미를 여러 필드명으로 표현하게 됩니다.

예:

- `run`, `run_id`, `runRef`, `run_ref`
- `eventTime`, `observed_at`, `timestamp`
- `artifactPath`, `location`, `uri`

### 3. tracing, metrics, artifacts를 완전히 별도 체계로 분리한다

이 경우 각 체계는 각각 동작하지만, 서로 연결이 약해집니다.

예를 들어:

- metric은 run id만 알고
- artifact는 파일 경로만 알고
- trace는 span id만 알고

그러면 "이 trace span이 발생하던 시점에 생성된 artifact가 무엇이고, 그때의 metric은 어땠는가" 같은 질문에 답하기 어려워집니다.

Spine은 이런 분절을 줄이기 위해 공통 컨텍스트와 공통 계약을 제공합니다.

## Spine이 모델을 나누는 방식

Spine의 모델은 크게 다섯 층으로 나눌 수 있습니다.

- 컨텍스트 계층: `Project`, `Run`, `StageExecution`, `OperationContext`, `EnvironmentSnapshot`
- 관측 계층: `StructuredEventRecord`, `MetricRecord`, `TraceSpanRecord`
- 산출물 계층: `ArtifactManifest`
- 관계 계층: `LineageEdge`, `ProvenanceRecord`
- 공통 인프라 계층: `StableRef`, `ExtensionFieldSet`, `schema_version`, validation, serialization

이 구조를 한 줄로 요약하면 이렇습니다.

```text
무슨 시스템에서
  -> 어떤 실행이 있었고
    -> 그 안에서 어떤 단계와 작업이 일어났고
      -> 어떤 관측값과 산출물이 생겼으며
        -> 그들 사이에 어떤 관계가 있는가
```

즉, Spine은 "관측 데이터 저장 형식"이라기보다 "관측 가능한 ML 실행을 구조화하는 모델"에 가깝습니다.

## Spine의 객체 그래프

가장 기본적인 Spine 객체 그래프는 다음처럼 생각할 수 있습니다.

```text
Project
  -> Run
    -> StageExecution
      -> OperationContext
        -> RecordEnvelope + Payload
    -> EnvironmentSnapshot
    -> ArtifactManifest
    -> LineageEdge / ProvenanceRecord
```

이 그래프는 몇 가지 중요한 메시지를 담고 있습니다.

### 1. 레코드는 혼자 존재하지 않는다

metric 하나만 있어도 일단 저장은 가능합니다. 하지만 Spine은 "이 metric이 어디에서 나온 것인지"를 항상 중요하게 봅니다.

그래서 레코드는 보통 다음과 연결됩니다.

- `run_ref`
- `stage_execution_ref`
- `operation_context_ref`

이 연결이 있어야 나중에 다음 같은 질의가 가능합니다.

- train stage의 metric만 보고 싶다
- step-42에서 나온 이벤트만 보고 싶다
- 특정 run에 속한 trace span만 보고 싶다
- 동일 run 안에서 stage별 error event를 모으고 싶다
- 특정 operation context에서 나온 artifact를 찾고 싶다

### 2. artifact도 실행 맥락과 연결된다

artifact는 파일 그 자체가 아니라, 실행의 결과물입니다. 그래서 `ArtifactManifest`는 단순 파일 메타데이터가 아니라 run/stage와 연결된 객체입니다.

즉 Spine에서 artifact는 이런 식으로 생각해야 합니다.

```text
checkpoint file
  -> run 안에서 생성됨
  -> 특정 stage에서 생성됨
  -> 특정 producer가 생성함
```

이 연결이 없으면 artifact는 단지 "어딘가에 있는 파일"로만 남습니다. 그러나 ML 운영에서는 보통 그보다 훨씬 더 많은 질문이 필요합니다.

- 이 체크포인트는 어느 실험 결과인가
- 어떤 train stage에서 만들어졌는가
- 어떤 producer가 export했는가
- 해시와 크기는 무엇인가

### 3. relation은 별도 계층으로 분리된다

artifact와 record와 run이 있다고 해서 관계가 저절로 설명되지는 않습니다. "무엇이 무엇에서 나왔는가"는 별도의 의미를 갖는 모델입니다.

그래서 Spine은 `LineageEdge`와 `ProvenanceRecord`를 별도 계층으로 둡니다.

이 설계 덕분에 Spine은 단순 이벤트 저장을 넘어 lineage와 provenance까지 표현할 수 있습니다.

예를 들어 같은 artifact라도 다음은 전혀 다른 주장입니다.

- dataset에서 `generated_from`
- stage에 의해 `produced_by`
- deploy artifact에서 `deployed_from`

이 차이를 문자열 메모로 남기는 대신 구조화된 모델로 남기는 것이 Spine의 방향입니다.

## 컨텍스트, 관측, 산출물, 관계는 왜 분리되는가

Spine 모델을 잘 이해하려면 "이것들이 왜 서로 다른 클래스여야 하느냐"를 이해해야 합니다.

### 컨텍스트

컨텍스트는 관측을 둘러싼 실행 맥락입니다.

질문 예:

- 어떤 프로젝트의 실행인가
- 어떤 stage인가
- 어떤 operation인가

### 관측

관측은 실제로 측정되거나 기록된 데이터입니다.

질문 예:

- 무슨 metric인가
- 어떤 이벤트가 발생했는가
- 어떤 span이 얼마나 걸렸는가

### 산출물

산출물은 실행 중 만들어진 결과물입니다.

질문 예:

- 어떤 파일/모델/리포트가 생성됐는가
- 어디 저장됐는가
- 해시와 크기는 무엇인가

### 관계

관계는 엔터티들 사이의 의미 연결입니다.

질문 예:

- 어떤 artifact가 어떤 dataset에서 유도되었는가
- 어떤 결과가 어떤 실행에 의해 보고되었는가
- 그 주장은 명시적인가 추론된 것인가

이 네 가지는 모두 중요하지만, 하나의 객체에 섞어 넣으면 곧 모델 경계가 무너집니다. Spine은 그것을 막기 위해 계층을 나눕니다.

## 왜 `Project -> Run -> StageExecution -> OperationContext` 구조인가

이 구조는 "큰 맥락"과 "작은 작업"을 한꺼번에 잃지 않기 위해 필요합니다.

### Project

`Project`는 오래 지속되는 논리 단위입니다.

예:

- 하나의 모델 계열
- 하나의 제품 기능
- 하나의 실험 트랙
- 하나의 서비스군

`Project`는 대개 오랫동안 유지됩니다. 며칠, 몇 주, 몇 달에 걸쳐 여러 run이 쌓일 수 있습니다.

### Run

`Run`은 실제 한 번 수행된 실행입니다.

예:

- 한 번의 training job
- 한 번의 batch evaluation
- 하루치 offline inference

`Run`은 "실행 단위"라는 점이 중요합니다. Project가 정적이고 장기적인 기준이라면, Run은 동적이고 시간 축을 가지는 기준입니다.

### StageExecution

`StageExecution`은 run 내부의 큰 단계입니다.

예:

- `extract`
- `prepare`
- `train`
- `evaluate`
- `deploy`

모든 시스템이 stage를 필요로 하진 않지만, run 안에서 의미 있는 큰 단계를 나눌 수 있으면 운영과 디버깅이 훨씬 쉬워집니다.

예:

- "실패는 train에서 났는가, evaluate에서 났는가?"
- "artifact는 train stage에서 생성됐는가?"
- "metric은 deploy 전후 어느 단계에서 나온 값인가?"

### OperationContext

`OperationContext`는 stage 내부의 더 세밀한 작업입니다.

예:

- `epoch-1`
- `step-42`
- `batch-000123`
- `request-abc123`

이 레벨은 특히 세밀한 metric/trace를 다룰 때 중요합니다.

예:

- 어떤 step에서 loss가 급격히 튀었는가
- 어떤 batch에서 latency가 비정상적이었는가
- 어떤 request에서 오류 span이 발생했는가

이 네 층을 모두 두는 이유는 다음과 같습니다.

- 너무 거칠면 상세 추적이 안 됨
- 너무 세밀하면 전체 맥락을 잃음
- 둘 다 잡아야 운영과 분석이 가능함

## Spine이 “레벨”을 나누는 기준

Spine의 컨텍스트 계층은 사실상 "스코프(scope)"를 나누는 구조입니다.

- `Project`: 장기적/논리적 스코프
- `Run`: 한 번의 실행 스코프
- `StageExecution`: 실행 내부의 단계 스코프
- `OperationContext`: 단계 내부의 세부 작업 스코프

이렇게 보면 Spine의 설계는 꽤 자연스럽습니다. 결국 관측 데이터를 해석하려면 "어느 스코프의 데이터인가"를 알아야 하기 때문입니다.

## 왜 레코드를 envelope와 payload로 나누는가

Spine에서 가장 중요한 설계 결정 중 하나입니다.

metric, event, trace는 서로 다른 데이터를 담지만 다음 메타데이터는 공통으로 가집니다.

- `record_ref`
- `record_type`
- `recorded_at`
- `observed_at`
- `producer_ref`
- `run_ref`
- `stage_execution_ref`
- `operation_context_ref`

반면 실제 payload는 다릅니다.

- event면 `event_key`, `message`, `level`
- metric이면 `metric_key`, `value`, `unit`
- trace면 `span_id`, `trace_id`, `started_at`, `ended_at`

이 둘을 분리하면 얻는 이점:

- 공통 validation 로직 재사용
- ingestion 파이프라인 단순화
- 공통 인덱싱 전략 수립 가능
- 레코드 타입 추가 시 envelope 규칙 재사용 가능
- 모든 레코드에 대해 동일한 context query 가능

즉, envelope/payload 분리는 단순 구현 취향이 아니라, 관측 모델의 확장성과 일관성을 위한 핵심 설계입니다.

## envelope가 의미하는 것

envelope는 "이 레코드를 둘러싼 사실"을 담습니다.

대표적으로:

- 누가 만들었는가 (`producer_ref`)
- 언제 기록됐는가 (`recorded_at`)
- 실제로 언제 관측됐는가 (`observed_at`)
- 어느 run/stage/op에 속하는가
- 데이터 품질 상태는 어떤가 (`completeness_marker`, `degradation_marker`)

즉, envelope는 payload를 이해하기 위한 문맥입니다.

반대로 payload는 "핵심 데이터 그 자체"입니다.

예:

- event payload: 무슨 일이 일어났는가
- metric payload: 무슨 값이 측정됐는가
- trace payload: 무슨 span이 얼마 동안 실행됐는가

## `observed_at`와 `recorded_at`를 왜 둘 다 두는가

처음 보면 두 필드가 겹쳐 보일 수 있습니다. 하지만 실제 운영에서는 둘이 다릅니다.

- `observed_at`: 현상이 실제로 발생한 시각
- `recorded_at`: 그 현상이 Spine 레코드로 기록된 시각

둘이 달라지는 대표 사례:

- 비동기 버퍼 flush
- 네트워크 지연
- batch collector
- sidecar exporter
- retry 후 재전송

이 구분이 있으면 다음이 가능해집니다.

- ingestion delay 추적
- 수집 pipeline 병목 분석
- 관측과 기록의 시간차 해석
- consumer가 늦게 받은 데이터를 올바른 시간축에 배치

즉, 이 둘의 차이는 단순 메타데이터가 아니라 시간 의미론의 일부입니다.

## 왜 `StableRef`를 별도 타입으로 두는가

`StableRef`는 단순 문자열 래퍼가 아닙니다. Spine에서 식별자는 계약의 일부입니다.

다음 둘은 겉보기엔 비슷하지만 의미가 다릅니다.

```python
"project:nova"
StableRef("project", "nova")
```

`StableRef`를 사용하면 얻는 것:

- kind/value 구조를 코드 레벨에서 표현 가능
- 잘못된 형식을 조기에 검증 가능
- serialization 시 항상 같은 표현 보장
- 타입 의미를 코드에서 더 명확하게 드러냄

예를 들어 `run_ref`에 실수로 `project` kind를 넣는 경우도 모델 단계에서 빨리 드러나게 만들 수 있습니다.

즉, id를 단순 문자열 convention에 맡기지 않고, 모델의 일부로 끌어올린 것입니다.

## 왜 schema version이 객체 안에 들어가나

Spine은 payload를 단순히 메모리에서 잠깐 쓰고 버리는 구조로 보지 않습니다. 저장하고, 전송하고, 나중에 다시 읽을 것을 전제로 합니다.

이때 schema version이 없으면 다음이 불명확해집니다.

- 이 payload가 어떤 계약 버전으로 생성됐는가
- 현재 reader가 그대로 읽어도 되는가
- 구버전 필드 매핑이 필요한가
- 동일 이름의 필드가 과거와 같은 의미를 갖는가

schema version은 다음 역할을 합니다.

- 현재 payload의 계약 버전 표기
- compatibility reader의 upgrade 기준 제공
- validation 기준 스키마 명시
- historical payload 해석 근거 제공

즉, schema version은 단순 부가 정보가 아니라 "이 객체를 어떤 계약으로 읽어야 하는가"를 알려주는 메타데이터입니다.

## 왜 extension을 top-level field가 아니라 별도 구조로 두는가

실무에서는 표준 스키마에 없는 데이터가 항상 생깁니다. 문제는 그걸 아무 필드나 추가하는 식으로 처리하면 계약이 금방 무너진다는 점입니다.

예를 들면 이런 상황이 생깁니다.

- 팀 A는 `owner`
- 팀 B는 `team_owner`
- 팀 C는 `serviceOwner`

모두 비슷한 의미지만 구조는 달라집니다.

Spine은 이 문제를 줄이기 위해 `ExtensionFieldSet`과 `ExtensionRegistry`를 둡니다.

- 표준 필드는 core schema로 유지
- 비표준 필드는 namespace 아래 확장으로 관리
- namespace 소유권은 registry로 통제

이 방식의 장점:

- 표준/비표준 경계가 명확함
- 의미 충돌을 줄일 수 있음
- 향후 표준 스키마 편입 후보를 관리하기 쉬움
- 각 팀이 필요한 메타데이터를 넣으면서도 공용 계약을 깨지 않음

## Spine이 추구하는 모델링 원칙

이 라이브러리를 쓰면서 기억하면 좋은 원칙은 다음과 같습니다.

### 1. 의미를 payload 이름에만 의존하지 않는다

Spine은 `metric_key` 문자열 하나에 모든 의미를 밀어넣기보다, run/stage/op/record/artifact/relation 구조를 통해 의미를 분산해서 표현합니다.

### 2. 실행 맥락을 항상 보존한다

관측 데이터는 단독 값보다 "어느 실행에서 나온 값인가"가 중요합니다. Spine은 이 맥락을 모델 차원에서 강제합니다.

### 3. 관계를 별도 엔터티로 다룬다

"A가 B에서 나왔다"는 사실은 부가 설명이 아니라 독립된 의미를 가지므로, Spine은 lineage를 별도 모델로 둡니다.

### 4. 과거 payload는 명시적으로 업그레이드한다

레거시 입력을 조용히 수용하지 않고, compatibility reader로 명시적 migration 경로를 둡니다.

### 5. 검증 가능한 구조를 우선한다

모델이 너무 자유로우면 처음엔 편하지만, 나중에 검증과 운영이 어려워집니다. Spine은 의도적으로 약간 더 구조적인 모델을 택합니다.

## Spine이 가능하게 하는 질문들

모델이 좋은지 아닌지는 결국 어떤 질문에 답할 수 있느냐로 드러납니다. Spine 구조를 잘 쓰면 다음 같은 질의가 가능해집니다.

- 특정 프로젝트의 모든 run 보기
- 한 run 안에서 train stage의 metric만 보기
- 특정 operation context의 trace span과 metric을 함께 보기
- 특정 artifact가 어느 run과 stage에서 생성됐는지 찾기
- 어떤 lineage edge가 explicit인지 inferred인지 구분하기
- 구버전 payload가 얼마나 자주 업그레이드되고 있는지 추적하기

즉, Spine은 데이터 저장 형식을 통일하는 것을 넘어, 이후의 분석과 운영 쿼리를 가능하게 합니다.

## 언제 어떤 레벨까지 모델링해야 하나

실무에서는 모든 객체를 항상 다 만들 필요는 없습니다. 하지만 어느 수준까지 모델링할지 판단 기준은 있어야 합니다.

### 최소 수준

- `Project`
- `Run`
- `MetricRecord` 또는 `StructuredEventRecord`

이 정도면 기본적인 관측은 가능합니다.

적합한 경우:

- 작은 실험성 시스템
- 우선 메트릭 수집부터 시작하는 단계
- lineage가 아직 중요하지 않은 초기 단계

### 운영 수준

- `Project`
- `Run`
- `StageExecution`
- record 계열
- `ArtifactManifest`

이 수준이면 대부분의 대시보드/운영/장애 분석이 가능해집니다.

적합한 경우:

- 학습/평가 파이프라인이 명확히 구분되는 시스템
- artifact 관리가 중요한 팀
- stage 단위 관찰이 필요한 운영 환경

### lineage/감사 수준

- 위의 모든 것
- `LineageEdge`
- `ProvenanceRecord`
- `EnvironmentSnapshot`

이 수준이면 재현성, 관계 추적, 정책 기반 분석까지 가능해집니다.

적합한 경우:

- 감사 가능성이 중요한 환경
- lineage 시각화가 필요한 환경
- 어떤 결과가 어떤 근거에서 나왔는지 추적해야 하는 환경

## 모델링 판단 가이드

다음 질문으로 판단하면 도움이 됩니다.

### `StageExecution`이 필요한가

다음 중 하나라도 해당하면 대체로 필요합니다.

- run 안에 단계가 명확히 나뉜다
- stage별 metric이나 artifact를 따로 보고 싶다
- 실패 지점을 단계 수준에서 식별해야 한다

### `OperationContext`가 필요한가

다음 중 하나라도 해당하면 고려할 가치가 큽니다.

- step/batch/request 수준 추적이 필요하다
- 동일 stage 안에서 매우 많은 세부 작업을 구분해야 한다
- trace/metric를 더 촘촘한 단위로 묶어야 한다

### `LineageEdge`가 필요한가

다음 질문에 답해야 한다면 필요합니다.

- 무엇이 무엇에서 만들어졌는가
- 어떤 결과가 어떤 입력/정책/이전 artifact에 의존하는가
- 관계를 사람이 아니라 시스템이 조회해야 하는가

## 흔한 모델링 실수

### 1. 모든 걸 metric 하나로 몰아넣기

event로 남겨야 할 상태 전이까지 metric으로 표현하면 의미가 왜곡됩니다.

예:

- `training.epoch.started=1`

이 값은 숫자처럼 보이지만 실제로는 이벤트에 가깝습니다.

### 2. run 없이 레코드만 남기기

처음엔 편하지만 나중에 실행 단위 분석이 거의 불가능해집니다.

예:

- metric은 남아 있는데 어느 실험인지 알 수 없음
- event는 있는데 어떤 run에서 난 오류인지 모름

### 3. artifact를 파일 경로 문자열로만 다루기

이렇게 하면 run/stage/producer/해시 정보가 쉽게 분리되어 버립니다.

결국 artifact는 "설명할 수 없는 파일"이 됩니다.

### 4. relation을 메모나 문자열 설명으로만 남기기

lineage를 별도 모델로 남기지 않으면 나중에 쿼리나 시각화가 어려워집니다.

예:

- `"derived from previous model"` 같은 설명 문자열만 남김

이 방식은 사람이 읽을 수는 있어도 시스템이 이해하기 어렵습니다.

### 5. 모든 팀별 메타데이터를 core field처럼 쓰기

이 경우 시간이 지나면 팀마다 같은 의미를 다른 필드명으로 쓰게 됩니다. 이런 경우는 extension namespace를 쓰는 편이 낫습니다.

## 이 페이지를 읽는 가장 좋은 방식

이 문서는 한 번에 다 외우려고 보기보다, 다음 관점으로 읽으면 좋습니다.

- "Spine은 무엇을 first-class entity로 취급하는가?"
- "왜 그 엔터티를 따로 분리했는가?"
- "내 시스템은 어느 레벨까지 모델링해야 하는가?"

이 질문에 답할 수 있다면 이 페이지의 목적은 충분히 달성된 것입니다.

## 이 페이지를 읽은 뒤 무엇을 보면 좋은가

이 문서가 "왜 이런 구조인가"를 설명했다면, 다음 문서들은 "각 구조가 실제로 어떻게 생겼는가"를 설명합니다.

- 실행 단위와 환경은 [컨텍스트 모델](./context-models.md)
- 이벤트/메트릭/트레이스는 [관측 레코드](./observability-records.md)
- artifact와 relation은 [산출물과 계보](./artifacts-and-lineage.md)

다음으로는 보통 [컨텍스트 모델](./context-models.md)부터 읽는 것이 가장 자연스럽습니다.
