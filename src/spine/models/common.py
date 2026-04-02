"""Common canonical primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import re
from types import MappingProxyType
from typing import Any, Mapping


REF_KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
REF_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
SCHEMA_VERSION = "1.0.0"


def normalize_timestamp(value: str | datetime) -> str:
    """Return an ISO-8601 UTC timestamp with trailing Z."""
    if isinstance(value, datetime):
        dt = value
    else:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.isoformat().replace("+00:00", "Z")


def _frozen_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not values:
        return MappingProxyType({})
    ordered = {key: values[key] for key in sorted(values)}
    return MappingProxyType(ordered)


@dataclass(frozen=True, slots=True)
class StableRef:
    """Stable namespaced canonical reference."""

    kind: str
    value: str

    def __post_init__(self) -> None:
        if not REF_KIND_PATTERN.fullmatch(self.kind):
            raise ValueError(f"Invalid ref kind: {self.kind!r}")
        if not REF_VALUE_PATTERN.fullmatch(self.value):
            raise ValueError(f"Invalid ref value: {self.value!r}")

    def __str__(self) -> str:
        return f"{self.kind}:{self.value}"

    @classmethod
    def parse(cls, raw: str) -> "StableRef":
        kind, sep, value = raw.partition(":")
        if not sep:
            raise ValueError(f"StableRef must contain ':': {raw!r}")
        return cls(kind=kind, value=value)

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True, slots=True)
class ExtensionFieldSet:
    """Governed extension values registered under a namespace."""

    namespace: str
    fields: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if "." not in self.namespace:
            raise ValueError("Extension namespace must contain a '.' separator.")
        object.__setattr__(self, "fields", _frozen_mapping(self.fields))

    def to_dict(self) -> dict[str, Any]:
        return {"namespace": self.namespace, "fields": self.fields}
