<div align="center">
  <h1>🩻 Spine</h1>
  <p><em>머신러닝 관측성(Observability) 시스템을 위한 표준 컨트랙트 라이브러리</em></p>

[![Actions status](https://github.com/eastlighting1/Spine/actions/workflows/ci.yml/badge.svg)](https://github.com/eastlighting1/Spine/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://github.com/eastlighting1/Spine)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

[**English**](./README.md) • [**한국어**](./README.ko.md)

</div>

---

**Spine**은 실행 컨텍스트, 관측성 기록, 아티팩트, 데이터 계보(lineage), 유효성 검사, 결정론적 직렬화 및 호환성을 고려한 읽기 작업을 위해 팀 전체가 공유할 수 있는 모델을 제공합니다.

각각의 프로듀서가 자체적인 페이로드 형태를 고안하게 두는 대신, Spine은 전체 머신러닝 파이프라인에 걸쳐 동일한 종류의 객체를 일관되게 생성, 검증, 직렬화 및 다시 읽어 들일 수 있도록 **단 하나의 통합된 컨트랙트(규약)**를 제공합니다.

Spine의 생성자는 자동으로 검증하지 않습니다. 의도된 사용 패턴은 명시적입니다. 객체를 만들고, 검증하고, 그 다음 직렬화하거나 저장합니다.

## ❓ 왜 Spine인가?

머신러닝 시스템은 보통 다음과 같은 동일한 지점에서 어긋나고 고장 납니다.

- Run(실행) 및 프로젝트 식별
- 메트릭 및 이벤트 페이로드 형태
- 타임스탬프 정규화
- 아티팩트 메타데이터
- 데이터 계보(Lineage) 및 출처(provenance) 표현
- 레거시 페이로드 처리

> **Spine은 모델 계층에서 이러한 어긋남(drift)을 방지하기 위해 존재합니다.**

Spine을 사용하면 다음에 대한 엄격한 모델을 강제할 수 있습니다.

- **실행 컨텍스트 (Execution Context):** `Project`, `Run`, `StageExecution`, `OperationContext`, `EnvironmentSnapshot`
- **관측성 기록 (Observability Records):** `StructuredEventRecord`, `MetricRecord`, `TraceSpanRecord`
- **영구 출력물 (Durable Outputs):** `ArtifactManifest`
- **의미론적 관계 (Semantic Relationships):** `LineageEdge`, `ProvenanceRecord`

## 🧠 핵심 아이디어

Spine은 계층적 데이터 모델을 통해 이해하는 것이 가장 쉽습니다. 실행 컨텍스트는 관찰된 사실(observed facts)과 엄격하게 분리됩니다.

    graph TD
        %% Context Hierarchy
        P[Project] --> R[Run]
        R --> S[StageExecution]
        S --> O[OperationContext]
        O --> E[RecordEnvelope]
        E --> PL((Payload))

        %% Artifacts & Lineage
        R -.-> AM[ArtifactManifest]
        S -.-> AM
        
        %% Styles
        classDef context fill:#f9f2f4,stroke:#c7254e,stroke-width:2px;
        classDef record fill:#eef1f8,stroke:#428bca,stroke-width:2px;
        classDef artifact fill:#f4f9f4,stroke:#5cb85c,stroke-width:2px;
        
        class P,R,S,O context;
        class E,PL record;
        class AM artifact;

### 강력한 기본값 (Strong Defaults)

- 임시방편적인 식별자 문자열 대신 `StableRef`를 사용합니다.
- 생성과 검증을 분리합니다. 먼저 객체를 만들고, 이어서 `validate_*().raise_for_errors()`를 호출합니다.
- 메타데이터 mapping은 생성 시 정렬되고 read-only로 고정되어 canonical 객체가 생성 후 흔들리지 않게 합니다.
- 결정론적이고 표준적인(canonical) 페이로드로 직렬화합니다.
- 데이터 마이그레이션을 암묵적인 마법이 아닌 명시적인 호환성 경로로 취급합니다.

## 📦 설치 방법

저장소를 클론합니다:

    git clone https://github.com/eastlighting1/Spine.git
    cd Spine

`uv`를 사용한 로컬 개발 환경 구성:

    uv run --with-editable . python

설치 확인:

    uv run --with-editable . python -c "import spine; print(spine.__file__)"

테스트 도구 실행:

    uv run pytest tests

라이브러리 코드와 테스트까지 함께 타입 검사:

    uv run mypy src tests

## ⚡ 빠른 시작

Spine의 기본적인 사용 루프는 간단합니다. **1) 표준 객체 생성 ➔ 2) 유효성 검사 ➔ 3) 시스템 경계에서 직렬화**

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

    # 1. 컨텍스트 정의 및 유효성 검사
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

    # 2. 관찰된 사실 기록
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
        ),
    )
    validate_metric_record(metric).raise_for_errors()

    # 3. 결정론적 직렬화
    print(to_json(metric))

`tags`, `attributes`, `packages`, 환경 변수 map 같은 메타데이터 dictionary는 생성 시 일반 dict로 넘겨도 됩니다. Spine이 내부적으로 정렬하고 read-only mapping으로 고정하므로, 결과 객체는 생성 후에도 안정적으로 유지됩니다.

## 📚 공식 문서

Spine의 아키텍처와 API에 대해 더 자세히 알아보세요.

| 가이드 | English | 한국어 |
|---|---|---|
| **메인 가이드** | [README.md](./docs/en/README.md) | [README.md](./docs/ko/README.md) |
| **API 레퍼런스** | [api-reference.md](./docs/en/api-reference.md) | [api-reference.md](./docs/ko/api-reference.md) |

**권장 읽기 순서:**

1. [시작하기 (Getting Started)](./docs/en/getting-started.md)
2. [Spine 모델 이해하기](./docs/en/understanding-spine-models.md)
3. [컨텍스트 모델](./docs/en/context-models.md)
4. [관측성 기록](./docs/en/observability-records.md)
5. [아티팩트 및 데이터 계보](./docs/en/artifacts-and-lineage.md)

## 🏗️ 저장소 구조

- `src/spine`: 공개 패키지 및 구현체
- `examples`: 실행 가능한 예제 플로우
- `tests`: 모델 및 직렬화 테스트
- `docs/en` & `docs/ko`: 상세 문서

## 🚦 현재 상태

이 저장소는 현재 초기 단계에 있지만, 핵심적인 컨트랙트 표면(contract surface)은 완전히 작동합니다:

- ✅ 표준 객체 모델링
- ✅ 엄격한 스키마 유효성 검사
- ✅ 결정론적 직렬화
- ✅ 호환성을 고려한 읽기
- ✅ 확장 네임스페이스 관리(governance)
