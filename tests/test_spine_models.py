from spine import (
    ArtifactManifest,
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    StableRef,
    StructuredEventPayload,
    StructuredEventRecord,
    TraceSpanPayload,
    TraceSpanRecord,
    validate_artifact_manifest,
    validate_metric_record,
    validate_project,
    validate_structured_event_record,
    validate_trace_span_record,
)


def test_public_exports_are_explicit_and_stable() -> None:
    expected = {
        "ArtifactManifest",
        "CompatibilityError",
        "ExtensionError",
        "ExtensionRegistry",
        "SerializationError",
        "SpineError",
        "StableRef",
        "ValidationError",
        "validate_project",
    }

    assert expected.issubset(set(__import__("spine").__all__))


def test_project_validation_passes_for_canonical_project() -> None:
    project = Project(
        project_ref=StableRef("project", "nova"),
        name="NovaVision",
        created_at="2026-03-29T10:15:21Z",
    )

    report = validate_project(project)

    assert report.valid is True


def test_artifact_manifest_requires_non_negative_size() -> None:
    manifest = ArtifactManifest(
        artifact_ref=StableRef("artifact", "checkpoint-01"),
        artifact_kind="checkpoint",
        created_at="2026-03-29T10:29:58Z",
        producer_ref="sdk.python.local",
        run_ref=StableRef("run", "run-01"),
        stage_execution_ref=StableRef("stage", "train"),
        location_ref="file://artifacts/checkpoint-01.ckpt",
        size_bytes=-1,
    )

    report = validate_artifact_manifest(manifest)

    assert report.valid is False
    assert report.issues[0].path == "size_bytes"


def test_project_validation_requires_normalized_timestamp() -> None:
    project = Project(
        project_ref=StableRef("project", "nova"),
        name="NovaVision",
        created_at="2026-03-29T10:15:21",
    )

    report = validate_project(project)

    assert report.valid is False
    assert report.issues[0].path == "created_at"


def test_record_validators_cover_event_metric_and_trace() -> None:
    event_record = StructuredEventRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "evt-1"),
            record_type="structured_event",
            recorded_at="2026-03-29T10:15:21Z",
            observed_at="2026-03-29T10:15:21Z",
            producer_ref="sdk.python.local",
            run_ref=StableRef("run", "run-01"),
            stage_execution_ref=StableRef("stage", "train"),
            operation_context_ref=StableRef("op", "epoch-1"),
        ),
        payload=StructuredEventPayload(
            event_key="training.epoch.started",
            level="info",
            message="Epoch 1 started.",
        ),
    )
    metric_record = MetricRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "metric-1"),
            record_type="metric",
            recorded_at="2026-03-29T10:16:02Z",
            observed_at="2026-03-29T10:16:02Z",
            producer_ref="sdk.python.local",
            run_ref=StableRef("run", "run-01"),
            stage_execution_ref=StableRef("stage", "train"),
            operation_context_ref=StableRef("op", "step-42"),
        ),
        payload=MetricPayload(
            metric_key="training.loss",
            value=0.4821,
            value_type="scalar",
        ),
    )
    trace_record = TraceSpanRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "trace-1"),
            record_type="trace_span",
            recorded_at="2026-03-29T10:16:03Z",
            observed_at="2026-03-29T10:16:03Z",
            producer_ref="sdk.python.local",
            run_ref=StableRef("run", "run-01"),
            stage_execution_ref=StableRef("stage", "train"),
            operation_context_ref=StableRef("op", "step-42"),
        ),
        payload=TraceSpanPayload(
            span_id="span-forward",
            trace_id="trace-train-01",
            parent_span_id="span-step-42",
            span_name="model.forward",
            started_at="2026-03-29T10:16:03Z",
            ended_at="2026-03-29T10:16:04Z",
            status="ok",
            span_kind="model_call",
        ),
    )

    assert validate_structured_event_record(event_record).valid is True
    assert validate_metric_record(metric_record).valid is True
    assert validate_trace_span_record(trace_record).valid is True


def test_trace_validation_rejects_inverted_payload_timestamps() -> None:
    trace_record = TraceSpanRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "trace-1"),
            record_type="trace_span",
            recorded_at="2026-03-29T10:16:05Z",
            observed_at="2026-03-29T10:16:03Z",
            producer_ref="sdk.python.local",
            run_ref=StableRef("run", "run-01"),
            stage_execution_ref=StableRef("stage", "train"),
            operation_context_ref=StableRef("op", "step-42"),
        ),
        payload=TraceSpanPayload(
            span_id="span-forward",
            trace_id="trace-train-01",
            parent_span_id="span-step-42",
            span_name="model.forward",
            started_at="2026-03-29T10:16:04Z",
            ended_at="2026-03-29T10:16:03Z",
            status="ok",
            span_kind="model_call",
        ),
    )

    report = validate_trace_span_record(trace_record)

    assert report.valid is False
    assert any(issue.path == "payload.ended_at" for issue in report.issues)
