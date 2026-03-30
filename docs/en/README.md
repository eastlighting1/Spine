# Spine User Guide

Spine documentation is organized so that a new user can see "where should I start if I want to use this library right away" before worrying about "what can this library model." If this is your first time here, the fastest path is to read the pages below in order.

- [Getting Started](./getting-started.md)
- [Understanding Spine Models](./understanding-spine-models.md)
- [Context Models](./context-models.md)
- [Observability Records](./observability-records.md)
- [Artifacts And Lineage](./artifacts-and-lineage.md)
- [Validation Rules](./validation-rules.md)
- [Serialization And Schema](./serialization-and-schema.md)
- [Compatibility And Migrations](./compatibility-and-migrations.md)
- [Extensions And Custom Fields](./extensions-and-custom-fields.md)
- [Workflow Examples](./workflow-examples.md)
- [API Reference](./api-reference.md)

Recommended reading order:

1. If you want to import Spine right away and build your first object, start with [Getting Started](./getting-started.md).
2. If you want to understand why Spine uses a `Project -> Run -> Record` structure, read [Understanding Spine Models](./understanding-spine-models.md).
3. If you want to model execution context and observability data, read [Context Models](./context-models.md), [Observability Records](./observability-records.md), and [Artifacts And Lineage](./artifacts-and-lineage.md).
4. If you want to understand storage, validation, and migration boundaries, read [Validation Rules](./validation-rules.md), [Serialization And Schema](./serialization-and-schema.md), and [Compatibility And Migrations](./compatibility-and-migrations.md).
5. If you want to look up public types and functions quickly, use [API Reference](./api-reference.md).

If you are new to Spine, it is usually much more efficient to read `Getting Started` and `Understanding Spine Models` first, then jump to the type-specific pages you need, rather than reading every page from top to bottom.

Related files:

- Package entrypoint: [`src/spine/__init__.py`](C:/Users/eastl/MLObservability/Spine/src/spine/__init__.py)
- Basic example: [`examples/basic_training_flow.py`](C:/Users/eastl/MLObservability/Spine/examples/basic_training_flow.py)
