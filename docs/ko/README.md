# Spine 사용자 가이드

Spine 문서는 "이 라이브러리로 무엇을 만들 수 있는가"보다 먼저 "어디서부터 읽어야 바로 써볼 수 있는가"가 보이도록 구성되어 있습니다. 처음 온 사용자라면 아래 순서대로 읽는 것이 가장 빠릅니다.

- [시작하기](./getting-started.md)
- [Spine 모델 이해하기](./understanding-spine-models.md)
- [컨텍스트 모델](./context-models.md)
- [관측 레코드](./observability-records.md)
- [산출물과 계보](./artifacts-and-lineage.md)
- [검증 규칙](./validation-rules.md)
- [직렬화와 스키마](./serialization-and-schema.md)
- [호환성 및 마이그레이션](./compatibility-and-migrations.md)
- [확장과 커스텀 필드](./extensions-and-custom-fields.md)
- [워크플로 예제](./workflow-examples.md)
- [API Reference](./api-reference.md)

추천 읽기 순서:

1. Spine을 바로 import하고 첫 객체를 만들어보려면 [시작하기](./getting-started.md)
2. Spine이 왜 `Project -> Run -> Record` 구조를 쓰는지 이해하려면 [Spine 모델 이해하기](./understanding-spine-models.md)
3. 실행 맥락과 관측 데이터를 모델링하려면 [컨텍스트 모델](./context-models.md), [관측 레코드](./observability-records.md), [산출물과 계보](./artifacts-and-lineage.md)
4. 저장, 검증, 마이그레이션 경계를 이해하려면 [검증 규칙](./validation-rules.md), [직렬화와 스키마](./serialization-and-schema.md), [호환성 및 마이그레이션](./compatibility-and-migrations.md)
5. 공개 타입과 함수를 빠르게 찾으려면 [API Reference](./api-reference.md)

Spine이 처음이라면 모든 문서를 처음부터 끝까지 읽기보다, 먼저 `시작하기`와 `Spine 모델 이해하기`를 읽고 필요한 타입 문서로 들어가는 편이 훨씬 효율적입니다.

관련 파일:

- 패키지 진입점: [`src/spine/__init__.py`](C:/Users/eastl/MLObservability/Spine/src/spine/__init__.py)
- 기본 예제: [`examples/basic_training_flow.py`](C:/Users/eastl/MLObservability/Spine/examples/basic_training_flow.py)
