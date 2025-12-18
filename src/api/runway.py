"""
Runway Gen-4 Provider
=====================

Integration with Runway's Gen-4 video generation API.

Key Features:
- Persistent visual memory for character consistency
- Single reference image support
- Sophisticated camera controls
- 5 or 10 second durations
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

import httpx

from .base import (
    BaseVideoProvider,
    VideoGenerationResult,
    GenerationRequest,
    GenerationStatus,
)
from .factory import register_provider

logger = logging.getLogger(__name__)


@register_provider("runway")
class RunwayProvider(BaseVideoProvider):
    """
    Runway Gen-4 video generation provider.

    Features persistent visual memory for maintaining
    consistent characters across generations.
    """

    @property
    def provider_name(self) -> str:
        return "Runway"

    @property
    def supported_models(self) -> List[str]:
        return ["gen-4-turbo", "gen-4"]

    @property
    def env_key_name(self) -> str:
        return "RUNWAY_API_KEY"

    def _get_default_base_url(self) -> str:
        return "https://api.runwayml.com/v1"

    @property
    def max_reference_images(self) -> int:
        return 1  # Gen-4 uses single reference for consistency

    @property
    def supported_aspect_ratios(self) -> List[str]:
        return ["16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]

    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """
        Generate a video using Runway Gen-4.

        Args:
            request: Generation request parameters

        Returns:
            VideoGenerationResult
        """
        result = VideoGenerationResult(
            provider=self.provider_name,
            prompt=request.prompt,
            reference_images=request.reference_images,
            model=request.model or "gen-4-turbo",
        )

        try:
            # Build request payload
            payload = self._build_payload(request)

            logger.info(f"Generating video with Runway {result.model}")

            # Make API request
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/generations",
                json=payload,
            )

            if response.status_code not in (200, 201, 202):
                result.status = GenerationStatus.FAILED
                result.error_message = f"API error: {response.status_code} - {response.text}"
                return result

            data = response.json()

            # Runway returns a generation ID for polling
            if "id" in data:
                result.job_id = data["id"]
                result.status = GenerationStatus.PROCESSING

                # Poll for completion
                result = await self.wait_for_completion(result.job_id)
            elif "output" in data:
                # Immediate result
                result.video_url = data["output"]
                result.status = GenerationStatus.COMPLETED
                result.completed_at = datetime.now()
            else:
                result.status = GenerationStatus.FAILED
                result.error_message = "Unexpected response format"

            return result

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            return result

    def _build_payload(self, request: GenerationRequest) -> Dict[str, Any]:
        """Build the Runway API request payload."""
        payload = {
            "prompt": request.prompt,
        }

        # Duration (5 or 10 seconds)
        duration = request.duration
        if duration not in (5, 10):
            duration = 5 if duration < 7.5 else 10
        payload["duration"] = duration

        # Aspect ratio
        if request.aspect_ratio:
            payload["ratio"] = request.aspect_ratio

        # Reference image (first frame for I2V)
        if request.reference_images:
            ref_img = request.reference_images[0]
            if ref_img.startswith(("http://", "https://")):
                payload["image_url"] = ref_img
            else:
                # Convert to data URI
                mime_type = self.get_mime_type(ref_img)
                b64_data = self.encode_image_to_base64(ref_img)
                payload["image_url"] = f"data:{mime_type};base64,{b64_data}"

        # First frame override
        if request.first_frame:
            if request.first_frame.startswith(("http://", "https://")):
                payload["image_url"] = request.first_frame
            else:
                mime_type = self.get_mime_type(request.first_frame)
                b64_data = self.encode_image_to_base64(request.first_frame)
                payload["image_url"] = f"data:{mime_type};base64,{b64_data}"

        # Seed
        if request.seed is not None:
            payload["seed"] = request.seed

        return payload

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """Check the status of a generation job."""
        result = VideoGenerationResult(
            job_id=job_id,
            provider=self.provider_name,
        )

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/generations/{job_id}")

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                result.error_message = f"Status check failed: {response.status_code}"
                return result

            data = response.json()

            status = data.get("status", "").lower()
            if status == "completed" or status == "succeeded":
                result.status = GenerationStatus.COMPLETED
                result.video_url = data.get("output") or data.get("video_url")
                result.completed_at = datetime.now()
            elif status == "failed":
                result.status = GenerationStatus.FAILED
                result.error_message = data.get("error", "Generation failed")
            elif status in ("pending", "queued"):
                result.status = GenerationStatus.PENDING
            else:
                result.status = GenerationStatus.PROCESSING

            # Capture seed if available
            if "seed" in data:
                result.seed = data["seed"]

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
        """Download the generated video."""
        if not result.video_url:
            raise ValueError("No video URL available")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        client = await self._get_client()
        response = await client.get(result.video_url)

        if response.status_code != 200:
            raise Exception(f"Download failed: {response.status_code}")

        with open(output_path, "wb") as f:
            f.write(response.content)

        result.video_path = str(output_path)
        return str(output_path)
