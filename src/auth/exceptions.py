"""Authentication exceptions for EduIG-Pipeline."""

from src.exceptions import PipelineError


class AuthenticationError(PipelineError):
    """Base exception for authentication failures."""

    pass


class SessionExpiredError(AuthenticationError):
    """Raised when an active session has expired and requires re-login."""

    pass


class AccountLockedError(AuthenticationError):
    """Raised when the Instagram account is locked, suspended, or challenged."""

    pass


class TwoFARequiredError(AuthenticationError):
    """Raised when Two-Factor Authentication is required but cannot be completed."""

    pass
