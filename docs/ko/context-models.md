# 컨텍스트 모델

[사용자 가이드 홈](./README.md)

Spine을 실제로 쓰기 시작하면, metric이나 event를 만들기 전에 먼저 "이 값이 어느 실행에서 나온 것인지"를 정해야 합니다. 이 문서는 그 실행 맥락을 표현하는 컨텍스트 모델을 설명합니다.

대부분의 관측 데이터는 결국 `Project`, `Run`, `StageExecution`, `OperationContext` 같은 컨텍스트를 참조합니다. 그래서 이 계층을 먼저 이해하면 뒤의 레코드와 artifact 문서도 훨씬 쉽게 읽힙니다.

이 페이지의 목표는 다음과 같습니다.

1. `Project`, `Run`, `StageExecution`, `OperationContext`, `EnvironmentSnapshot`의 역할 차이를 분명히 이해하기
2. 어떤 시스템에서 어느 레벨까지 컨텍스트를 모델링해야 하는지 판단하기
3. 컨텍스트 모델이 이후 레코드, artifact, lineage 해석에 어떻게 연결되는지 이해하기

## 컨텍스트 계층이 하는 일

Spine의 다른 객체들은 대개 "무슨 일이 일어났는가"를 표현합니다. 반면 컨텍스트 모델은 "그 일이 어디에서 일어났는가"를 표현합니다.

예를 들어 metric 하나만 보면 다음 정도만 알 수 있습니다.

- `training.loss = 0.4821`

하지만 실무에서 필요한 건 보통 더 많습니다.

- 어느 project의 metric인가
- 어느 run의 metric인가
- train stage에서 나온 것인가 evaluate stage에서 나온 것인가
- step 42의 값인가 epoch 평균인가
- 환경 차이와 함께 비교할 수 있는가

이 질문들은 모두 값 자체보다 배경 정보를 요구합니다. 컨텍스트 계층은 바로 그 배경을 구조화합니다.

## 컨텍스트 모델을 왜 먼저 이해해야 하나

컨텍스트 모델 없이도 metric 하나, event 하나, trace span 하나는 남길 수 있습니다. 하지만 실무에서는 곧 다음 질문이 생깁니다.

- 이 값은 어떤 실험에서 나온 것인가
- 같은 프로젝트의 다른 run과 비교할 수 있는가
- 어떤 stage에서 문제가 발생했는가
- step 수준 문제인가, run 수준 문제인가
- 환경 차이 때문에 결과가 달라졌는가

이 질문들은 모두 "값 자체"보다 "값의 배경"을 요구합니다. Spine의 컨텍스트 모델은 바로 이 배경을 구조화합니다.

## 컨텍스트 계층 전체 그림

가장 흔한 연결 구조는 다음과 같습니다.

```text
Project
  -> Run
    -> StageExecution
      -> OperationContext
    -> EnvironmentSnapshot
```

이 구조는 사실상 실행 범위를 점점 좁혀가는 방식입니다.

- `Project`: 장기적이고 논리적인 범위
- `Run`: 한 번의 실제 실행 범위
- `StageExecution`: 실행 내부의 큰 단계 범위
- `OperationContext`: 단계 내부의 세부 작업 범위
- `EnvironmentSnapshot`: 해당 실행이 놓여 있던 환경 범위

이 관점에서 보면 컨텍스트 모델은 단순 타입 목록이 아니라 "스코프 계층"입니다.

## Project

`Project`는 가장 상위의 논리 단위입니다. 일반적으로 하나의 모델 계열, 서비스군, 실험 트랙, 혹은 ML 제품 라인을 나타냅니다.

주요 필드:

- `project_ref`: 프로젝트의 canonical reference
- `name`: 사람이 읽는 이름
- `created_at`: 프로젝트 기준 생성 시각
- `description`: 설명
- `tags`: 간단한 메타데이터
- `schema_version`
- `extensions`

예시:

```python
from spine import Project, StableRef

project = Project(
    project_ref=StableRef("project", "nova"),
    name="NovaVision",
    created_at="2026-03-30T09:00:00Z",
    description="Image classification project.",
    tags={"team": "research", "track": "vision"},
)
```

직렬화 payload 예시:

```json
{
  "created_at": "2026-03-29T10:15:21Z",
  "description": "Image classification project.",
  "name": "NovaVision",
  "project_ref": "project:nova",
  "schema_version": "1.0.0",
  "tags": {
    "team": "research",
    "track": "vision"
  }
}
```

### Project를 어떻게 잡아야 하나

`Project`를 너무 작게 잡으면 run이 불필요하게 흩어지고, 너무 크게 잡으면 서로 성격이 다른 실행이 한 프로젝트 안에 섞입니다.

대체로 다음 기준이 좋습니다.

- 같은 제품/모델 계열인가
- 비교하고 싶은 run들이 같은 논리 그룹인가
- 공통 태그와 설명을 공유할 수 있는가

좋은 예:

- `NovaVision`
- `fraud-detection`
- `ranking-v2`

덜 좋은 예:

- `train-20260330-01`
- `epoch-1`

이런 이름은 대체로 `Run`이나 `OperationContext` 쪽 의미에 가깝습니다.

### Project가 답하는 질문

- 이 run은 어느 제품/실험 트랙에 속하는가
- 같은 프로젝트 안의 run들을 한 번에 보고 싶은가
- 팀/도메인 단위 메타데이터를 어디에 붙일 것인가

### Project validation에서 주로 보는 것

현재 검증 로직은 대체로 다음을 봅니다.

- `project_ref.kind == "project"`
- `name`이 비어 있지 않은가
- `created_at`이 정규 UTC `Z` 형식인가
- `schema_version`이 현재 스키마와 일치하는가

실무 팁:

- `Project`는 장기간 유지되는 식별자여야 합니다.
- 배치 실행 이름은 `Run`에 두고, 제품/실험 계열 이름은 `Project`에 두는 편이 좋습니다.
- `tags`는 검색과 분류에 자주 쓰일 키만 두는 편이 좋습니다.

## Run

`Run`은 실제 한 번 수행된 실행 단위입니다. 학습 job, 평가 job, 배치 추론, 데이터 생성 파이프라인 실행 등을 표현할 수 있습니다.

주요 필드:

- `run_ref`
- `project_ref`
- `name`
- `status`
- `started_at`
- `ended_at`
- `description`
- `schema_version`
- `extensions`

허용 status:

- `created`
- `running`
- `completed`
- `failed`
- `cancelled`

예시:

```python
from spine import Run, StableRef

run = Run(
    run_ref=StableRef("run", "train-20260330-01"),
    project_ref=StableRef("project", "nova"),
    name="baseline-resnet50",
    status="running",
    started_at="2026-03-30T09:05:00Z",
)
```

### Run이 중요한 이유

Spine에서 `Run`은 사실상 가장 자주 참조되는 컨텍스트입니다.

대부분의 레코드와 산출물은 결국 run에 귀속됩니다.

예:

- metric은 어느 run의 값인가
- event는 어느 run에서 발생했는가
- artifact는 어느 run의 결과물인가
- environment snapshot은 어느 run의 환경인가

즉, run은 "실행 시간축의 기본 단위"입니다.

### Run 이름과 Run ref의 차이

실무에서는 이 둘을 구분하는 것이 좋습니다.

- `run_ref`: 시스템적으로 안정적인 식별자
- `name`: 사람이 읽기 좋은 실행 이름

예:

- `run_ref = run:train-20260330-01`
- `name = baseline-resnet50`

이렇게 두면 내부 식별자와 사용자 가독성을 동시에 만족할 수 있습니다.

### Run을 설계할 때 생각할 점

- retried job을 같은 run으로 볼 것인가, 별도 run으로 볼 것인가
- batch inference 하루치를 하나의 run으로 묶을 것인가
- evaluation run과 training run을 분리할 것인가

이 판단은 운영 쿼리와 lineage 해석에 직접 영향을 줍니다.

### Run이 답하는 질문

- 이번 실행은 성공했는가 실패했는가
- 언제 시작했고 언제 끝났는가
- 어떤 project에 속하는가
- 어떤 레코드와 artifact가 같은 실행에 속하는가

### Run validation에서 주로 보는 것

- `run_ref.kind == "run"`
- `project_ref.kind == "project"`
- status가 허용값 안에 있는가
- `started_at`이 유효한가
- `ended_at`이 있으면 시간 순서가 맞는가

실무 팁:

- run 이름에는 사람이 바로 이해할 수 있는 실험 의미를 담는 것이 좋습니다.
- `run_ref`는 시스템 식별자, `name`은 사용자 친화 이름으로 역할을 분리하는 편이 좋습니다.
- 운영 화면에서 가장 먼저 검색하는 기준이 run인 경우가 많습니다.

## StageExecution

`StageExecution`은 하나의 run을 더 큰 단계로 나눈 구조입니다.

대표 예:

- `extract`
- `prepare`
- `train`
- `evaluate`
- `deploy`

주요 필드:

- `stage_execution_ref`
- `run_ref`
- `stage_name`
- `status`
- `started_at`
- `ended_at`
- `order_index`
- `schema_version`
- `extensions`

### 모든 시스템에 StageExecution이 필요한가

반드시 그렇지는 않습니다. 하지만 다음 중 하나라도 해당하면 큰 도움이 됩니다.

- run 내부 단계가 명확히 나뉜다
- stage별 metric을 따로 보고 싶다
- stage별 실패 원인을 나누고 싶다
- artifact 생성 위치를 단계 수준에서 추적하고 싶다

예를 들어 학습 파이프라인이 다음처럼 구성된다면 stage 분리가 자연스럽습니다.

```text
prepare -> train -> evaluate -> register
```

### StageExecution이 답하는 질문

- 실패는 어느 단계에서 일어났는가
- 이 artifact는 train stage의 결과인가 evaluate stage의 결과인가
- stage별 latency와 성공률은 어떤가
- stage 간 시간 순서는 어떻게 되는가

### `stage_name`과 `stage_execution_ref`의 관계

실무적으로는 둘의 역할을 나눠두는 편이 좋습니다.

- `stage_name`: 사람이 이해하는 단계 이름
- `stage_execution_ref`: 참조 가능한 식별자

특히 여러 run에서 같은 이름의 stage가 반복될 수 있으므로, ref와 name을 분리해두면 더 안정적입니다.

### StageExecution validation에서 주로 보는 것

- `stage_execution_ref.kind == "stage"`
- `run_ref.kind == "run"`
- `stage_name`이 비어 있지 않은가
- status가 유효한가
- 시간 순서가 맞는가

실무적으로는 다음 상황에 특히 유용합니다.

- 하나의 run 안에서 여러 단계 metric을 분리하고 싶을 때
- artifact가 어느 단계에서 생성되었는지 추적하고 싶을 때
- stage 단위 SLA/실패율/latency를 보고 싶을 때

## OperationContext

`OperationContext`는 stage 내부의 더 세밀한 작업 단위입니다.

대표 예:

- `epoch-1`
- `step-42`
- `batch-000123`
- `feature-join`
- `request-abc123`

주요 필드:

- `operation_context_ref`
- `run_ref`
- `stage_execution_ref`
- `operation_name`
- `observed_at`
- `schema_version`
- `extensions`

### OperationContext를 언제 도입해야 하나

처음부터 모든 시스템에 필요한 것은 아닙니다. 하지만 다음 상황에서는 가치가 큽니다.

- metric이나 trace가 step/batch/request 수준으로 많이 나온다
- 같은 stage 안에서도 세부 작업을 분리해 보고 싶다
- 특정 오류나 지연이 어떤 세부 작업에서 발생했는지 알고 싶다

예:

- 학습 step별 loss 추적
- request별 inference latency 추적
- feature join 작업별 오류 이벤트 추적

### OperationContext가 답하는 질문

- 이 metric은 어느 step에서 발생했는가
- 이 trace span은 어떤 request에 속하는가
- 이 event는 어느 세부 작업 중 발생했는가

### OperationContext를 남발하면 생기는 문제

모든 내부 함수 호출을 operation으로 만들면 모델이 지나치게 시끄러워질 수 있습니다.

좋은 기준:

- 운영적으로 구분할 가치가 있는가
- metric/trace/event를 연결해 볼 가치가 있는가
- 나중에 이 단위로 검색하거나 집계할 가능성이 있는가

이 모델은 특히 레코드와 함께 쓸 때 강력합니다. 예를 들어 `MetricRecord`의 `operation_context_ref`를 `op:step-42`로 연결해두면 "이 metric이 어느 연산 단위에서 나왔는가"를 정확히 알 수 있습니다.

## EnvironmentSnapshot

`EnvironmentSnapshot`은 실행 환경 자체를 보존하기 위한 모델입니다.

주요 필드:

- `environment_snapshot_ref`
- `run_ref`
- `captured_at`
- `python_version`
- `platform`
- `packages`
- `environment_variables`
- `schema_version`
- `extensions`

### 왜 환경을 별도 모델로 두나

환경은 metric이나 artifact만큼 자주 보지 않을 수 있습니다. 하지만 장애나 재현성 이슈가 생기면 오히려 가장 먼저 필요해지는 정보 중 하나입니다.

예:

- 패키지 버전이 달라서 결과가 달라짐
- Python 버전 차이로 serialization 동작이 달라짐
- 환경 변수 설정 차이로 입력 경로가 달라짐

즉, 평소엔 조용하지만 문제가 생기면 가장 가치가 커지는 데이터가 환경 정보입니다.

### EnvironmentSnapshot이 답하는 질문

- 이 run은 어떤 Python 버전에서 실행됐는가
- 어떤 패키지가 설치돼 있었는가
- 환경 변수 차이가 있었는가
- 서로 다른 두 run의 환경 차이는 무엇인가

### EnvironmentSnapshot을 언제 꼭 남겨야 하나

다음 경우라면 강하게 권장됩니다.

- 재현성이 중요한 training 시스템
- 환경 drift가 자주 문제되는 배포/추론 시스템
- 감사 가능성이 중요한 환경

이 모델이 중요한 이유:

- 재현성 분석
- 환경 차이에 따른 오류 추적
- 패키지 버전 drift 확인

## 컨텍스트 모델을 어떻게 조합해서 써야 하나

실무에서는 항상 모든 레벨이 필요한 것은 아닙니다.

### 최소 조합

- `Project`
- `Run`

이 정도면 run 단위로 metric과 artifact를 묶는 기본 구조는 만들어집니다.

### 운영 조합

- `Project`
- `Run`
- `StageExecution`

이 정도면 대부분의 단계별 운영 분석이 가능해집니다.

### 세밀한 추적 조합

- `Project`
- `Run`
- `StageExecution`
- `OperationContext`

이 구조면 step/request 수준 추적까지 가능합니다.

### 재현성 조합

- 위 구조
- `EnvironmentSnapshot`

이 구조면 "무슨 실행이 어떤 환경에서 돌아갔는가"까지 설명할 수 있습니다.

## 모델링 결정 트리

간단히 결정하려면 아래 질문 순서가 도움이 됩니다.

### 1. 여러 실행을 하나의 논리 그룹으로 묶고 싶은가

그렇다면 `Project`가 필요합니다.

### 2. 시간 축을 가진 개별 실행 단위가 필요한가

거의 항상 `Run`이 필요합니다.

### 3. 실행 내부에 사람이 이해할 수 있는 큰 단계가 있는가

그렇다면 `StageExecution`을 두는 편이 좋습니다.

### 4. step, batch, request 같은 세부 단위 추적이 필요한가

그렇다면 `OperationContext`를 고려해야 합니다.

### 5. 환경 차이가 결과에 영향을 줄 수 있는가

그렇다면 `EnvironmentSnapshot`을 남기는 편이 좋습니다.

## 컨텍스트 모델을 설계할 때 흔한 실수

### 1. Project와 Run을 사실상 같은 의미로 쓰기

예:

- 프로젝트 이름에 날짜와 실행 번호까지 포함

이 경우 장기적 그룹과 단기적 실행이 섞여 버립니다.

### 2. StageExecution 없이 모든 걸 Run 하나에 몰아넣기

초기에는 단순하지만, 나중에 prepare/train/evaluate를 분리해서 보기 어려워집니다.

### 3. OperationContext를 너무 세밀하게 남발하기

모든 내부 함수 호출을 operation으로 만들면 오히려 모델이 지나치게 시끄러워질 수 있습니다. operation은 "운영적으로 구분할 가치가 있는 단위"에만 두는 것이 좋습니다.

### 4. EnvironmentSnapshot을 전혀 남기지 않기

초기에는 안 써도 돌아가지만, 재현성 이슈가 생기는 순간 가장 아쉬운 정보가 되기 쉽습니다.

### 5. 이름과 식별자 역할을 섞기

`name`과 `*_ref`를 같은 의미로 쓰면 나중에 사람이 읽는 이름과 시스템 식별자가 섞이게 됩니다.

## 컨텍스트 모델이 이후 문서에 미치는 영향

컨텍스트 모델은 다른 모든 모델의 해석 기준이 됩니다.

- 레코드는 이 컨텍스트를 참조합니다.
- artifact는 이 컨텍스트 안에서 생성됩니다.
- lineage는 이 컨텍스트 위에서 관계를 표현합니다.

즉, 컨텍스트 모델이 흔들리면 나머지 문서에서 다루는 의미도 함께 흔들립니다.

## 이 페이지를 읽은 뒤

다음 문서는 컨텍스트 위에 올라가는 실제 관측 데이터와 산출물을 설명합니다.

- 레코드 구조는 [관측 레코드](./observability-records.md)
- artifact와 lineage는 [산출물과 계보](./artifacts-and-lineage.md)

보통은 다음으로 [관측 레코드](./observability-records.md)를 읽는 것이 가장 자연스럽습니다.
