"""Example of using Spine inside a simple ML training workflow."""

from spine import (
    ArtifactManifest,
    MetricPayload,
    MetricRecord,
    Project,
    RecordEnvelope,
    Run,
    StableRef,
    StageExecution,
    StructuredEventPayload,
    StructuredEventRecord,
    to_json,
    validate_artifact_manifest,
    validate_metric_record,
    validate_project,
    validate_run,
    validate_stage_execution,
    validate_structured_event_record,
)


def main() -> None:
    project = Project(
        project_ref=StableRef("project", "nova"),
        name="NovaVision",
        created_at="2026-03-30T09:00:00Z",
        description="Image classification experiments.",
        tags={"team": "research", "track": "vision"},
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

    train_stage = StageExecution(
        stage_execution_ref=StableRef("stage", "train"),
        run_ref=run.run_ref,
        stage_name="train",
        status="running",
        started_at="2026-03-30T09:06:00Z",
        order_index=1,
    )
    validate_stage_execution(train_stage).raise_for_errors()

    event = StructuredEventRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "event-epoch-1-start"),
            record_type="structured_event",
            recorded_at="2026-03-30T09:07:00Z",
            observed_at="2026-03-30T09:07:00Z",
            producer_ref="scribe.python.local",
            run_ref=run.run_ref,
            stage_execution_ref=train_stage.stage_execution_ref,
            operation_context_ref=None,
        ),
        payload=StructuredEventPayload(
            event_key="training.epoch.started",
            level="info",
            message="Epoch 1 started.",
        ),
    )
    validate_structured_event_record(event).raise_for_errors()

    metric = MetricRecord(
        envelope=RecordEnvelope(
            record_ref=StableRef("record", "metric-step-42"),
            record_type="metric",
            recorded_at="2026-03-30T09:08:30Z",
            observed_at="2026-03-30T09:08:30Z",
            producer_ref="scribe.python.local",
            run_ref=run.run_ref,
            stage_execution_ref=train_stage.stage_execution_ref,
            operation_context_ref=StableRef("op", "step-42"),
        ),
        payload=MetricPayload(
            metric_key="training.loss",
            value=0.4821,
            value_type="scalar",
            unit="ratio",
            tags={"device": "cuda:0"},
        ),
    )
    validate_metric_record(metric).raise_for_errors()

    checkpoint = ArtifactManifest(
        artifact_ref=StableRef("artifact", "checkpoint-epoch-1"),
        artifact_kind="checkpoint",
        created_at="2026-03-30T09:20:00Z",
        producer_ref="scribe.python.local",
        run_ref=run.run_ref,
        stage_execution_ref=train_stage.stage_execution_ref,
        location_ref="file://artifacts/checkpoints/epoch_1.ckpt",
        hash_value="sha256:abc123",
        size_bytes=184223744,
        attributes={"framework": "pytorch", "dtype": "float16"},
    )
    validate_artifact_manifest(checkpoint).raise_for_errors()

    print(to_json(project))
    print(to_json(run))
    print(to_json(event))
    print(to_json(metric))
    print(to_json(checkpoint))


if __name__ == "__main__":
    main()
