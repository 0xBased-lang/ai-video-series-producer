"""
PiAPI Provider (Kling Specialist)
=================================

Third-party API for Kling video generation.
Supports Kling 2.0, 2.1, 2.5, and Elements features.

Features:
- Up to 4 reference images (Elements)
- Text-to-video and Image-to-video
- Competitive pricing
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from .base import (
    BaseVideoProvider,
    VideoGenerationResult,
    GenerationRequest,
    GenerationStatus,
)
from .factory import register_provider

logger = logging.getLogger(__name__)


@register_provider("piapi")
class PiAPIProvider(BaseVideoProvider):
    """
    PiAPI provider for Kling video generation.

    Offers unofficial but reliable access to Kling models
    with competitive pricing.
    """

    @property
    def provider_name(self) -> str:
        return "PiAPI"

    @property
    def supported_models(self) -> List[str]:
        return [
            "kling-v2-5-pro",
            "kling-v2-1-master",
            "kling-v2-0-pro",
            "kling-elements",
        ]

    @property
    def env_key_name(self) -> str:
        return "PIAPI_API_KEY"

    def _get_default_base_url(self) -> str:
        return "https://api.piapi.ai"

    @property
    def max_reference_images(self) -> int:
        return 4  # Kling Elements supports 4

    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """Generate video via PiAPI."""
        result = VideoGenerationResult(
            provider=self.provider_name,
            prompt=request.prompt,
            reference_images=request.reference_images,
            model=request.model or "kling-v2-5-pro",
        )

        try:
            payload = self._build_payload(request)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/kling/v1/video/generation",
                json=payload,
            )

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                result.error_message = f"API error: {response.status_code}"
                return result

            data = response.json()

            if data.get("code") == 0:
                result.job_id = data.get("data", {}).get("task_id")
                result.status = GenerationStatus.PROCESSING
                result = await self.wait_for_completion(result.job_id)
            else:
                result.status = GenerationStatus.FAILED
                result.error_message = data.get("message", "Unknown error")

            return result

        except Exception as e:
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            return result

    def _build_payload(self, request: GenerationRequest) -> Dict[str, Any]:
        """Build PiAPI request payload."""
        payload = {
            "model": request.model or "kling-v2-5-pro",
            "prompt": request.prompt,
            "duration": str(request.duration),
            "aspect_ratio": request.aspect_ratio or "16:9",
        }

        # Reference images for Elements
        if request.reference_images and "elements" in (request.model or "").lower():
            elements = []
            for img in request.reference_images[:4]:
                if img.startswith(("http://", "https://")):
                    elements.append({"image_url": img})
                else:
                    b64 = self.encode_image_to_base64(img)
                    mime = self.get_mime_type(img)
                    elements.append({"image_url": f"data:{mime};base64,{b64}"})
            payload["elements"] = elements

        # First frame for I2V
        elif request.first_frame or request.reference_images:
            img = request.first_frame or request.reference_images[0]
            if img.startswith(("http://", "https://")):
                payload["image_url"] = img
            else:
                b64 = self.encode_image_to_base64(img)
                mime = self.get_mime_type(img)
                payload["image_url"] = f"data:{mime};base64,{b64}"

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        return payload

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """Check generation status."""
        result = VideoGenerationResult(job_id=job_id, provider=self.provider_name)

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/kling/v1/video/generation/{job_id}"
            )

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                return result

            data = response.json()
            task_data = data.get("data", {})
            status = task_data.get("status", "").lower()

            if status == "completed":
                result.status = GenerationStatus.COMPLETED
                result.video_url = task_data.get("video_url")
                result.completed_at = datetime.now()
            elif status == "failed":
                result.status = GenerationStatus.FAILED
                result.error_message = task_data.get("error", "Failed")
            else:
                result.status = GenerationStatus.PROCESSING

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
        """Download video to local storage."""
        if not result.video_url:
            raise ValueError("No video URL")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        client = await self._get_client()
        response = await client.get(result.video_url)

        with open(output_path, "wb") as f:
            f.write(response.content)

        result.video_path = str(output_path)
        return str(output_path)
