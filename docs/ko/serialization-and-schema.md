# 직렬화와 스키마

[사용자 가이드 홈](./README.md)

Spine 객체를 파일로 저장하거나 다른 서비스로 넘기려면, 결국 JSON-compatible payload로 바꾸는 경계를 지나야 합니다. 이 문서는 그 serialization 경계와, 다시 current schema object로 읽어오는 deserialization 경계를 설명합니다.

이 문서의 핵심은 다음과 같습니다.

- 왜 deterministic serialization이 중요한가
- `to_payload()`와 `to_json()`은 무엇이 다른가
- deserializer는 단순 dict 변환기가 아니라는 점
- 스키마 버전이 serialization/reading 경계에서 어떤 의미를 가지는가

처음 쓰는 사용자라면 이 문서를 "JSON 유틸리티 설명"보다 "Spine 객체가 시스템 밖으로 나갔다가 다시 돌아올 때 어떤 규칙이 유지되는가"를 이해하는 문서로 읽는 편이 좋습니다.

## 왜 deterministic serialization이 중요한가

같은 객체가 매번 다른 key 순서의 JSON으로 나오면 다음 작업이 어려워집니다.

- payload diff
- golden fixture 테스트
- 캐시 키 생성
- 해시 계산
- 재현성 비교

Spine은 같은 객체에 대해 안정적인 출력이 나오도록 설계돼 있습니다.

이 성질은 보기 좋은 포맷팅 이상의 의미를 가집니다. serialization 결과가 안정적이면 "같은 의미의 객체는 같은 payload를 만든다"는 기대를 세울 수 있고, 그 위에 fixture 비교, 캐시, 해시, 회귀 테스트 같은 운영 기법을 얹기 쉬워집니다.

## 왜 serialization이 별도 계층인가

Spine 객체를 그대로 파이썬 메모리 안에서만 다룬다면 serialization은 크게 눈에 띄지 않을 수 있습니다. 하지만 시스템 경계를 넘는 순간 상황이 달라집니다.

- 파일로 저장해야 할 수 있고
- 다른 서비스로 전송해야 할 수 있으며
- 테스트 fixture와 비교해야 할 수 있고
- 로그나 감사 기록으로 남겨야 할 수 있습니다

이때 필요한 것은 "대충 dict로 바꾸는 함수"가 아니라, 현재 canonical contract를 외부로 안전하게 드러내는 경계입니다. Spine의 serialization 레이어는 바로 그 경계를 담당합니다.

반대로 deserialization 레이어는 외부 세계에서 들어온 값을 다시 Spine 계약 안으로 들여오는 문입니다. 이 문이 느슨하면 raw payload의 혼란이 내부 모델까지 그대로 스며들고, 이 문이 엄격하면 외부 입력의 불확실성을 경계에서 차단할 수 있습니다.

## `to_payload()`

`to_payload()`는 Spine 객체를 JSON 호환 dict로 변환합니다.

```python
from spine import to_payload

payload = to_payload(metric)
```

변환 규칙:

- `StableRef`는 `"kind:value"` 문자열
- dataclass는 field 이름 기반 dict
- tuple은 JSON 친화 구조
- dict는 key 정렬

즉, `to_payload()`는 "모델 객체를 저장/전송 가능한 구조"로 바꾸는 단계입니다.

조금 더 구체적으로 보면 `to_payload()`는 다음 성질을 가집니다.

- `StableRef`는 항상 문자열 ref로 바뀜
- dataclass는 field 이름 기준으로 재귀적으로 펼쳐짐
- tuple은 JSON 친화적인 list로 바뀜
- dict는 key가 정렬된 순서로 나옴

즉 `to_payload()`는 단순 dump가 아니라 "canonical object를 JSON-compatible canonical shape로 내리는 단계"라고 보는 편이 정확합니다.

중요한 건 이 단계가 "파이썬 객체를 아무 식으로나 평평하게 만드는 것"이 아니라는 점입니다. Spine은 ref, nested dataclass, tuple, metadata dict를 모두 현재 canonical schema가 기대하는 형태로 정리해서 내보냅니다. 그래서 `to_payload()` 결과는 단순 중간 산출물이 아니라, 곧바로 fixture나 API payload의 기준형으로 삼을 수 있습니다.

## `to_json()`

`to_json()`은 `to_payload()` 결과를 안정적인 JSON 문자열로 인코딩합니다.

```python
from spine import to_json

encoded = to_json(metric)
```

이 함수는 다음 상황에서 특히 유용합니다.

- 저장 전 문자열 payload 생성
- fixture 비교
- 서명/해시 기준 문자열 생성
- 로그 출력

현재 구현은 `json.dumps(..., sort_keys=True, separators=(",", ":"))` 형태에 가깝기 때문에, key 순서가 정렬되고 불필요한 공백이 제거된 안정적인 JSON 문자열이 나옵니다. 따라서 사람이 읽기 좋은 pretty JSON보다는, 기계 비교와 저장 경계에 더 적합합니다.

즉 `to_json()`의 관심사는 표현 미학이 아니라 canonicality입니다. 같은 객체가 다시 직렬화될 때 같은 문자열을 얻을 수 있어야, 이후 해시 계산이나 fixture 비교가 의미를 갖기 때문입니다.

## `to_payload()`와 `to_json()`의 차이

### `to_payload()`

- dict를 반환
- 프로그램 내부 처리에 적합
- 후속 가공이 쉬움

### `to_json()`

- 문자열을 반환
- 전송/저장/출력에 적합
- 비교 대상이 명확함

실무에서는 보통:

- 내부 파이프라인: `to_payload()`
- 외부 경계나 저장: `to_json()`

패턴이 자연스럽습니다.

한 줄로 요약하면:

- `to_payload()`는 구조를 보존한 파이썬 값
- `to_json()`은 그 구조를 고정된 문자열 표현으로 만든 결과

## serialization 예시

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

`payload`는 대략 다음과 같은 dict가 됩니다.

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

그리고 `encoded = to_json(metric)` 는 같은 내용을 공백 없는 안정적인 JSON 문자열로 돌려줍니다.

즉 serialization 단계에서 중요한 건 "값을 잃지 않으면서도, 외부 경계에서 비교 가능한 일관된 표현으로 바꾸는 것"입니다.

## end-to-end로 보면 어떤 흐름인가

이 문서를 가장 실무적으로 읽는 방법은 Spine 객체가 다음 경로를 돈다고 생각하는 것입니다.

1. 애플리케이션 코드가 canonical object를 만든다
2. `to_payload()` 또는 `to_json()`으로 외부 표현을 만든다
3. 그 payload가 저장소, 네트워크, fixture 파일 같은 경계를 지난다
4. 나중에 `deserialize_*()`가 그 값을 다시 canonical object로 읽는다
5. 이때 schema, ref, timestamp, enum 계약이 다시 확인된다

즉 serialization/deserialization은 단순한 입출력 유틸리티가 아니라, Spine 계약이 시스템 바깥으로 나갔다가 다시 들어오는 왕복 경로입니다.

## deserialization

현재 스키마 payload를 읽을 때는 `deserialize_*` 계열 함수를 사용합니다.

예:

- `deserialize_project`
- `deserialize_run`
- `deserialize_artifact_manifest`
- `deserialize_metric_record`
- `deserialize_trace_span_record`

예시:

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

이 경로의 핵심은 입력이 raw dict라는 점입니다. deserializer는 이 raw payload를 그대로 신뢰하지 않고, ref 파싱과 객체 생성, validation을 거쳐야만 canonical object를 돌려줍니다.

이 차이는 굉장히 중요합니다. `to_payload()`가 만드는 값은 Spine 내부에서 나온 canonical payload이지만, `deserialize_*()`가 받는 값은 외부 세계가 건네준 미검증 입력입니다. 그래서 둘은 겉보기엔 반대 작업 같아도, 신뢰 모델은 전혀 다릅니다.

## deserializer가 하는 일

deserializer는 단순히 dict를 dataclass로 바꾸는 함수가 아닙니다. 내부적으로는 대체로 다음 일을 합니다.

1. raw payload에서 필드를 읽음
2. ref 문자열을 `StableRef`로 파싱
3. Spine 객체 생성
4. validation 수행
5. validation 실패 시 `SerializationError` 발생

즉, deserializer는 "읽기 + 계약 검증"을 함께 수행합니다.

현재 구현 관점에서 보면 대략 다음 흐름입니다.

1. 필수 ref는 `_parse_ref(...)` 로 읽음
2. `StableRef.parse(...)` 에 실패하면 즉시 `SerializationError`
3. 나머지 필드를 현재 schema 형태로 객체에 채움
4. validator를 호출해 contract 위반 여부 점검
5. validation 실패는 `SerializationError`로 다시 감싸서 반환

즉 deserializer는 "필드 매핑"보다 "현재 schema boundary enforcement"에 더 가깝습니다.

이 관점에서 보면 deserializer는 parser와 validator를 얇게 이어 붙인 함수가 아니라, 현재 schema의 문지기 역할을 하는 진입점입니다.

## 역직렬화 실패

다음 상황에서는 `SerializationError`가 날 수 있습니다.

- 필수 ref 누락
- ref 문자열 형식 오류
- validation 실패
- 현재 스키마에 맞지 않는 값

예를 들어 현재 스키마인데 `created_at`에 `Z`가 없으면 실패합니다.

조금 더 나누면 실패 지점은 보통 세 부류입니다.

- 구조 실패: 필수 필드/필수 ref 누락
- 파싱 실패: ref 문자열이 `kind:value` 형식이 아님
- 계약 실패: validation 규칙 위반

이 셋을 한데 묶어 `SerializationError`로 다루는 이유는, 외부 payload를 현재 canonical object로 읽는 경계에서 문제가 났다는 점이 더 중요하기 때문입니다.

예를 들어 실제로는 다음처럼 서로 다른 문제가 한 층에서 만납니다.

- `project_ref` 자체가 빠져 있음
- `project_ref`가 `project-nova`처럼 잘못된 ref 문자열임
- `created_at`이 `Z` 없이 들어와 validation에서 거절됨

원인은 다르지만, 사용자 입장에서는 모두 "현재 schema payload를 안전하게 읽지 못했다"는 같은 종류의 실패입니다. `SerializationError`는 이 경계 실패를 한 종류의 예외로 모아 다루게 해 줍니다.

## schema version의 의미

serialization/reading 경계에서 schema version은 매우 중요합니다.

- 현재 스키마 payload인지
- 현재 reader가 그대로 읽어도 되는지
- compatibility 경로를 타야 하는지

즉 schema version은 "이 payload를 어떤 계약으로 해석할지"를 알려주는 스위치입니다.

특히 같은 필드 이름이 남아 있어도 schema version이 다르면 의미가 달라질 수 있습니다. 그래서 Spine은 "비슷해 보이니 그냥 읽자"보다는 "어떤 버전 계약인지 먼저 확인하자" 쪽에 가깝습니다.

이 점은 문서 전체에서 가장 중요합니다. schema version은 부가 메타데이터가 아니라, payload를 읽는 규칙 자체를 선택하는 값입니다. 같은 JSON shape처럼 보여도 version contract가 다르면 같은 객체라고 가정하면 안 됩니다.

현재 스키마 입력만 처리한다면 deserializer를 쓰고, 구버전 입력까지 받아야 한다면 compatibility reader를 고려해야 합니다.

## serializer와 deserializer를 함께 볼 때의 직관

두 레이어는 서로 반대 방향으로 보이지만 역할이 완전히 대칭적인 것은 아닙니다.

- serializer는 canonical object를 외부 표현으로 내보내는 경계
- deserializer는 외부 표현을 canonical object로 들여오는 경계

하지만 들여오는 쪽이 더 위험하기 때문에 deserializer는 더 엄격합니다. 내보낼 때는 이미 canonical object라고 가정할 수 있지만, 들어오는 payload는 그렇지 않을 수 있기 때문입니다.

따라서 보통:

- 내부에서는 객체를 유지하고
- 경계에서만 `to_payload()` / `to_json()` / `deserialize_*()` 를 사용하며
- raw dict를 business logic에 바로 넘기지 않는 것이 가장 안전합니다

이 패턴을 지키면 내부 로직은 "항상 canonical object만 받는다"는 가정을 세울 수 있습니다. 반대로 raw dict가 안쪽까지 들어오면, 각 호출 지점마다 ref 형식, schema version, optional field 해석을 다시 고민해야 해서 코드 전체가 빠르게 불안정해집니다.

## 언제 deserializer를 쓰나

- 입력이 이미 현재 스키마라고 확신할 수 있을 때
- 계약 위반은 바로 실패시키고 싶을 때
- ingestion 경로를 엄격하게 통제하고 있을 때

반대로 다음 경우엔 일반 deserializer만으로는 부족합니다.

- producer 버전이 섞여 있을 때
- 저장소에 과거 schema payload가 남아 있을 때
- 필드 rename이나 timestamp 정규화가 필요한 과도기일 때

즉 일반 deserializer는 "현재 계약만 받겠다"는 선언에 가깝고, compatibility reader는 "과거 계약을 현재 계약으로 통역하겠다"는 경로라고 보면 이해하기 쉽습니다.

구버전 입력은 [호환성 및 마이그레이션](./compatibility-and-migrations.md)를 참고하세요.

## 추천 패턴

- 애플리케이션 내부에서는 Spine 객체 유지
- 외부 경계에서만 payload/JSON으로 변환
- 외부 입력은 raw dict로 바로 business logic에 넘기지 말고 deserializer를 통과

## 흔한 실수

### 1. `to_payload()` 결과를 비정규 dict처럼 임의 수정하기

serialization 결과를 중간에서 제멋대로 바꾸기 시작하면, 이후 deserializer나 downstream consumer가 기대하는 canonical shape가 흐트러질 수 있습니다.

특히 테스트를 빨리 맞추려고 payload 일부를 임의 patch하는 습관이 생기면, fixture는 통과해도 실제 schema contract와 어긋난 데이터가 쌓일 수 있습니다.

### 2. raw dict를 곧바로 비즈니스 로직에 넘기기

이 경우 schema/version/ref 형식 오류가 시스템 안쪽까지 들어와서 더 늦게, 더 불명확한 형태로 터질 수 있습니다.

이건 serialization 계층이 있는 라이브러리에서 가장 흔한 실수 중 하나입니다. 경계 검증을 생략하면 입구에서 막을 수 있었던 오류가 나중에 "왜 이 필드가 가끔 문자열이고 가끔 null이지?" 같은 식으로 퍼집니다.

### 3. 구버전 payload를 현재 deserializer에 바로 넣기

부분적으로 읽히는 것처럼 보여도 실제론 잘못 해석될 수 있습니다. 이런 입력은 compatibility reader 경로로 보내는 편이 맞습니다.

### 4. deterministic JSON을 사람이 읽기 좋은 pretty JSON과 혼동하기

Spine의 `to_json()`은 미관보다 안정성과 비교 가능성을 우선합니다. 사람이 읽기 좋은 출력이 필요하다면 그건 별도 표현 계층에서 다루는 편이 낫습니다.

## 왜 이 계층이 운영에서 중요한가

serialization/schema 경계가 단단하면 다음이 쉬워집니다.

- fixture 기반 회귀 테스트
- producer와 consumer 사이 계약 고정
- 장기 저장 payload의 재읽기 가능성 확보
- schema rollout 시점의 영향 범위 파악

반대로 이 계층이 흐리면 다음 문제가 생깁니다.

- 서비스마다 payload shape가 조금씩 달라짐
- 같은 객체가 실행마다 다른 JSON으로 나옴
- 구버전과 현재 버전이 조용히 섞임
- 실패가 경계가 아니라 시스템 안쪽에서 뒤늦게 터짐

즉 이 문서는 단순 serialization 사용법이 아니라, Spine contract가 외부 세계와 맞닿는 가장 중요한 경계를 설명하는 문서라고 보는 편이 맞습니다.

## 이 문서를 읽을 때 잡아야 할 핵심 직관

아주 짧게 요약하면 다음과 같습니다.

- `to_payload()`는 canonical object를 JSON-compatible canonical shape로 바꾼다
- `to_json()`은 그 shape를 안정적인 문자열로 고정한다
- `deserialize_*()`는 raw payload를 그냥 읽지 않고, 파싱과 validation을 거쳐 canonical object로 올린다
- schema version은 이 경계에서 어떤 계약을 써야 하는지 결정한다

한 문장으로 더 압축하면 이렇습니다.

"Spine의 serialization 레이어는 객체를 내보내는 형식을 고정하고, deserialization 레이어는 그 형식으로만 다시 들어오게 만든다."

## 다음 문서

- 구버전 입력 업그레이드는 [호환성 및 마이그레이션](./compatibility-and-migrations.md)
- 검증 규칙은 [검증 규칙](./validation-rules.md)
