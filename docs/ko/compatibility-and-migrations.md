# 호환성 및 마이그레이션

[사용자 가이드 홈](./README.md)

프로젝트를 오래 운영하다 보면 현재 schema만 다루는 시기는 생각보다 짧습니다. 이 문서는 과거 버전 payload를 현재 Spine 계약으로 안전하게 올릴 때 사용하는 compatibility reader와 migration 관점을 설명합니다.

이 페이지는 다음 질문에 답합니다.

- 왜 일반 deserializer와 별도 경로가 필요한가
- compatibility reader는 무엇을 반환하는가
- 어떤 상황에서 migration 경로를 써야 하는가

핵심은 단순히 "구버전도 읽는다"가 아닙니다. 처음 오는 사용자는 여기서 "과거 payload를 현재 contract로 가져올 때 무엇을 기록해야 하는가"를 이해하면 됩니다. Spine은 호환성을 숨겨진 편의 기능이 아니라, 추적 가능한 업그레이드 경로로 다룹니다.

## 왜 별도 compatibility 경로가 필요한가

실제 시스템에서는 payload가 항상 현재 스키마만 들어오지 않습니다.

예:

- 과거 버전 producer가 아직 살아 있음
- 저장된 historical payload를 다시 읽어야 함
- 팀 간 전송 중 예전 필드명이 계속 남아 있음

이 상황에서 현재 스키마 deserializer만 사용하면 두 가지 문제가 생깁니다.

- 너무 쉽게 깨짐
- 혹은 조용히 잘못 해석됨

compatibility reader는 이 두 문제 사이에서 "명시적 업그레이드"라는 경로를 제공합니다.

즉 Spine은 자동 마법을 지향하지 않습니다. legacy payload가 현재 schema와 다를 수 있다는 사실을 인정하고, 어떤 필드를 어떻게 바꿨는지 기록하면서 현재 계약으로 올리는 쪽을 택합니다.

## 현재 제공되는 reader

- `read_compat_project`
- `read_compat_artifact_manifest`

앞으로 스키마가 확장되면 여기에 더 많은 reader가 추가될 수 있습니다.

현재 구현 기준으로는 project와 artifact manifest에 대해 explicit compatibility 경로가 제공됩니다. 즉 Spine은 "모든 타입을 다 암묵적으로 호환 처리"하는 대신, 지원 범위를 명확히 드러내는 방식에 더 가깝습니다.

## CompatibilityResult

compatibility reader는 다음을 반환합니다.

- `value`: 현재 스키마로 변환된 객체
- `source_schema_version`: 원래 payload 버전
- `notes`: 어떤 필드 매핑과 업그레이드가 일어났는지 설명

이 구조가 중요한 이유는 "성공적으로 읽혔다"는 사실만큼 "어떤 보정이 있었는가"도 중요하기 때문입니다.

조금 더 풀면 `CompatibilityResult`는 세 질문에 답합니다.

- 무엇을 읽었는가: `value`
- 원래 어떤 버전이었는가: `source_schema_version`
- 현재 계약으로 오기까지 어떤 보정이 있었는가: `notes`

이 구조 덕분에 compatibility 경로는 단순 loader가 아니라 migration audit trail처럼 동작할 수 있습니다.

`notes`의 각 항목은 대체로 다음 형태로 이해하면 됩니다.

- `path`: 어떤 필드나 변환 지점에서
- `message`: 어떤 업그레이드나 매핑이 일어났는가

## 예시: legacy project 읽기

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

이 경우 reader는:

- `ref` -> `project_ref` 매핑
- `created` -> `created_at` 매핑
- timestamp 정규화
- schema version 업그레이드

그리고 `notes`에 그 사실을 남깁니다.

실제 읽기 결과를 개념적으로 쓰면 다음과 비슷합니다.

```text
value = Project(...)
source_schema_version = "0.9.0"
notes = [
  {path: "ref", message: "Mapped legacy 'ref' to 'project_ref'."},
  {path: "created", message: "Mapped legacy 'created' to 'created_at'."},
  {path: "schema_version", message: "Upgraded payload from 0.9.0 to 1.0.0."},
]
```

## 예시: legacy artifact 읽기

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

이 경우 reader는:

- legacy `hash`를 `hash_value`로 매핑
- schema version 업그레이드 note 생성

즉 artifact 경로에서는 "필드 rename" 같은 구체적 변환이 더 중요하게 드러납니다. 나중에 어떤 producer가 아직 옛 필드명을 쓰고 있는지 추적할 때 이 note가 그대로 운영 단서가 됩니다.

## deserializer와 compatibility reader의 차이

### deserializer

- 현재 스키마를 전제로 함
- 더 엄격함
- validation 실패 시 `SerializationError`

### compatibility reader

- 과거 스키마를 받아들일 수 있음
- 명시적 필드 매핑 수행
- 업그레이드 note 반환
- 지원하지 않는 버전은 `CompatibilityError`

한 줄로 정리하면:

- deserializer는 현재 계약만 받는 문
- compatibility reader는 과거 계약을 현재 계약으로 통역하는 문

이 둘을 섞지 않는 것이 중요합니다. 그래야 현재 schema 경계와 migration 경계가 흐려지지 않습니다.

## 언제 compatibility reader를 쓰나

- 입력 producer 버전이 섞여 있을 때
- historical payload를 읽어야 할 때
- migration 중간 단계에서 필드명이 공존할 때
- 어떤 자동 보정이 있었는지 기록해야 할 때

현재 스키마 입력만 받는다면 일반 deserializer가 더 적합합니다.

## compatibility reader가 실제로 하는 일

현재 구현을 기준으로 보면 compatibility reader는 대체로 다음 순서로 동작합니다.

1. 입력 payload의 `schema_version`을 읽음
2. 지원하는 버전인지 확인
3. legacy 필드명을 현재 필드명으로 매핑
4. timestamp 같은 값을 현재 정규 형식으로 정리
5. 현재 schema object 생성
6. 현재 validator로 다시 검증
7. 어떤 보정이 있었는지 `notes`에 기록

즉 compatibility 경로도 결국 목표는 현재 canonical object입니다. 차이는 그 객체를 만들기 전에 "버전 차이를 해소하는 단계"가 하나 더 있다는 점입니다.

## end-to-end로 보면 migration은 어떤 흐름인가

실무에서는 보통 다음 흐름으로 이해하는 편이 가장 자연스럽습니다.

1. 과거 producer나 historical store가 legacy payload를 내보낸다
2. compatibility reader가 version을 확인한다
3. legacy 필드와 형식을 현재 contract에 맞게 정리한다
4. 현재 canonical object를 만든다
5. validator로 현재 contract를 다시 확인한다
6. 어떤 업그레이드가 일어났는지 `notes`로 남긴다
7. 이후 단계는 current schema object만 다룬다

이 흐름의 핵심은 compatibility가 시스템 전체에 퍼지는 것이 아니라, 경계 한 지점에서 끝나야 한다는 점입니다. 경계 안쪽으로 들어온 뒤에는 가능한 한 모두가 같은 current schema object만 보게 만드는 것이 가장 안전합니다.

## 언제 migration을 시작했다고 봐야 하나

실무에서는 다음 중 하나라도 생기면 이미 migration 상태라고 보는 편이 맞습니다.

- producer 일부가 새 필드명을 쓰고 일부가 옛 필드명을 씀
- timestamp 형식이 세대별로 다름
- historical payload를 현재 분석 시스템에서 다시 읽어야 함
- schema rollout이 한 번에 끝나지 않고 장기간 공존 상태가 됨

이때 "일단 현재 deserializer에 넣어 보자"는 선택은 보통 장기적으로 더 큰 혼란을 만듭니다. migration 상태라면 migration 경로를 문서화하고 compatibility note를 남기는 편이 훨씬 안전합니다.

## migration을 운영 관점에서 어떻게 읽을까

compatibility note는 단순한 부가 로그가 아니라 rollout 상태를 읽는 센서처럼 쓸 수 있습니다.

예를 들어:

- 특정 producer에서만 `ref -> project_ref` note가 계속 뜬다
- 특정 artifact 입력에서만 `hash -> hash_value` note가 반복된다
- timestamp 정규화 note가 특정 파이프라인에 집중된다

이 패턴은 곧 "어디에 아직 구버전 계약이 남아 있는가"를 보여 줍니다. 즉 compatibility layer는 읽기 도구이면서 동시에 migration 관측 도구이기도 합니다.

## 어떤 전략으로 rollout하는가

실무적으로는 보통 다음 세 전략 중 하나를 택하게 됩니다.

### 1. strict cutover

한 시점 이후 구버전 입력을 전부 거절합니다.

장점:

- 운영이 단순함
- current schema 경계가 분명함

단점:

- producer 동기화가 완벽하지 않으면 장애로 이어지기 쉬움

### 2. bounded compatibility

일정 기간 동안만 compatibility reader를 운영합니다.

장점:

- 현실적인 rollout에 잘 맞음
- migration note로 상태를 추적 가능

단점:

- 종료 시점을 관리하지 않으면 기술 부채로 남기 쉬움

### 3. long-tail historical support

historical backfill이나 감사 요구 때문에 오래된 버전도 계속 읽습니다.

장점:

- 장기 저장 데이터 활용이 쉬움

단점:

- 호환 규칙이 복잡해질 수 있음
- reader가 사실상 버전 박물관이 되기 쉬움

Spine의 현재 방향은 보통 두 번째 전략과 가장 잘 맞습니다. 즉 필요한 동안 명시적으로 운영하고, note와 fixture를 근거로 점진적으로 종료하는 방식이 자연스럽습니다.

## migration 운영 팁

- compatibility note를 로깅하면 아직 남아 있는 구버전 producer를 추적하기 쉽습니다.
- 업그레이드가 많이 발생하는 필드는 schema rollout 상태를 보여주는 지표가 될 수 있습니다.
- compatibility 경로를 오래 유지해야 한다면, 테스트 fixture도 버전별로 관리하는 편이 좋습니다.

추가로 다음 원칙도 도움이 됩니다.

- compatibility reader는 가능한 한 버전별 규칙을 작고 명시적으로 유지
- 지원 종료 시점을 팀 안에서 정하고, 무기한 호환을 기본값으로 두지 않기
- note가 쌓이는 패턴을 migration backlog와 연결하기

즉 compatibility는 영구 기능이라기보다, 안전한 전환을 위한 운영 장치에 가깝습니다.

## 언제 compatibility 경로를 걷어낼까

이 질문도 중요합니다. 호환 경로는 유용하지만, 너무 오래 남기면 현재 계약이 아니라 과거 계약들의 박물관이 되기 쉽습니다.

보통 다음 조건이 맞으면 축소를 검토할 수 있습니다.

- 더 이상 구버전 producer가 없음
- historical backfill이 끝남
- compatibility note 발생 빈도가 충분히 낮아짐
- 관련 fixture와 rollout 문서가 정리됨

즉 compatibility 경로는 "있으면 안전하다"가 아니라, "필요한 동안만 명시적으로 운영한다"는 태도가 더 건강합니다.

실무적으로는 "더 이상 필요 없어 보인다"는 느낌보다, 명확한 종료 조건을 미리 정해 두는 편이 좋습니다.

예:

- 30일 이상 compatibility note가 거의 발생하지 않음
- 모든 공식 producer가 current schema 배포 완료
- historical 재처리 작업 종료
- 관련 fixture가 current schema 기준으로 정리됨

이런 기준이 있어야 compatibility가 임시 경로에서 영구 경로로 변질되지 않습니다.

## 흔한 실수

### 1. 구버전 입력도 그냥 deserializer에 넣기

이 경우 깨지거나, 더 나쁘게는 잘못 읽힐 수 있습니다.

### 2. compatibility 경로에서 무슨 매핑이 일어났는지 기록하지 않기

성공 여부만 보면 migration 진행 상태를 알기 어렵습니다.

### 3. 너무 많은 스키마 버전을 한 reader에 무질서하게 섞기

버전별 규칙은 명확하게 관리하는 편이 좋습니다.

### 4. compatibility note를 무시하고 성공 여부만 보기

성공은 했지만 계속 업그레이드가 일어나는 상태라면, migration은 아직 끝나지 않은 것입니다.

### 5. compatibility reader를 현재 schema의 일반 입구처럼 사용하기

이렇게 되면 현재 계약과 migration 계약의 경계가 흐려지고, 어떤 입력이 정말 current payload인지 판단하기 어려워집니다.

### 6. migration 규칙보다 "운 좋게 읽히는지"에 의존하기

필드가 우연히 겹친다고 해서 같은 계약이라고 보면, 가장 위험한 종류의 조용한 오해가 생깁니다.

## current schema로 올린 뒤에는 무엇을 해야 하나

compatibility reader의 목표는 migration 상태를 시스템 전체로 전파하는 것이 아닙니다. 목표는 current schema object를 만드는 것입니다.

따라서 보통은:

- compatibility reader에서 current object를 얻고
- 이후 business logic, validation 결과 처리, serialization 경계는
- 가능한 한 모두 current schema 기준으로만 다루는 편이 좋습니다

즉 migration은 시스템 내부의 기본 상태가 아니라, 경계에서 끝내야 하는 번역 작업에 가깝습니다.

## 이 문서를 읽을 때 잡아야 할 핵심 직관

아주 짧게 요약하면 다음과 같습니다.

- compatibility reader는 구버전 입력을 현재 schema object로 올리는 명시적 통역 계층이다
- 성공적으로 읽었다는 사실만큼 어떤 업그레이드가 있었는지도 중요하다
- migration 상태에서는 strict deserializer보다 compatibility 경로가 더 안전할 수 있다
- 호환성은 영구 마법이 아니라, 추적 가능하고 종료 가능한 운영 경로여야 한다

## 다음 문서

- 현재 스키마 읽기는 [직렬화와 스키마](./serialization-and-schema.md)
- 확장 정책은 [확장과 커스텀 필드](./extensions-and-custom-fields.md)
