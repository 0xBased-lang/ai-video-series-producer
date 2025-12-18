"""
Core Module
===========

Core utilities, configuration, and exceptions for the AI Video Series Producer.
"""

from .config import Config, VideoConfig, GenerationConfig, QualityConfig
from .exceptions import (
    VideoProducerError,
    ConfigurationError,
    ProviderError,
    GenerationError,
    ValidationError,
    SecurityError,
)
from .security import PathValidator, sanitize_filename

__all__ = [
    # Configuration
    "Config",
    "VideoConfig",
    "GenerationConfig",
    "QualityConfig",
    # Exceptions
    "VideoProducerError",
    "ConfigurationError",
    "ProviderError",
    "GenerationError",
    "ValidationError",
    "SecurityError",
    # Security
    "PathValidator",
    "sanitize_filename",
]
