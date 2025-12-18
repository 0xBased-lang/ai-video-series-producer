"""
Base Video Provider V2
======================

Enhanced base class with shared functionality, consistent error handling,
retry logic, and reduced duplication across providers.
"""

import asyncio
import logging
import os
import base64
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Callable
import httpx

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

from ..core.exceptions import (
    ProviderError,
    GenerationError,
    ValidationError,
    TimeoutError,
    RateLimitError,
)
from ..core.security import PathValidator, sanitize_prompt, redact_api_key

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================


# Subprocess timeout in seconds
SUBPROCESS_TIMEOUT = 30

# Default retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0
DEFAULT_RETRY_MULTIPLIER = 2.0
DEFAULT_TIMEOUT = 300


# =============================================================================
# Data Classes
# =============================================================================


class GenerationStatus(Enum):
    """Status of a video generation job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def from_provider_status(cls, status: str) -> "GenerationStatus":
        """
        Normalize provider-specific status strings to GenerationStatus.

        This centralizes the status mapping that was duplicated across providers.
        """
        status_lower = status.lower().strip()

        # Completed states
        if status_lower in ("completed", "succeeded", "done", "success", "finished"):
            return cls.COMPLETED

        # Failed states
        if status_lower in ("failed", "error", "failure", "errored"):
            return cls.FAILED

        # Cancelled states
        if status_lower in ("cancelled", "canceled", "aborted", "stopped"):
            return cls.CANCELLED

        # Pending states
        if status_lower in ("pending", "queued", "in_queue", "waiting", "scheduled"):
            return cls.PENDING

        # Default to processing
        return cls.PROCESSING


@dataclass
class VideoGenerationResult:
    """Result of a video generation request."""

    # Core result data
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    status: GenerationStatus = GenerationStatus.PENDING

    # Generation metadata
    job_id: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Generation parameters (for reproducibility)
    prompt: Optional[str] = None
    reference_images: List[str] = field(default_factory=list)
    seed: Optional[int] = None
    generation_params: Dict[str, Any] = field(default_factory=dict)

    # Quality metrics
    quality_score: Optional[float] = None
    consistency_score: Optional[float] = None

    # For chaining
    last_frame_path: Optional[str] = None
    thumbnail_path: Optional[str] = None

    # Error handling
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    # Cost tracking
    cost_usd: Optional[float] = None

    def is_complete(self) -> bool:
        """Check if generation completed successfully."""
        return self.status == GenerationStatus.COMPLETED and self.video_url is not None

    def is_failed(self) -> bool:
        """Check if generation failed."""
        return self.status == GenerationStatus.FAILED

    def is_pending(self) -> bool:
        """Check if generation is still pending or processing."""
        return self.status in (GenerationStatus.PENDING, GenerationStatus.PROCESSING)

    def validate_state(self) -> None:
        """Validate that the result state is consistent."""
        if self.status == GenerationStatus.COMPLETED and not self.video_url:
            raise ValidationError(
                "Completed status but no video URL",
                field="video_url",
                constraint="required when status is COMPLETED",
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "video_url": self.video_url,
            "video_path": self.video_path,
            "status": self.status.value,
            "job_id": self.job_id,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "prompt": self.prompt,
            "reference_images": self.reference_images,
            "seed": self.seed,
            "generation_params": self.generation_params,
            "quality_score": self.quality_score,
            "consistency_score": self.consistency_score,
            "last_frame_path": self.last_frame_path,
            "thumbnail_path": self.thumbnail_path,
            "error_message": self.error_message,
            "cost_usd": self.cost_usd,
        }


@dataclass
class GenerationRequest:
    """Request parameters for video generation."""

    # Required
    prompt: str

    # Optional reference images (paths or URLs)
    reference_images: List[str] = field(default_factory=list)

    # Video settings
    duration: int = 5  # seconds
    resolution: str = "720p"
    aspect_ratio: str = "16:9"
    fps: int = 24

    # First/last frame control
    first_frame: Optional[str] = None  # image path or URL
    last_frame: Optional[str] = None

    # Style control
    style_reference: Optional[str] = None
    negative_prompt: Optional[str] = None

    # Generation control
    seed: Optional[int] = None
    guidance_scale: Optional[float] = None

    # Audio
    with_audio: bool = False

    # Provider-specific
    model: Optional[str] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and sanitize request."""
        self.prompt = sanitize_prompt(self.prompt)
        if self.negative_prompt:
            self.negative_prompt = sanitize_prompt(self.negative_prompt)


# =============================================================================
# Base Provider Class
# =============================================================================


class BaseVideoProvider(ABC):
    """
    Enhanced abstract base class for video generation providers.

    Features:
    - Thread-safe client management
    - Automatic retry with exponential backoff
    - Shared download functionality
    - Consistent error handling
    - Status normalization
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        output_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the provider.

        Args:
            api_key: API key (or read from environment)
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
            output_path: Base path for downloaded files
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.base_url = base_url or self._get_default_base_url()
        self.timeout = timeout
        self.max_retries = max_retries
        self.output_path = Path(output_path) if output_path else Path("./output")

        # HTTP client with lock for thread safety
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

        # Path validator for secure file operations
        self._path_validator = PathValidator(self.output_path)

        # Validate configuration
        self._validate_config()

    # -------------------------------------------------------------------------
    # Abstract Methods (must be implemented by subclasses)
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Return list of supported models."""
        pass

    @property
    @abstractmethod
    def env_key_name(self) -> str:
        """Return the environment variable name for the API key."""
        pass

    @abstractmethod
    def _get_default_base_url(self) -> str:
        """Return the default base URL for this provider."""
        pass

    @abstractmethod
    async def _make_generation_request(
        self,
        request: GenerationRequest,
    ) -> Dict[str, Any]:
        """
        Make the actual API request for video generation.

        Subclasses implement provider-specific request logic.

        Args:
            request: Generation request parameters

        Returns:
            Raw API response data
        """
        pass

    @abstractmethod
    async def _check_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check job status from the provider.

        Subclasses implement provider-specific status checking.

        Args:
            job_id: The job ID to check

        Returns:
            Raw status response data
        """
        pass

    @abstractmethod
    def _parse_response(
        self,
        data: Dict[str, Any],
        result: VideoGenerationResult,
    ) -> VideoGenerationResult:
        """
        Parse provider-specific response into VideoGenerationResult.

        Args:
            data: Raw API response
            result: Result object to populate

        Returns:
            Updated VideoGenerationResult
        """
        pass

    # -------------------------------------------------------------------------
    # Shared Implementation Methods
    # -------------------------------------------------------------------------

    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """
        Generate a video from the request with retry logic.

        This is the main entry point that handles:
        - Retry logic with exponential backoff
        - Error handling and logging
        - Result normalization

        Args:
            request: Generation request parameters

        Returns:
            VideoGenerationResult with the generated video
        """
        result = VideoGenerationResult(
            provider=self.provider_name,
            prompt=request.prompt,
            reference_images=request.reference_images,
            model=request.model,
        )

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = DEFAULT_RETRY_DELAY * (DEFAULT_RETRY_MULTIPLIER ** (attempt - 1))
                    logger.info(f"Retry {attempt}/{self.max_retries} after {delay:.1f}s delay")
                    await asyncio.sleep(delay)

                # Make the generation request
                logger.info(f"Generating video with {self.provider_name} (attempt {attempt + 1})")
                data = await self._make_generation_request(request)

                # Handle async vs sync response
                if self._is_async_response(data):
                    result.job_id = self._extract_job_id(data)
                    result.status = GenerationStatus.PROCESSING
                    result = await self.wait_for_completion(result.job_id)
                else:
                    result = self._parse_response(data, result)

                # Validate result state
                result.validate_state()

                return result

            except RateLimitError as e:
                # Always retry rate limits
                last_error = e
                logger.warning(f"Rate limited: {e}")
                continue

            except ProviderError as e:
                last_error = e
                if not e.recoverable:
                    raise
                logger.warning(f"Recoverable provider error: {e}")
                continue

            except Exception as e:
                logger.error(f"Generation failed: {redact_api_key(str(e))}")
                result.status = GenerationStatus.FAILED
                result.error_message = str(e)
                return result

        # All retries exhausted
        result.status = GenerationStatus.FAILED
        result.error_message = f"All retries exhausted. Last error: {last_error}"
        return result

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """
        Check the status of a generation job.

        Args:
            job_id: The job ID to check

        Returns:
            Updated VideoGenerationResult
        """
        result = VideoGenerationResult(job_id=job_id, provider=self.provider_name)

        try:
            data = await self._check_job_status(job_id)
            status_str = self._extract_status(data)
            result.status = GenerationStatus.from_provider_status(status_str)

            if result.status == GenerationStatus.COMPLETED:
                result = self._parse_response(data, result)
            elif result.status == GenerationStatus.FAILED:
                result.error_message = self._extract_error(data)

            return result

        except Exception as e:
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            return result

    async def download_video(
        self,
        result: VideoGenerationResult,
        output_path: Union[str, Path],
    ) -> str:
        """
        Download the generated video to local storage.

        This shared implementation handles:
        - Path validation for security
        - Async file I/O when available
        - Error handling with meaningful messages

        Args:
            result: The generation result with video URL
            output_path: Where to save the video

        Returns:
            Path to the downloaded video
        """
        if not result.video_url:
            raise ValidationError(
                "No video URL available to download",
                field="video_url",
                constraint="required for download",
            )

        # Validate and resolve output path
        try:
            output_path = self._path_validator.validate_video(output_path)
        except Exception:
            # If validation fails, use safe path within output directory
            safe_name = Path(output_path).name
            output_path = self.output_path / "videos" / safe_name

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            client = await self._get_client()
            response = await client.get(result.video_url)

            if response.status_code != 200:
                raise ProviderError(
                    f"Download failed with status {response.status_code}",
                    provider=self.provider_name,
                    status_code=response.status_code,
                )

            # Use async file I/O if available
            if HAS_AIOFILES:
                async with aiofiles.open(output_path, "wb") as f:
                    await f.write(response.content)
            else:
                with open(output_path, "wb") as f:
                    f.write(response.content)

            result.video_path = str(output_path)
            logger.info(f"Video downloaded to: {output_path}")

            return str(output_path)

        except httpx.TimeoutException:
            raise TimeoutError(
                "Download timed out",
                operation="download_video",
                timeout_seconds=self.timeout,
            )
        except Exception as e:
            raise ProviderError(
                f"Download failed: {e}",
                provider=self.provider_name,
            )

    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
    ) -> VideoGenerationResult:
        """
        Wait for a generation job to complete.

        Args:
            job_id: The job ID to wait for
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            Final VideoGenerationResult
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            result = await self.check_status(job_id)

            if result.status in (GenerationStatus.COMPLETED, GenerationStatus.FAILED):
                return result

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= max_wait:
                raise TimeoutError(
                    f"Job {job_id} timed out after {max_wait} seconds",
                    operation="wait_for_completion",
                    timeout_seconds=max_wait,
                )

            logger.debug(f"Job {job_id} status: {result.status.value}, waiting...")
            await asyncio.sleep(poll_interval)

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.getenv(self.env_key_name)

    def _validate_config(self) -> None:
        """Validate the provider configuration."""
        if not self.api_key:
            logger.warning(
                f"No API key found for {self.provider_name}. "
                f"Set {self.env_key_name} environment variable or pass api_key parameter."
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client (thread-safe)."""
        async with self._client_lock:
            if self._client is None:
                self._client = httpx.AsyncClient(
                    timeout=httpx.Timeout(self.timeout),
                    headers=self._get_headers(),
                )
            return self._client

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _is_async_response(self, data: Dict[str, Any]) -> bool:
        """Check if response indicates async processing."""
        return "request_id" in data or "job_id" in data or "id" in data

    def _extract_job_id(self, data: Dict[str, Any]) -> str:
        """Extract job ID from response."""
        return data.get("request_id") or data.get("job_id") or data.get("id") or ""

    def _extract_status(self, data: Dict[str, Any]) -> str:
        """Extract status string from response."""
        return data.get("status") or data.get("state") or "unknown"

    def _extract_error(self, data: Dict[str, Any]) -> str:
        """Extract error message from response."""
        return (
            data.get("error")
            or data.get("error_message")
            or data.get("message")
            or "Unknown error"
        )

    # -------------------------------------------------------------------------
    # Image Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def encode_image_to_base64(image_path: Union[str, Path]) -> str:
        """Encode an image file to base64."""
        path = Path(image_path)
        if not path.exists():
            raise ValidationError(
                f"Image not found: {image_path}",
                field="image_path",
                value=str(image_path),
            )

        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    @staticmethod
    def get_mime_type(image_path: Union[str, Path]) -> str:
        """Get MIME type from file extension."""
        ext = Path(image_path).suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mime_types.get(ext, "image/jpeg")

    def prepare_reference_images(
        self,
        images: List[str],
        encode: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Prepare reference images for API request.

        Args:
            images: List of image paths or URLs
            encode: Whether to base64 encode local files

        Returns:
            List of prepared image objects
        """
        prepared = []

        for img in images:
            if img.startswith(("http://", "https://")):
                # URL - use directly
                prepared.append({"url": img})
            elif encode:
                # Local file - encode to base64
                mime_type = self.get_mime_type(img)
                b64_data = self.encode_image_to_base64(img)
                prepared.append({
                    "data": f"data:{mime_type};base64,{b64_data}",
                    "mime_type": mime_type,
                })
            else:
                prepared.append({"path": img})

        return prepared

    # -------------------------------------------------------------------------
    # Provider Capabilities
    # -------------------------------------------------------------------------

    @property
    def supports_reference_images(self) -> bool:
        """Whether this provider supports reference images."""
        return True

    @property
    def max_reference_images(self) -> int:
        """Maximum number of reference images supported."""
        return 1

    @property
    def supports_audio(self) -> bool:
        """Whether this provider supports audio generation."""
        return False

    @property
    def supports_scene_extension(self) -> bool:
        """Whether this provider supports extending scenes."""
        return False

    @property
    def supports_lora(self) -> bool:
        """Whether this provider supports LoRA fine-tuning."""
        return False

    @property
    def max_duration(self) -> int:
        """Maximum video duration in seconds."""
        return 10

    @property
    def supported_resolutions(self) -> List[str]:
        """List of supported resolutions."""
        return ["480p", "720p", "1080p"]

    @property
    def supported_aspect_ratios(self) -> List[str]:
        """List of supported aspect ratios."""
        return ["16:9", "9:16", "1:1"]

    # -------------------------------------------------------------------------
    # Context Manager Protocol
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client."""
        async with self._client_lock:
            if self._client:
                await self._client.aclose()
                self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
