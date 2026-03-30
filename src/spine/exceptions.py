"""Typed exceptions for Spine contract handling."""

from __future__ import annotations


class SpineError(Exception):
    """Base exception for Spine."""


class ValidationError(SpineError):
    """Raised when canonical validation fails."""


class SerializationError(SpineError):
    """Raised when serialization or deserialization fails."""


class CompatibilityError(SpineError):
    """Raised when a payload cannot be read under compatibility rules."""


class ExtensionError(SpineError):
    """Raised when extension registration violates policy."""
