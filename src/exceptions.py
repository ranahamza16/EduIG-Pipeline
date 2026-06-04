"""Custom exceptions for EduIG-Pipeline.

Provides a unified hierarchy of exceptions for pipeline operations.
"""


class PipelineError(Exception):
    """Base exception for all pipeline errors."""


class RateLimitExceededError(PipelineError):
    """Raised when the hourly or daily request cap is reached."""


class CircuitBreakerError(PipelineError):
    """Raised when the circuit trips due to too many consecutive failures."""


class ExtractionError(PipelineError):
    """Base class for extraction errors."""


class PrivateProfileError(ExtractionError):
    """Raised when a profile is private and cannot be extracted."""


class ProfileNotFoundError(ExtractionError):
    """Raised when a profile does not exist (404)."""
