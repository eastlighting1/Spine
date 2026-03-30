"""Validation report types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ValidationReport:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    def raise_for_errors(self) -> None:
        if self.valid:
            return
        from ..exceptions import ValidationError

        details = "; ".join(f"{issue.path}: {issue.message}" for issue in self.issues)
        raise ValidationError(details)
