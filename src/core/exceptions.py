"""
Custom Exceptions
=================

Unified exception hierarchy for consistent error handling across the framework.
"""

from typing import Optional, Dict, Any


class VideoProducerError(Exception):
    """Base exception for all Video Producer errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.recoverable = recoverable

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }


class ConfigurationError(VideoProducerError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        if expected_type:
            details["expected_type"] = expected_type
        super().__init__(message, details=details, **kwargs)


class ProviderError(VideoProducerError):
    """Provider/API-related errors."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider
        if status_code:
            details["status_code"] = status_code
        if response_body:
            # Truncate large responses
            details["response_body"] = response_body[:500] if len(response_body) > 500 else response_body

        # Most provider errors are recoverable with retry
        recoverable = kwargs.pop("recoverable", status_code in (429, 500, 502, 503, 504) if status_code else False)
        super().__init__(message, recoverable=recoverable, details=details, **kwargs)


class GenerationError(VideoProducerError):
    """Video generation errors."""

    def __init__(
        self,
        message: str,
        job_id: Optional[str] = None,
        stage: Optional[str] = None,
        prompt: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if job_id:
            details["job_id"] = job_id
        if stage:
            details["stage"] = stage
        if prompt:
            # Truncate long prompts
            details["prompt"] = prompt[:200] if len(prompt) > 200 else prompt
        super().__init__(message, details=details, **kwargs)


class ValidationError(VideoProducerError):
    """Input/output validation errors."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]
        if constraint:
            details["constraint"] = constraint
        super().__init__(message, details=details, **kwargs)


class SecurityError(VideoProducerError):
    """Security-related errors (path traversal, injection attempts, etc.)."""

    def __init__(
        self,
        message: str,
        attempted_path: Optional[str] = None,
        security_type: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if attempted_path:
            # Don't expose full paths in error details
            details["attempted_path"] = "***REDACTED***"
        if security_type:
            details["security_type"] = security_type
        super().__init__(message, recoverable=False, details=details, **kwargs)


class TimeoutError(VideoProducerError):
    """Operation timeout errors."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(message, recoverable=True, details=details, **kwargs)


class RateLimitError(ProviderError):
    """Rate limit exceeded errors."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, status_code=429, recoverable=True, details=details, **kwargs)


class ResourceNotFoundError(VideoProducerError):
    """Resource not found errors."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, recoverable=False, details=details, **kwargs)
