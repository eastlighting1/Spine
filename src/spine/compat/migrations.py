"""Compatibility migration helpers."""

from __future__ import annotations

from typing import Any

from ..models import SCHEMA_VERSION, normalize_timestamp
from .types import CompatibilityNote


def migrate_project_090_to_100(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], tuple[CompatibilityNote, ...]]:
    migrated = dict(payload)
    notes: list[CompatibilityNote] = []

    if "ref" in migrated and "project_ref" not in migrated:
        migrated["project_ref"] = migrated["ref"]
        notes.append(CompatibilityNote(path="ref", message="Mapped legacy 'ref' to 'project_ref'."))

    if "created" in migrated and "created_at" not in migrated:
        migrated["created_at"] = migrated["created"]
        notes.append(
            CompatibilityNote(path="created", message="Mapped legacy 'created' to 'created_at'.")
        )

    if "created_at" in migrated:
        migrated["created_at"] = normalize_timestamp(str(migrated["created_at"]))

    migrated["schema_version"] = SCHEMA_VERSION
    notes.append(
        CompatibilityNote(
            path="schema_version",
            message=f"Upgraded payload from 0.9.0 to {SCHEMA_VERSION}.",
        )
    )
    return migrated, tuple(notes)


def migrate_artifact_090_to_100(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], tuple[CompatibilityNote, ...]]:
    migrated = dict(payload)
    notes: list[CompatibilityNote] = []

    if migrated.get("hash_value") is None and "hash" in migrated:
        migrated["hash_value"] = migrated["hash"]
        notes.append(
            CompatibilityNote(path="hash", message="Mapped legacy 'hash' to 'hash_value'.")
        )

    if "created_at" in migrated:
        migrated["created_at"] = normalize_timestamp(str(migrated["created_at"]))

    migrated["schema_version"] = SCHEMA_VERSION
    notes.append(
        CompatibilityNote(
            path="schema_version",
            message=f"Upgraded payload from 0.9.0 to {SCHEMA_VERSION}.",
        )
    )
    return migrated, tuple(notes)
