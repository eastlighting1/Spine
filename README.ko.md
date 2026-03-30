# Spine

`Spine`은 ML 관측 가능성 시스템을 위한 canonical contract 라이브러리입니다.

영문 README: [README.md](./README.md)

Spine은 실행 컨텍스트, 관측 레코드, 산출물, lineage, validation, deterministic serialization, compatibility-aware reading을 위한 공용 모델을 팀에 제공합니다. producer마다 제각각 payload shape를 만들게 두는 대신, 같은 종류의 객체를 만들고 검증하고 직렬화하고 다시 읽어오는 과정을 하나의 계약으로 묶습니다.

## 왜 Spine인가

ML 시스템은 보통 다음 지점에서 쉽게 drift가 생깁니다.

- run과 project identity,
- metric과 event payload shape,
- timestamp 정규화,
- artifact metadata,
- lineage와 provenance 표현,
- legacy payload 처리.

Spine은 이런 drift를 모델 계층에서 막기 위해 존재합니다.

Spine으로 다음을 모델링할 수 있습니다.

- `Project`, `Run`, `StageExecution`, `OperationContext`, `EnvironmentSnapshot` 기반 실행 컨텍스트,
- `StructuredEventRecord`, `MetricRecord`, `TraceSpanRecord` 기반 관측 레코드,
- `ArtifactManifest` 기반 결과물,
- `LineageEdge`, `ProvenanceRecord` 기반 의미 관계,
- validation과 deterministic serialization을 통한 계약 집행,
- explicit compatibility reader를 통한 legacy upgrade 경로.

## 핵심 개념

Spine은 다음 구조로 이해하면 가장 쉽습니다.

```text
Project
  -> Run
    -> StageExecution
      -> OperationContext
        -> RecordEnvelope + Payload

Run / Stage
  -> ArtifactManifest

Refs between objects
  -> LineageEdge
  -> ProvenanceRecord
```

이 라이브러리는 몇 가지 강한 기본 원칙 위에 서 있습니다.

- 모델 내부 식별자는 ad hoc string 대신 `StableRef` 사용,
- 실행 컨텍스트와 관측 사실 분리,
- 객체 생성 직후 validation 수행,
- deterministic canonical payload로 serialization,
- migration을 숨겨진 마법이 아니라 explicit compatibility path로 처리.

## 설치

로컬 개발에서 `uv`를 쓸 경우:

```bash
uv run --with-editable . python
```

import 확인:

```bash
uv run --with-editable . python -c "import spine; print(spine.__file__)"
```

테스트 실행:

```bash
uv run pytest tests
```

## 빠른 예제

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
        unit="ratio",
    ),
)
validate_metric_record(metric).raise_for_errors()

print(to_json(metric))
```

기본 사용 루프는 다음과 같습니다.

1. canonical object를 만든다.
2. validation한다.
3. 시스템 경계에서만 serialization한다.

## 무엇을 얻는가

- context, record, artifact, lineage, provenance를 위한 canonical model.
- ref, timestamp, enum, schema boundary에 대한 strict validation.
- fixture, 저장, 해시, 전송에 적합한 deterministic JSON-compatible serialization.
- raw payload를 parse하고 validate하는 current-schema deserializer.
- 지원하는 legacy payload를 current canonical object로 올리는 compatibility reader.
- namespace 기반 `ExtensionFieldSet`, `ExtensionRegistry`를 통한 governed extension.

## 문서

- 영어 가이드: [docs/en/README.md](./docs/en/README.md)
- 한국어 가이드: [docs/ko/README.md](./docs/ko/README.md)
- 영어 API reference: [docs/en/api-reference.md](./docs/en/api-reference.md)
- 한국어 API reference: [docs/ko/api-reference.md](./docs/ko/api-reference.md)

처음 보는 사용자라면 다음 순서가 가장 빠릅니다.

1. [시작하기](./docs/ko/getting-started.md)
2. [Spine 모델 이해하기](./docs/ko/understanding-spine-models.md)
3. [컨텍스트 모델](./docs/ko/context-models.md)
4. [관측 레코드](./docs/ko/observability-records.md)
5. [산출물과 계보](./docs/ko/artifacts-and-lineage.md)

## 저장소 구조

- `src/spine`: public package와 구현
- `examples`: 실행 가능한 example flow
- `tests`: model 및 serialization 테스트
- `docs/en`: 영어 가이드
- `docs/ko`: 한국어 가이드

## 현재 상태

이 저장소는 아직 초기 단계이지만, 핵심 contract surface는 이미 갖춰져 있습니다.

- canonical object modeling,
- validation,
- deterministic serialization,
- compatibility-aware reading,
- extension namespace governance.

포함된 example과 현재 테스트 스위트는 모두 `uv` 기준으로 정상 실행됩니다.
