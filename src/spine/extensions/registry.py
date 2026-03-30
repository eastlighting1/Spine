"""Governed extension registration."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..exceptions import ExtensionError


@dataclass(slots=True)
class ExtensionRegistry:
    """Registry for explicit extension namespaces."""

    _owners: dict[str, str] = field(default_factory=dict)

    def register(self, namespace: str, owner: str) -> None:
        if "." not in namespace:
            raise ExtensionError("Extension namespace must contain a '.' separator.")
        existing = self._owners.get(namespace)
        if existing is not None and existing != owner:
            raise ExtensionError(
                f"Namespace {namespace!r} is already registered to owner {existing!r}."
            )
        self._owners[namespace] = owner

    def is_registered(self, namespace: str) -> bool:
        return namespace in self._owners

    def owner_for(self, namespace: str) -> str | None:
        return self._owners.get(namespace)
