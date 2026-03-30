# 확장과 커스텀 필드

[사용자 가이드 홈](./README.md)

Spine을 실제 팀에 도입하면, 표준 모델만으로는 아직 담기지 않는 팀별 메타데이터가 거의 항상 생깁니다. 이 문서는 그런 값을 extension으로 다뤄야 할 때 무엇을 넣고 무엇은 넣지 말아야 하는지 설명합니다.

처음 쓰는 사용자라면 extension을 "자유 필드"가 아니라 "공용 계약을 깨지 않으면서 팀별 의미를 얹는 통제된 확장 포인트"로 이해하면 가장 정확합니다.

## 왜 extension이 필요한가

실무 시스템에서는 표준 필드만으로 모든 의미를 담기 어렵습니다.

예:

- 조직별 owner 정보
- 내부 우선순위
- 배포 승인 상태
- 사내 정책 분류

하지만 이런 필드를 아무 제약 없이 top-level에 추가하면 공용 계약이 빠르게 무너집니다. Spine은 이를 피하기 위해 확장을 별도 구조로 분리합니다.

즉 extension은 core schema를 대신하는 공간이 아니라, core schema를 보호하면서도 실무 요구를 수용하는 완충지대입니다.

## ExtensionFieldSet

객체에 부착하는 실제 확장 데이터 단위입니다.

```python
from spine import ExtensionFieldSet

ext = ExtensionFieldSet(
    namespace="ml.team",
    fields={
        "owner": "research-platform",
        "priority": "high",
    },
)
```

규칙:

- namespace에는 반드시 `.` 포함
- fields는 내부적으로 key 정렬

즉, extension도 완전히 자유로운 dict가 아니라 최소한의 거버넌스를 전제로 합니다.

payload로 보면 보통 다음처럼 보입니다.

```json
{
  "namespace": "ml.team",
  "fields": {
    "owner": "research-platform",
    "priority": "high"
  }
}
```

그리고 이 값은 `Project`, `Run`, `StageExecution`, `RecordEnvelope`, `ArtifactManifest`, `LineageEdge`, `ProvenanceRecord` 같은 여러 canonical object의 `extensions` 필드에 붙을 수 있습니다. 즉 extension은 특정 한 타입 전용이 아니라, Spine 전반에 걸쳐 공통으로 부착 가능한 governed metadata 단위입니다.

예를 들어 artifact에 붙이면 다음처럼 쓸 수 있습니다.

```python
from spine import ArtifactManifest, ExtensionFieldSet, StableRef

artifact = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=StableRef("stage", "train"),
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
    extensions=(
        ExtensionFieldSet(
            namespace="ml.team",
            fields={"owner": "research-platform", "priority": "high"},
        ),
    ),
)
```

즉 extension은 "특정 타입만의 특수한 별도 구조"가 아니라, 공통 모델 위에 같은 방식으로 얹는 부가 의미 계층입니다.

## ExtensionRegistry

namespace 소유권을 관리하는 레지스트리입니다.

```python
from spine import ExtensionRegistry

registry = ExtensionRegistry()
registry.register("ml.team", owner="research-platform")
```

주요 메서드:

- `register(namespace, owner)`
- `is_registered(namespace)`
- `owner_for(namespace)`

다른 owner가 이미 등록한 namespace를 재등록하려 하면 `ExtensionError`가 발생합니다.

현재 코드 기준으로 registry는 namespace 소유권을 관리하는 명시적 유틸리티입니다. 즉 "어떤 namespace를 누가 관리하는가"를 추적하는 역할은 하지만, 모든 extension 부착 시점에 자동으로 강제되는 전역 정책 엔진이라기보다는 팀이 거버넌스를 운영하기 위한 기반 도구에 가깝습니다. 이 점은 현재 구현을 기준으로 한 설명입니다.

## 언제 extension을 써야 하나

- 표준 스키마에 아직 없는 팀별 메타데이터가 필요할 때
- 바로 core schema에 넣기엔 범용성이 아직 불명확할 때
- 소유 조직과 namespace를 분명히 나누고 싶을 때

예를 들어:

- 팀 내부 owner
- 내부 운영 priority
- 실험 분류용 사내 태그

이런 값은 extension으로 시작하는 것이 자연스럽습니다.

실무적으로는 다음 질문이 도움이 됩니다.

- 이 정보가 우리 팀에만 중요한가
- 아직 공용 schema로 승격할 만큼 안정적인가
- consumer 일부만 이해해도 되는가

셋 다 "예"에 가깝다면 extension이 좋은 후보입니다.

## 언제 extension을 피해야 하나

- 이미 표준 필드로 표현 가능한 경우
- 모든 consumer가 반드시 이해해야 하는 핵심 의미인 경우
- 관계나 artifact 같은 더 적절한 모델이 이미 존재하는 경우

즉, extension은 "아직 표준이 아닌 정보"를 위한 공간이지, core 모델을 우회하는 통로가 되어서는 안 됩니다.

예를 들어:

- `run_ref`가 이미 있는데 다른 이름의 실행 식별자를 extension으로 넣는 것
- lineage relation이 필요한데 문자열 설명을 extension에만 넣는 것
- 모든 consumer가 알아야 하는 핵심 상태를 extension으로 숨기는 것

이런 패턴은 확장이 아니라 core schema 회피에 가깝습니다.

## extension, attribute, tag는 어떻게 다를까

이 질문은 실무에서 자주 나옵니다. 대략 다음처럼 생각하면 편합니다.

### core field

Spine 계약의 중심 의미입니다.

- 모든 consumer가 공통으로 이해해야 함
- validator와 schema가 직접 의미를 가짐

### object-specific metadata

예를 들어 artifact의 `attributes`나 project의 `tags`처럼, 특정 타입 안에서 이미 허용된 보조 정보입니다.

- 해당 타입의 문맥 안에서만 해석됨
- 별도 namespace는 없음

### extension

여러 타입에 걸쳐 부착 가능한, namespace 기반의 팀별 확장입니다.

- ownership을 분리하고 싶을 때 적합
- 아직 core schema로 올리기 이른 의미를 담기 좋음

즉 "그 객체 타입 안에서만 자연스러운 보조 값인가"와 "팀 단위 namespace가 필요한가"가 extension 여부를 가르는 좋은 기준입니다.

## 추천 운영 방식

### 1. namespace를 조직/도메인 기준으로 잡기

예:

- `ml.team`
- `serving.platform`
- `risk.policy`

가능하면 namespace는 오래 살아도 어색하지 않은 단위로 잡는 편이 좋습니다. 일시적인 프로젝트명이나 개인 이름을 namespace에 넣기 시작하면, 시간이 지나며 ownership이 불분명해지고 정리 비용이 커집니다.

### 2. 확장에서 먼저 운영하고, 필요하면 표준 필드로 승격

이 방식이 바로 core schema에 넣는 것보다 안전합니다.

즉 extension은 종종 "실험 공간" 역할도 합니다. 충분히 널리 쓰이고 의미가 안정되면 core schema 승격 후보가 되고, 그렇지 않으면 팀 로컬 의미로 남을 수 있습니다.

### 3. 같은 의미를 여러 namespace에 중복 정의하지 않기

owner 정보를 여러 namespace로 흩뿌리면 표준화 이점이 사라집니다.

## extension을 설계할 때의 직관

좋은 extension은 다음 특징을 가집니다.

- namespace만 봐도 누가 책임지는지 짐작 가능
- field 이름이 그 namespace 안에서 일관됨
- core schema와 역할 충돌이 적음
- consumer가 몰라도 기본 해석이 크게 깨지지 않음

반대로 나쁜 extension은 다음과 비슷합니다.

- namespace가 너무 넓거나 모호함
- 같은 의미를 다른 namespace에 반복
- 핵심 관계나 identity를 extension으로 우회
- 시간이 지나도 승격/정리 기준이 없음

## extension을 언제 core schema로 올릴까

다음 조건이 맞으면 승격을 검토할 만합니다.

- 여러 팀이 같은 의미로 사용
- consumer 대부분이 그 필드를 공통으로 이해해야 함
- 더 이상 "팀별 예외"가 아니라 계약의 일부가 됨
- extension namespace별 해석 차이가 오히려 혼란을 만들기 시작함

즉 extension은 영구 보관함이 아니라, 필요하면 core schema 후보를 incubate하는 공간이기도 합니다.

## 운영에서 extension을 잘 쓰는 패턴

다음 패턴이 보통 안정적입니다.

### namespace별 owner를 분명히 두기

누가 필드 의미를 정의하고 바꿀 수 있는지 모르면, extension은 곧바로 공용 잡동사니 필드가 됩니다.

### field vocabulary를 짧게 문서화하기

예를 들어 `ml.team.priority`를 쓴다면 `high/medium/low` 같은 허용 vocabulary를 팀 안에서 정해 두는 편이 좋습니다.

### consumer fallback을 설계하기

consumer가 특정 namespace를 모를 때도 기본 동작이 크게 깨지지 않아야 합니다. extension은 "알면 더 풍부해지는 정보"에 가까울수록 안전합니다.

### 승격 또는 폐기 기준을 미리 정하기

계속 쓰여서 core schema 후보가 될지, 아니면 특정 프로젝트 종료와 함께 사라질지를 정해 두면 extension sprawl을 줄이기 쉽습니다.

## 흔한 실수

### 1. extension을 자유 필드 보관함처럼 쓰기

이렇게 되면 namespace는 있어도 실제로는 아무 거버넌스가 없는 상태가 됩니다.

### 2. namespace를 너무 짧거나 모호하게 짓기

누가 소유하는지 불명확해지고 나중에 충돌이 나기 쉽습니다.

### 3. 핵심 의미를 extension에만 넣기

모든 consumer가 이해해야 하는 정보라면 core schema 쪽이 더 자연스러울 수 있습니다.

### 4. registry 없이 namespace를 관습으로만 관리하기

작은 팀에선 버틸 수 있어도, 조직이 커질수록 ownership 충돌과 중복 정의가 빠르게 늘어납니다.

### 5. consumer가 이해하지 못하면 깨지는 의미를 extension에 넣기

extension은 보조 의미에 더 가깝습니다. 모르는 namespace가 있다고 해서 기본 해석이 무너지면, 사실 그건 core field 후보일 가능성이 큽니다.

## 이 문서를 읽을 때 잡아야 할 핵심 직관

아주 짧게 요약하면 다음과 같습니다.

- extension은 공용 계약을 깨지 않으면서 팀별 의미를 수용하는 governed escape hatch다
- namespace는 ownership과 충돌 방지를 위한 핵심 장치다
- extension은 core schema를 대체하는 공간이 아니라, 필요하면 core 승격 전 단계가 될 수 있다
- 좋은 extension 운영은 필드 추가보다 거버넌스 설계에 더 가깝다

## 다음 문서

- 실제 조립 흐름은 [워크플로 예제](./workflow-examples.md)
- 타입 구조는 [컨텍스트 모델](./context-models.md), [관측 레코드](./observability-records.md), [산출물과 계보](./artifacts-and-lineage.md)
