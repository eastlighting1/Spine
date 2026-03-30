# 산출물과 계보

[사용자 가이드 홈](./README.md)

Spine은 실행 중 남는 event와 metric만 다루는 라이브러리가 아닙니다. 모델 체크포인트, 평가 리포트, feature snapshot 같은 실행 결과물과 그들 사이의 관계도 함께 다룰 수 있습니다. 이 문서는 그때 사용하는 `ArtifactManifest`, `LineageEdge`, `ProvenanceRecord`를 설명합니다.

처음 읽을 때는 다음 두 가지를 먼저 잡으면 됩니다.

1. artifact는 단순 파일 메타데이터가 아니라 실행 결과물이라는 점
2. lineage는 문자열 설명이 아니라 별도 모델로 남겨야 한다는 점

## 왜 산출물과 계보를 별도 계층으로 두나

실행 중에 metric과 event만 남겨도 시스템은 어느 정도 돌아갑니다. 하지만 ML 시스템에서는 곧 이런 질문이 생깁니다.

- 이 체크포인트는 어떤 run의 결과인가
- 이 리포트는 어떤 stage에서 생성됐는가
- 이 모델은 어떤 dataset이나 이전 artifact에서 유도됐는가
- 이 관계는 명시적인가, 아니면 추론된 것인가

이 질문에 답하려면 단순 파일 경로나 설명 문자열만으로는 부족합니다. 그래서 Spine은 산출물과 관계를 별도 모델로 둡니다.

조금 더 직설적으로 말하면:

- 관측 레코드는 "실행 중 무슨 일이 있었는가"를 남기고
- artifact는 "실행 결과 무엇이 남았는가"를 남기며
- lineage는 "그 결과물이 무엇에서 왔는가"를 남깁니다

ML 시스템에서 재현성, 배포 추적, 평가 비교가 어려워지는 이유는 대개 세 번째 축이 빠져 있기 때문입니다. 파일은 남아 있어도 그 파일이 어떤 데이터, 어떤 실행, 어떤 이전 결과물과 연결되는지가 구조화되어 있지 않으면 결국 사람 기억과 운영 문서에 의존하게 됩니다.

## ArtifactManifest

`ArtifactManifest`는 모델 체크포인트, 평가 리포트, feature snapshot, exported dataset 같은 산출물을 표현합니다.

주요 필드:

- `artifact_ref`
- `artifact_kind`
- `created_at`
- `producer_ref`
- `run_ref`
- `stage_execution_ref`
- `location_ref`
- `hash_value`
- `size_bytes`
- `attributes`
- `schema_version`
- `extensions`

예시:

```python
from spine import ArtifactManifest, StableRef

checkpoint = ArtifactManifest(
    artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
    artifact_kind="checkpoint",
    created_at="2026-03-30T09:20:00Z",
    producer_ref="scribe.python.local",
    run_ref=StableRef("run", "train-20260330-01"),
    stage_execution_ref=StableRef("stage", "train"),
    location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
    hash_value="sha256:abc123",
    size_bytes=184223744,
    attributes={"framework": "pytorch", "dtype": "float16"},
)
```

payload 형태는 대략 다음처럼 보입니다.

```json
{
  "artifact_kind": "checkpoint",
  "artifact_ref": "artifact:checkpoint-epoch-1",
  "attributes": {
    "dtype": "float16",
    "framework": "pytorch"
  },
  "created_at": "2026-03-30T09:20:00Z",
  "extensions": [],
  "hash_value": "sha256:abc123",
  "location_ref": "file://artifacts/checkpoints/epoch_1.ckpt",
  "producer_ref": "scribe.python.local",
  "run_ref": "run:train-20260330-01",
  "schema_version": "1.0.0",
  "size_bytes": 184223744,
  "stage_execution_ref": "stage:train"
}
```

### ArtifactManifest가 단순 파일 메타데이터가 아닌 이유

Spine에서 artifact는 단순 파일 포인터가 아닙니다. 다음을 함께 설명하는 객체입니다.

- 어떤 실행에서 생성됐는가
- 어느 stage에서 나왔는가
- 누가 생성했는가
- 어디 저장됐는가
- 무결성 정보는 무엇인가

즉 artifact는 "어딘가의 파일"이 아니라 "설명 가능한 실행 결과물"입니다.

artifact를 별도 모델로 두면 좋은 점은 파일이 이동하거나 저장소가 바뀌어도 identity와 실행 맥락이 분리되어 남는다는 것입니다. 위치는 바뀔 수 있지만, "이 artifact가 무엇이었는가"는 바뀌지 않아야 하기 때문입니다.

### ArtifactManifest가 답하는 질문

- 어떤 run에서 생성됐는가
- 어떤 stage에서 나왔는가
- 저장 위치는 어디인가
- checksum과 크기는 무엇인가
- artifact의 종류는 무엇인가

### `artifact_kind`를 어떻게 생각하면 좋은가

`artifact_kind`는 artifact의 역할을 나타냅니다.

예:

- `checkpoint`
- `report`
- `dataset`
- `feature_snapshot`

이 값은 소비자가 artifact를 어떤 종류의 결과물로 해석할지 결정하는 데 중요합니다.

가능하면 팀 안에서 `artifact_kind` 어휘를 좁게 유지하는 편이 좋습니다. 예를 들어 `checkpoint`, `model_checkpoint`, `training_checkpoint`, `ckpt`를 모두 섞어 쓰기 시작하면, 같은 종류의 artifact를 소비자마다 따로 해석해야 하는 문제가 생깁니다.

좋은 방향은:

- 적은 수의 안정적인 kind를 유지하고
- 세부 차이는 `attributes`로 보강하며
- 정말 공통 의미가 커졌을 때만 새로운 kind를 추가하는 것입니다

### `attributes`는 언제 쓰나

artifact에 붙는 부가 정보를 넣을 수 있습니다.

예:

- `framework: pytorch`
- `dtype: float16`
- `split: validation`

다만 모든 의미를 `attributes`에 몰아넣기보다, 핵심 구조는 top-level 필드로 두는 것이 좋습니다.

실무적으로는 다음처럼 나누면 이해하기 쉽습니다.

- top-level 필드: 거의 모든 consumer가 공통으로 이해해야 하는 구조
- `attributes`: artifact 종류별로 달라질 수 있는 보조 메타데이터

예를 들어 artifact가 어디에 있고 어떤 실행에서 생성됐는지는 top-level에 있어야 하지만, 모델 프레임워크나 데이터 split 같은 값은 `attributes`에 두는 편이 자연스럽습니다.

### `location_ref`, `hash_value`, `size_bytes`

이 세 필드는 artifact를 운영 가능한 객체로 만들어 줍니다.

#### `location_ref`

artifact가 현재 어디 있는지를 가리킵니다.

예:

- `file://...`
- object storage URI
- 내부 registry 주소

중요한 점은 `location_ref`가 artifact의 정체성 자체는 아니라는 점입니다. location은 바뀔 수 있지만 `artifact_ref`는 가능한 한 안정적으로 유지되는 편이 좋습니다.

#### `hash_value`

무결성 확인과 동일성 비교에 유용합니다.

예를 들어 같은 이름의 checkpoint 두 개가 있어도 hash가 다르면 다른 결과물일 수 있습니다. 반대로 위치가 바뀌어도 hash가 같으면 동일한 바이너리인지 빠르게 확인할 수 있습니다.

#### `size_bytes`

겉보기에는 단순 부가 정보 같지만, 운영에서는 꽤 쓸모가 있습니다.

예:

- 저장 비용 추적
- artifact 생성 이상 탐지
- 비정상적으로 작은 결과물 조기 발견

즉 이 세 필드는 "어디 있나, 같은 건가, 정상적인 크기인가"를 빠르게 판단하게 해 줍니다.

## LineageEdge

`LineageEdge`는 두 ref 사이의 의미적 관계를 표현합니다.

주요 필드:

- `relation_ref`
- `relation_type`
- `source_ref`
- `target_ref`
- `recorded_at`
- `origin_marker`
- `confidence_marker`
- `operation_context_ref`
- `evidence_refs`
- `schema_version`
- `extensions`

허용 relation type:

- `generated_from`
- `consumed_by`
- `produced_by`
- `packaged_from`
- `reported_by`
- `evaluated_on`
- `deployed_from`
- `used`
- `derived_from`
- `observed_in`

### LineageEdge는 무엇을 표현하나

간단히 말해 "A와 B 사이에 어떤 의미적 연결이 있는가"를 표현합니다.

예시 해석:

- checkpoint artifact가 dataset에서 `generated_from`
- metric report가 run에 의해 `reported_by`
- serving model이 training artifact에서 `deployed_from`

예시 코드:

```python
from spine import LineageEdge, StableRef

edge = LineageEdge(
    relation_ref=StableRef("relation", "checkpoint-from-dataset"),
    relation_type="generated_from",
    source_ref=StableRef("artifact", "dataset-train-v3"),
    target_ref=StableRef("artifact", "checkpoint-epoch-1"),
    recorded_at="2026-03-30T09:21:00Z",
    origin_marker="pipeline_declared",
    confidence_marker="high",
    operation_context_ref=StableRef("op", "train-step"),
    evidence_refs=("record:trace-forward-001", "artifact:report-eval-01"),
)
```

payload로 보면 다음과 비슷합니다.

```json
{
  "confidence_marker": "high",
  "evidence_refs": [
    "record:trace-forward-001",
    "artifact:report-eval-01"
  ],
  "extensions": [],
  "operation_context_ref": "op:train-step",
  "origin_marker": "pipeline_declared",
  "recorded_at": "2026-03-30T09:21:00Z",
  "relation_ref": "relation:checkpoint-from-dataset",
  "relation_type": "generated_from",
  "schema_version": "1.0.0",
  "source_ref": "artifact:dataset-train-v3",
  "target_ref": "artifact:checkpoint-epoch-1"
}
```

### 왜 relation을 별도 모델로 두나

다음처럼 문자열 설명만 남길 수도 있습니다.

```text
"this model was derived from dataset-x"
```

하지만 이런 방식은 사람이 읽는 데는 괜찮아도 시스템이 이해하고 질의하기엔 불리합니다.

반면 `LineageEdge`로 남기면:

- source/target가 구조화됨
- relation type이 정규화됨
- lineage query와 시각화가 쉬워짐

그리고 더 중요한 차이는 relation이 "나중에 다시 계산되거나 교체될 수 있는 해석"이라는 점입니다. artifact 자체는 비교적 안정적인 사실이지만, 두 artifact 사이의 관계는 규칙이 바뀌거나 근거가 추가되면 더 정교해질 수 있습니다. 그래서 artifact와 lineage를 분리해 두는 편이 장기적으로 훨씬 유연합니다.

### source와 target을 어떻게 생각하면 좋은가

relation마다 읽는 방향이 중요합니다.

예:

- `generated_from`: target이 source에서 생성됨
- `deployed_from`: target이 source에서 배포됨

따라서 lineage를 설계할 때는 relation type뿐 아니라 방향도 일관되게 정하는 것이 중요합니다.

이 일관성이 없으면 나중에 lineage graph를 읽을 때 같은 관계를 어떤 edge는 좌에서 우로, 어떤 edge는 우에서 좌로 해석해야 하는 문제가 생깁니다. 그래서 relation type을 정할 때는 "문장을 어떻게 읽는가"까지 팀 안에서 합의해 두는 편이 좋습니다.

실무적으로는 relation type마다 읽는 문장을 먼저 정하는 방식이 가장 덜 헷갈립니다.

예:

- `target generated_from source`
- `target deployed_from source`
- `target evaluated_on source`

이 규칙을 먼저 정해 두면, 새 edge를 만들 때도 source/target을 자동으로 맞추기 쉬워집니다.

### relation type을 어떻게 고를까

relation type은 "두 객체가 연결돼 있다"는 사실보다, 그 연결이 어떤 의미인가를 드러내야 합니다.

예를 들어 checkpoint와 dataset 사이 관계를 남긴다고 해도:

- 학습 결과라면 `generated_from`
- 단순히 읽어서 사용했다면 `used`
- 평가가 특정 dataset을 기준으로 이뤄졌다면 `evaluated_on`

처럼 선택이 달라질 수 있습니다.

즉 relation type은 단순 연결 라벨이 아니라, 이후 질의와 해석을 결정하는 핵심 의미 필드입니다.

### `origin_marker`, `confidence_marker`, `evidence_refs`

이 세 필드는 lineage를 단순 연결선이 아니라 "해석 가능한 주장"으로 바꿔 줍니다.

#### `origin_marker`

이 관계가 어떤 경로로 만들어졌는지를 나타냅니다.

예:

- 파이프라인 코드가 명시적으로 선언
- 외부 카탈로그에서 수입
- 분석기가 후처리로 생성

#### `confidence_marker`

이 관계를 얼마나 강하게 믿을 수 있는지를 표현합니다.

explicit lineage와 inferred lineage를 동일한 신뢰도로 다루면 운영 판단이 흔들릴 수 있기 때문에, confidence 표시는 생각보다 중요합니다.

예를 들어:

- 파이프라인이 직접 남긴 `generated_from` 관계는 `high`
- 로그 상관분석으로 추정한 관계는 `medium`
- 약한 휴리스틱으로 만든 관계는 `low`

처럼 운용할 수 있습니다. 문서상으로 값 집합이 고정돼 있지는 않더라도, 팀 내부에서는 일관된 confidence vocabulary를 두는 편이 좋습니다.

#### `evidence_refs`

관계를 뒷받침하는 추가 ref들입니다.

예:

- 관계를 생성한 trace span
- 관계를 설명하는 report artifact
- 관계를 입증하는 별도 record

즉 `LineageEdge`는 "dataset A에서 model B가 나왔다"는 결론을 담고, `evidence_refs`는 "왜 그렇게 판단했는가"를 따라가는 실마리를 제공합니다.

여기서 중요한 건 evidence가 lineage 그 자체를 대체하지는 않는다는 점입니다. evidence만 많이 쌓아도 핵심 relation이 구조화돼 있지 않으면 소비자는 다시 증거를 하나씩 해석해야 합니다. Spine은 먼저 관계를 분명히 남기고, evidence는 그 관계를 뒷받침하는 보조 층으로 두는 쪽에 가깝습니다.

## ProvenanceRecord

`ProvenanceRecord`는 lineage assertion의 근거와 형성 맥락을 설명하는 타입입니다.

주요 필드:

- `provenance_ref`
- `relation_ref`
- `formation_context_ref`
- `policy_ref`
- `evidence_bundle_ref`
- `assertion_mode`
- `asserted_at`
- `schema_version`
- `extensions`

허용 assertion mode:

- `explicit`
- `imported`
- `inferred`

즉, `LineageEdge`가 "무슨 관계인가"를 말한다면, `ProvenanceRecord`는 "그 관계를 왜 그렇게 판단했는가"를 말합니다.

### assertion mode의 의미

- `explicit`: 시스템이나 사용자가 명시적으로 선언
- `imported`: 외부 시스템에서 가져옴
- `inferred`: 규칙이나 분석 결과로 추론

이 구분은 매우 중요합니다. 같은 lineage라도 explicit와 inferred는 신뢰 수준과 해석 방식이 다를 수 있기 때문입니다.

예시 코드:

```python
from spine import ProvenanceRecord, StableRef

provenance = ProvenanceRecord(
    provenance_ref=StableRef("provenance", "prov-checkpoint-from-dataset"),
    relation_ref=StableRef("relation", "checkpoint-from-dataset"),
    formation_context_ref=StableRef("op", "lineage-builder"),
    policy_ref="policy:lineage-min-confidence-v1",
    evidence_bundle_ref="bundle:evidence-checkpoint-01",
    assertion_mode="inferred",
    asserted_at="2026-03-30T09:21:05Z",
)
```

payload 관점에서는 다음과 같습니다.

```json
{
  "asserted_at": "2026-03-30T09:21:05Z",
  "assertion_mode": "inferred",
  "evidence_bundle_ref": "bundle:evidence-checkpoint-01",
  "extensions": [],
  "formation_context_ref": "op:lineage-builder",
  "policy_ref": "policy:lineage-min-confidence-v1",
  "provenance_ref": "provenance:prov-checkpoint-from-dataset",
  "relation_ref": "relation:checkpoint-from-dataset",
  "schema_version": "1.0.0"
}
```

`ProvenanceRecord`가 중요한 이유는 lineage edge만으로는 "관계가 있다"는 사실만 남고, 그 관계가 어떤 정책, 어떤 형성 맥락, 어떤 근거 묶음 위에서 만들어졌는지는 남지 않기 때문입니다.

### `formation_context_ref`, `policy_ref`, `evidence_bundle_ref`

이 세 필드는 provenance를 운영 가능한 기록으로 바꿔 줍니다.

#### `formation_context_ref`

이 provenance가 어떤 작업 흐름에서 형성됐는지를 가리킵니다.

예:

- lineage builder 작업
- catalog import job
- audit reconciliation step

#### `policy_ref`

어떤 규칙이나 정책 아래에서 관계가 인정되었는지를 설명합니다.

이 값이 있으면 "왜 이 관계는 accepted 되었고 저 관계는 rejected 되었는가"를 나중에 정책 단위로 추적하기 쉬워집니다.

#### `evidence_bundle_ref`

여러 근거를 하나의 묶음으로 가리킬 때 유용합니다. 개별 `evidence_refs`가 relation 수준의 실마리라면, bundle은 provenance 수준에서 "이번 판단에 사용한 근거 세트"를 가리키는 포인터라고 볼 수 있습니다.

## artifact와 lineage를 함께 쓰는 패턴

예를 들어 training run에서 checkpoint artifact를 만들고, 그 checkpoint가 특정 dataset에서 유도되었다고 표현하고 싶다면:

1. `ArtifactManifest`로 checkpoint 생성
2. `LineageEdge`로 dataset -> checkpoint 관계 생성
3. 필요하면 `ProvenanceRecord`로 관계의 근거 추가

이 패턴은 나중에 lineage 시각화, 감사 추적, 재현성 분석에 도움이 됩니다.

이 흐름을 질문 형태로 바꾸면 다음과 같습니다.

- artifact: "무엇이 생성됐는가"
- lineage edge: "무엇이 무엇에서 나왔는가"
- provenance: "왜 그렇게 판단했는가"

셋을 분리해 두면, 관계 자체를 재계산하거나 신뢰도 정책을 바꿔도 artifact identity는 그대로 유지할 수 있습니다.

### 실제 시나리오 1. 학습 파이프라인

학습 파이프라인에서는 보통 다음 조합이 자연스럽습니다.

1. 학습 dataset artifact 등록
2. checkpoint artifact 생성
3. evaluation report artifact 생성
4. dataset -> checkpoint 에 `generated_from`
5. checkpoint -> report 에 `reported_by` 또는 report와 대상 사이의 평가 관계 표현
6. 필요하면 inference나 policy 기반으로 provenance 추가

이렇게 남기면 "이 리포트는 어떤 모델에서 나왔고, 그 모델은 어떤 데이터에서 왔는가"를 한 번에 따라갈 수 있습니다.

### 실제 시나리오 2. 배포 흐름

배포에서는 다음 질문이 중요해집니다.

- 현재 서빙 중인 모델은 어느 artifact에서 왔는가
- 그 artifact는 어떤 학습 결과인가
- 그 배포 관계는 명시적 선언인가, 외부 시스템 import인가

이 경우에는:

1. 배포 대상 artifact 등록
2. source model artifact와 deployed target 사이에 `deployed_from`
3. provenance로 import 또는 explicit 여부 기록

패턴이 자연스럽습니다.

### 실제 시나리오 3. 추론 결과 분석

추론 시스템에서도 artifact/lineage는 쓸모가 있습니다.

예:

- 특정 feature snapshot이 어떤 모델 버전의 입력 기반이었는가
- 특정 report가 어느 serving model을 기준으로 생성됐는가
- drift 분석 결과가 어떤 dataset snapshot에 대해 계산됐는가

즉 이 계층은 학습 파이프라인 전용이 아니라, 배포와 분석까지 이어지는 공통 추적 계층입니다.

## 어떤 수준에서 lineage를 도입해야 하나

### 최소 수준

artifact만 관리하고 lineage는 아직 두지 않음

적합한 경우:

- 이제 막 artifact tracking을 시작함
- 관계 질의 요구가 아직 작음

### 운영 수준

핵심 artifact 사이의 주요 관계만 `LineageEdge`로 남김

적합한 경우:

- dataset -> model
- model -> report
- model -> deployed artifact

이 단계의 핵심은 "모든 걸 다 남기려 하지 말고, 나중에 반드시 물어볼 관계부터 남기는 것"입니다.

### 감사/재현성 수준

`LineageEdge`와 `ProvenanceRecord`를 함께 운영

적합한 경우:

- 관계의 출처를 설명해야 함
- imported lineage와 inferred lineage를 구분해야 함
- 정책 기반 분석이 필요함

이 단계에서는 단순 그래프보다 "왜 이 그래프를 믿어도 되는가"가 중요해집니다.

## 산출물과 계보 모델링에서 흔한 실수

### 1. artifact를 경로 문자열 하나로만 다루기

이렇게 하면 run/stage/producer/해시 정보가 빠지기 쉽습니다.

### 2. 관계를 문장 설명으로만 남기기

시스템이 lineage를 이해할 수 없게 됩니다.

### 3. inferred 관계와 explicit 관계를 구분하지 않기

이 경우 나중에 신뢰 수준을 구분하기 어렵습니다.

### 4. artifact_kind를 지나치게 제각각으로 쓰기

kind가 사실상 자유 텍스트가 되면 소비자가 해석하기 어려워집니다.

### 5. source/target 방향을 관계마다 제멋대로 쓰기

relation type은 같아도 edge 방향이 흔들리면 lineage 질의와 시각화가 크게 혼란스러워집니다.

### 6. evidence와 provenance를 끝까지 남기지 않기

처음에는 relation만 있어도 충분해 보이지만, 감사나 재현성 분석이 필요해지는 순간 "왜 이 관계를 믿었는가"를 설명할 수 없게 됩니다.

### 7. artifact identity와 location을 같은 것으로 취급하기

파일 경로나 object storage key가 바뀌는 순간 같은 artifact를 다른 것으로 오해하기 쉽습니다.

### 8. 너무 이른 단계에 모든 relation을 세밀하게 모델링하려 하기

lineage는 중요하지만, 처음부터 전체 그래프를 완벽하게 만들려 하면 오히려 운영이 멈추기 쉽습니다. 먼저 핵심 관계를 안정적으로 남기고, 이후 provenance와 evidence를 확장하는 쪽이 현실적입니다.

## 이 문서를 읽을 때 잡아야 할 핵심 직관

아주 짧게 요약하면 다음처럼 생각하면 됩니다.

- `ArtifactManifest`: 결과물의 정체성과 실행 맥락
- `LineageEdge`: 결과물들 사이의 의미적 연결
- `ProvenanceRecord`: 그 연결이 형성된 이유와 근거

이 세 층을 섞지 않으면, 나중에 위치 변경, 관계 재계산, 정책 변경이 생겨도 모델을 크게 흔들지 않고 운영할 수 있습니다.

## 이 계층이 운영에서 중요한 이유

산출물과 계보 구조가 잘 잡혀 있으면 다음 질문이 가능해집니다.

- 어떤 dataset에서 어떤 모델이 나왔는가
- 어떤 artifact가 현재 배포 중인 모델의 원천인가
- 어떤 관계가 imported이고 어떤 관계가 inferred인가
- 특정 artifact를 만든 근거와 정책은 무엇인가

즉 이 계층은 단순 보조 정보가 아니라, 재현성, 감사, lineage 시각화의 기반입니다.

## 다음 문서

- 실행 컨텍스트는 [컨텍스트 모델](./context-models.md)
- 이벤트/메트릭/트레이스는 [관측 레코드](./observability-records.md)
