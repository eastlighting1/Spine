## 1. Purpose and Scope
### 1.1 Purpose
This report defines the implementation rules for building `Spine` as the canonical contract library of the ML observability stack. Its purpose is to translate the approved design into concrete engineering rules so that every contributor implements schemas, validators, serializers, compatibility logic, and extension boundaries consistently.

Because `Spine` is the semantic foundation of the entire stack, this report is stricter than an ordinary coding guide. It is intended to prevent architectural drift, schema ambiguity, and accidental contract fragmentation across the implementation.

### 1.2 Scope
This report covers the `Spine` codebase structure, implementation rules, data contract boundaries, validation and serialization behavior, compatibility policy, testing rules, and delivery criteria.

**In Scope**
- Canonical object model implementation
- Validation, serialization, and compatibility-read behavior
- Package layering and responsibility boundaries
- Exception, logging, and testing rules
- Delivery criteria for contract-aligned releases

**Out of Scope**
- Storage engine implementation
- Runtime instrumentation behavior
- Visualization or UI behavior
- Product-level roadmap discussion beyond implementation scope

### 1.3 Reference Documents
- `Spine-Planning-and-Implementation-Strategy.md`
- `../Implementation_Strategy_Report.md`
- `../ML-Observability-Stack-Library-Overview-KR.md`
- `../ML-Observability-Spec.md`

---

## 2. Implementation Objectives and Principles
### 2.1 Implementation Objectives
- Implement a stable canonical contract layer for the entire stack
- Make semantic construction, validation, and serialization explicit
- Preserve compatibility and migration discipline from the start
- Keep the codebase narrow, testable, and easy to reason about

### 2.2 Core Principles
- Prefer explicit canonical construction over permissive convenience
- Keep semantic authority centralized in `Spine`
- Treat compatibility behavior as architecture, not as utility logic
- Make invalid states impossible or loudly rejected
- Preserve inspectable serialized forms
- Keep extensions namespaced and governed

### 2.3 Definition of Done
A `Spine` feature is complete only when:
- The canonical model and invariants are documented in code
- Required validators and serializers exist
- Compatibility implications are stated explicitly
- Contract tests and fixture tests pass
- No downstream concern has been pulled into the contract layer

---

## 3. Codebase Structure and Responsibility Boundaries
### 3.1 Repository Structure
- `src/`
- `tests/`
- `docs/`
- `examples/`
- `scripts/`

### 3.2 Module Structure
- `api/`: public factories, validators, and high-level entry points
- `models/`: canonical domain entities such as runs, stages, manifests, and relations
- `validation/`: invariant checks and validation reports
- `serialization/`: canonical serialization and deserialization logic
- `compat/`: compatibility-aware readers and schema evolution helpers
- `extensions/`: namespaced extension registration and policies
- `exceptions/`: typed contract and compatibility exceptions
- `logging/`: optional structured debug and warning helpers

### 3.3 Responsibility Rules
- Public API modules must expose contracts, not business workflows
- Model modules must not import compatibility or backend-specific helpers directly
- Validation modules must own invariant enforcement, not UI-friendly summaries
- Serialization modules must not silently reinterpret invalid state
- Compatibility modules must not become alternate sources of canonical truth
- Extension modules must not weaken the core namespace

### 3.4 Prohibited Patterns
- No schema meaning defined outside `Spine`
- No implicit mutation during canonical construction
- No compatibility fallback hidden inside strict write paths
- No storage-layout assumptions in canonical objects
- No surface-specific formatting logic in contract modules

---

## 4. Coding Rules and Implementation Conventions
### 4.1 File, Class, and Function Rules
- Each file must represent one contract family or one narrowly scoped implementation concern
- Canonical entities should be modeled as explicit typed classes or immutable data structures
- Validation functions must separate structural checks from compatibility notes clearly
- Serializer functions must have deterministic outputs and explicit version handling
- Compatibility helpers must be visibly marked and isolated from strict constructors

### 4.2 Naming Rules
- Use domain names such as `RunRef`, `StageExecution`, `ArtifactManifest`, `LineageEdge`
- Use `validate_*`, `serialize_*`, `deserialize_*`, `read_compat_*` for operations
- Avoid vague names such as `manager`, `helper`, `misc`, `handler`, or `data`
- Compatibility functions must signal compatibility intent in the name

### 4.3 Style Conventions
- Formatting tool: `ruff format`
- Linting tool: `ruff`
- Type checking policy: `mypy` on public and core modules
- Import ordering policy: `ruff`/`isort` compatible ordering
- Docstring style: Google-style docstrings for public APIs
- Comment style: comments explain invariants, tradeoffs, and compatibility concerns
- Async/sync naming conventions: not applicable in the initial core

### 4.4 Commenting Policy
- Comments should explain contract invariants and semantic boundaries
- Inline comments must not restate obvious field assignments
- Compatibility logic should carry comments explaining why the path exists
- TODOs must reference a compatibility, schema, or issue-tracking context

---

## 5. Implementation Rules for Core Concerns
### 5.1 Configuration Rules
- Configuration must remain minimal and explicit
- Allowed configuration is limited to validation mode, compatibility mode, and extension registration policy
- Environment variables must not redefine semantic meaning
- Invalid configuration must fail at construction time, not late in serialization

### 5.2 Data and State Rules
- Inputs must be normalized before becoming canonical objects
- Outputs must be deterministic and JSON-compatible
- Canonical entities should be immutable by default where practical
- Hidden global registries are prohibited except for explicit extension registration points
- Schema version and compatibility context must remain visible at boundaries

### 5.3 Error Handling Rules
- Use typed exceptions such as validation, serialization, compatibility, and extension errors
- Strict write paths must fail on invalid canonical state
- Compatibility reads may produce structured warnings or notes, but must remain explicit
- Never auto-repair invalid canonical objects silently
- Error messages must identify the failing field or invariant when possible

### 5.4 Logging and Observability Rules
- Logging is optional and maintenance-oriented
- Log deprecated field usage, extension conflicts, and compatibility-read warnings
- Avoid noisy logs during normal canonical construction
- Required fields for structured logs: timestamp, severity, module, contract family, version context

---

## 6. Testing and Quality Control
### 6.1 Testing Rules
- All public constructors and validators require contract tests
- Serialization requires fixture-based deterministic output tests
- Compatibility readers require historical fixture coverage
- Extension boundaries require conflict and namespace tests
- Error typing and field-level failure behavior must be tested

### 6.2 Test Design Principles
- Test semantic behavior, not internal implementation trivia
- Keep fixtures readable because they also serve as contract examples
- Use versioned serialized fixtures for regression protection
- Test strict write and compatibility read paths separately
- Add regression fixtures whenever a schema or compatibility defect is fixed

### 6.3 Review and Merge Criteria
- Layering rules are respected
- Public contracts and serialized outputs are reviewed carefully
- Tests, lint, and type checks pass
- Compatibility implications are documented in the PR or changelog context
- Changes that affect canonical meaning receive explicit architectural review

### 6.4 Quality Gates
- No unresolved critical contract-review comments
- All fixture updates are intentional and justified
- Compatibility behavior is covered where changed
- Release-blocking checks for serialization and validation are green

---

## 7. Delivery Plan and Work Breakdown
### 7.1 Implementation Phases
- Phase 1: Core models, refs, validators, and strict serialization
- Phase 2: Compatibility readers, version metadata, and extension boundaries
- Phase 3: Richer error/reporting behavior and fixture hardening
- Phase 4: Documentation completion and release hardening

### 7.2 Work Breakdown
**Workstream: Canonical Models**
- Objective: implement stable core entities and refs
- Owned modules: `models/`, `api/`
- Dependencies: strategy document, stack spec
- Deliverables: typed entities, constructors, public exports
- Exit criteria: core entities construct and validate correctly

**Workstream: Validation and Serialization**
- Objective: implement invariant enforcement and deterministic serialization
- Owned modules: `validation/`, `serialization/`
- Dependencies: canonical models
- Deliverables: validators, serializers, fixture coverage
- Exit criteria: strict write path and round-trip behaviors pass tests

**Workstream: Compatibility and Extensions**
- Objective: support safe schema evolution and governed extension points
- Owned modules: `compat/`, `extensions/`
- Dependencies: models, serialization
- Deliverables: compatibility readers, extension registry, tests
- Exit criteria: old fixtures read under explicit compatibility policy

### 7.3 MVP Scope
- Required public APIs: canonical constructors, validators, serializers
- Required core modules: `models`, `validation`, `serialization`
- Required configuration support: validation and compatibility modes
- Required logging and exception handling: typed exceptions and warnings
- Required tests and documentation: contract fixtures, serialization fixtures, API examples

---

## 8. Open Issues, Deferred Decisions, and Technical Debt
### 8.1 Open Implementation Issues
- Exact stable ref encoding scheme
- Initial extension namespace format
- Compatibility-report object shape
- Schema version publication format

### 8.2 Deferred Decisions
- Alternate wire formats beyond JSON-compatible serialization
- Formal schema export artifacts for external tooling
- More advanced extension loading mechanisms

### 8.3 Technical Debt Rules
- Do not duplicate serializer logic across contract families
- Do not allow compatibility code to leak into strict constructors
- Track any temporary schema shortcuts explicitly before release

