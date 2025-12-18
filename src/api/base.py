"""
Base Video Provider
===================

Abstract base class for all video generation API providers.
"""

import os
import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import base64
import httpx

logger = logging.getLogger(__name__)


class GenerationStatus(Enum):
    """Status of a video generation job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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


class BaseVideoProvider(ABC):
    """
    Abstract base class for video generation providers.

    All provider implementations must inherit from this class
    and implement the required abstract methods.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 300,
        max_retries: int = 3,
    ):
        """
        Initialize the provider.

        Args:
            api_key: API key (or read from environment)
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries on failure
        """
        self.api_key = api_key or self._get_api_key_from_env()
        self.base_url = base_url or self._get_default_base_url()
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None

        # Validate configuration
        self._validate_config()

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
    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """
        Generate a video from the request.

        Args:
            request: Generation request parameters

        Returns:
            VideoGenerationResult with the generated video
        """
        pass

    @abstractmethod
    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """
        Check the status of a generation job.

        Args:
            job_id: The job ID to check

        Returns:
            Updated VideoGenerationResult
        """
        pass

    @abstractmethod
    async def download_video(
        self,
        result: VideoGenerationResult,
        output_path: Union[str, Path],
    ) -> str:
        """
        Download the generated video to local storage.

        Args:
            result: The generation result with video URL
            output_path: Where to save the video

        Returns:
            Path to the downloaded video
        """
        pass

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
        """Get or create the HTTP client."""
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

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def encode_image_to_base64(image_path: Union[str, Path]) -> str:
        """Encode an image file to base64."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

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
                result.status = GenerationStatus.FAILED
                result.error_message = f"Timeout after {max_wait} seconds"
                return result

            logger.debug(f"Job {job_id} status: {result.status.value}, waiting...")
            await asyncio.sleep(poll_interval)

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
