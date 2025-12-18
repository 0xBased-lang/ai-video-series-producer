"""
Security Utilities
==================

Path validation, input sanitization, and security utilities.
"""

import re
import os
import logging
from pathlib import Path
from typing import Optional, Union, Set

from .exceptions import SecurityError

logger = logging.getLogger(__name__)


class PathValidator:
    """
    Validates file paths to prevent directory traversal and other attacks.

    Usage:
        validator = PathValidator(base_path="/app/data")
        safe_path = validator.validate("/app/data/videos/file.mp4")  # OK
        safe_path = validator.validate("../../etc/passwd")  # Raises SecurityError
    """

    # Dangerous patterns that should never appear in paths
    DANGEROUS_PATTERNS = [
        r"\.\./",  # Parent directory traversal
        r"\.\.\\",  # Windows parent directory
        r"^/etc/",  # System directories
        r"^/var/",
        r"^/usr/",
        r"^/root/",
        r"^~",  # Home directory expansion
        r"\x00",  # Null bytes
        r"%2e%2e",  # URL-encoded traversal
        r"%252e",  # Double-encoded
    ]

    # Allowed file extensions (whitelist approach)
    ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    ALLOWED_DATA_EXTENSIONS = {".json", ".yaml", ".yml", ".db", ".sqlite"}

    def __init__(
        self,
        base_path: Union[str, Path],
        allowed_extensions: Optional[Set[str]] = None,
    ):
        """
        Initialize the path validator.

        Args:
            base_path: The base directory that all paths must be within
            allowed_extensions: Set of allowed file extensions (None = all allowed)
        """
        self.base_path = Path(base_path).resolve()
        self.allowed_extensions = allowed_extensions

        # Ensure base path exists and is a directory
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS]

    def validate(self, path: Union[str, Path]) -> Path:
        """
        Validate a path and return the resolved safe path.

        Args:
            path: Path to validate (relative or absolute)

        Returns:
            Resolved Path object

        Raises:
            SecurityError: If path is potentially malicious
        """
        path_str = str(path)

        # Check for dangerous patterns
        for pattern in self._compiled_patterns:
            if pattern.search(path_str):
                logger.warning(f"Blocked dangerous path pattern: {pattern.pattern}")
                raise SecurityError(
                    "Path contains dangerous pattern",
                    attempted_path=path_str,
                    security_type="path_traversal",
                )

        # Resolve the path
        try:
            if Path(path).is_absolute():
                resolved = Path(path).resolve()
            else:
                resolved = (self.base_path / path).resolve()
        except (ValueError, OSError) as e:
            raise SecurityError(
                f"Invalid path: {e}",
                attempted_path=path_str,
                security_type="invalid_path",
            )

        # Ensure path is within base directory
        try:
            resolved.relative_to(self.base_path)
        except ValueError:
            logger.warning(f"Blocked path outside base directory: {resolved}")
            raise SecurityError(
                "Path is outside allowed directory",
                attempted_path=path_str,
                security_type="path_traversal",
            )

        # Check file extension if restrictions are set
        if self.allowed_extensions and resolved.suffix.lower() not in self.allowed_extensions:
            raise SecurityError(
                f"File extension not allowed: {resolved.suffix}",
                attempted_path=path_str,
                security_type="invalid_extension",
            )

        return resolved

    def validate_image(self, path: Union[str, Path]) -> Path:
        """Validate an image file path."""
        resolved = self.validate(path)
        if resolved.suffix.lower() not in self.ALLOWED_IMAGE_EXTENSIONS:
            raise SecurityError(
                f"Not a valid image extension: {resolved.suffix}",
                attempted_path=str(path),
                security_type="invalid_extension",
            )
        return resolved

    def validate_video(self, path: Union[str, Path]) -> Path:
        """Validate a video file path."""
        resolved = self.validate(path)
        if resolved.suffix.lower() not in self.ALLOWED_VIDEO_EXTENSIONS:
            raise SecurityError(
                f"Not a valid video extension: {resolved.suffix}",
                attempted_path=str(path),
                security_type="invalid_extension",
            )
        return resolved

    def is_safe(self, path: Union[str, Path]) -> bool:
        """Check if a path is safe without raising an exception."""
        try:
            self.validate(path)
            return True
        except SecurityError:
            return False


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing dangerous characters.

    Args:
        filename: Original filename
        max_length: Maximum allowed length

    Returns:
        Sanitized filename safe for filesystem operations
    """
    if not filename:
        return "unnamed"

    # Remove or replace dangerous characters
    # Keep: alphanumeric, underscore, hyphen, dot, space
    sanitized = re.sub(r"[^\w\-. ]", "_", filename)

    # Remove multiple consecutive underscores/spaces
    sanitized = re.sub(r"[_\s]+", "_", sanitized)

    # Remove leading/trailing special characters
    sanitized = sanitized.strip("._- ")

    # Prevent hidden files
    if sanitized.startswith("."):
        sanitized = "_" + sanitized

    # Truncate if too long (preserve extension)
    if len(sanitized) > max_length:
        name = Path(sanitized).stem
        ext = Path(sanitized).suffix
        max_name_len = max_length - len(ext)
        sanitized = name[:max_name_len] + ext

    # Fallback if empty after sanitization
    if not sanitized or sanitized in (".", ".."):
        sanitized = "unnamed"

    return sanitized


def sanitize_prompt(prompt: str, max_length: int = 2000) -> str:
    """
    Sanitize a prompt string to prevent injection attacks.

    Args:
        prompt: User-provided prompt
        max_length: Maximum allowed length

    Returns:
        Sanitized prompt string
    """
    if not prompt:
        return ""

    # Remove control characters
    sanitized = "".join(char for char in prompt if char.isprintable() or char in "\n\t")

    # Remove potential injection patterns
    # These might be used to manipulate AI models
    injection_patterns = [
        r"ignore previous instructions",
        r"disregard above",
        r"system prompt",
        r"\[INST\]",
        r"\[/INST\]",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
    ]

    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
        logger.warning(f"Prompt truncated from {len(prompt)} to {max_length} characters")

    return sanitized.strip()


def redact_api_key(text: str) -> str:
    """
    Redact API keys and sensitive tokens from text.

    Args:
        text: Text that might contain API keys

    Returns:
        Text with API keys redacted
    """
    if not text:
        return text

    # Common API key patterns
    patterns = [
        # Generic Bearer tokens
        (r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer ***REDACTED***"),
        # fal.ai keys
        (r"fal_[A-Za-z0-9]+", "fal_***REDACTED***"),
        # Google API keys
        (r"AIza[A-Za-z0-9_\-]{35}", "AIza***REDACTED***"),
        # Runway keys
        (r"rway_[A-Za-z0-9]+", "rway_***REDACTED***"),
        # Generic API key patterns
        (r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-]+", "api_key: ***REDACTED***"),
        # Environment variable patterns
        (r"(FAL_API_KEY|GOOGLE_API_KEY|RUNWAY_API_KEY|REPLICATE_API_TOKEN)=[^\s]+", r"\1=***REDACTED***"),
    ]

    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def validate_url(url: str, allowed_hosts: Optional[Set[str]] = None) -> str:
    """
    Validate a URL for safety.

    Args:
        url: URL to validate
        allowed_hosts: Set of allowed hostnames (None = all HTTPS allowed)

    Returns:
        Validated URL

    Raises:
        SecurityError: If URL is potentially malicious
    """
    from urllib.parse import urlparse

    if not url:
        raise SecurityError("Empty URL", security_type="invalid_url")

    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise SecurityError(f"Invalid URL format: {e}", security_type="invalid_url")

    # Only allow HTTP/HTTPS
    if parsed.scheme not in ("http", "https"):
        raise SecurityError(
            f"Invalid URL scheme: {parsed.scheme}",
            security_type="invalid_url_scheme",
        )

    # Block local/private addresses
    hostname = parsed.hostname or ""
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
    if hostname.lower() in blocked_hosts:
        raise SecurityError(
            "URLs to local addresses are not allowed",
            security_type="blocked_host",
        )

    # Check for IP address patterns that might be internal
    if re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)", hostname):
        raise SecurityError(
            "URLs to private IP addresses are not allowed",
            security_type="blocked_host",
        )

    # Check allowed hosts if specified
    if allowed_hosts and hostname.lower() not in allowed_hosts:
        raise SecurityError(
            f"Host not in allowed list: {hostname}",
            security_type="blocked_host",
        )

    return url
