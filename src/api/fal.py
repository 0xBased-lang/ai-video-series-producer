"""
fal.ai Provider
===============

Unified API provider supporting multiple video models:
- Kling 2.5/2.6
- Google Veo 3/3.1
- MiniMax Hailuo
- Wan 2.1/2.2
- And 600+ more models

This is the recommended provider for most use cases.
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


@register_provider("fal")
class FalProvider(BaseVideoProvider):
    """
    fal.ai unified video generation provider.

    Supports multiple models through a single API:
    - kling-2.5, kling-2.6 (best value + consistency)
    - veo-3, veo-3-fast (best reference control)
    - hailuo-02 (strong subject lock)
    - wan-2.1 (open source + LoRA)
    """

    # Model endpoint mappings
    MODEL_ENDPOINTS = {
        # Kling models
        "kling-2.5": "fal-ai/kling-video/v2.5/standard/text-to-video",
        "kling-2.5-i2v": "fal-ai/kling-video/v2.5/standard/image-to-video",
        "kling-2.6": "fal-ai/kling-video/v2.6/pro/text-to-video",
        "kling-2.6-i2v": "fal-ai/kling-video/v2.6/pro/image-to-video",
        "kling-elements": "fal-ai/kling-video/v2/master/elements-to-video",

        # Google Veo
        "veo-3": "fal-ai/veo3",
        "veo-3-fast": "fal-ai/veo3/fast",
        "veo-3-i2v": "fal-ai/veo3/image-to-video",

        # MiniMax Hailuo
        "hailuo-02": "fal-ai/minimax/hailuo-02/standard/text-to-video",
        "hailuo-02-i2v": "fal-ai/minimax/hailuo-02/standard/image-to-video",
        "hailuo-s2v": "fal-ai/minimax/hailuo-s2v-01/subject-to-video",

        # Wan (open source)
        "wan-2.1": "fal-ai/wan-t2v",
        "wan-2.1-i2v": "fal-ai/wan-i2v",
        "wan-2.2": "fal-ai/wan2.2/text-to-video",

        # Luma
        "luma-ray": "fal-ai/luma-dream-machine",
    }

    # Model capabilities
    MODEL_CAPABILITIES = {
        "kling-2.5": {"max_refs": 4, "max_duration": 10, "audio": False},
        "kling-2.6": {"max_refs": 4, "max_duration": 10, "audio": True},
        "kling-elements": {"max_refs": 4, "max_duration": 10, "elements": True},
        "veo-3": {"max_refs": 3, "max_duration": 8, "audio": True},
        "veo-3-fast": {"max_refs": 3, "max_duration": 8, "audio": False},
        "hailuo-02": {"max_refs": 1, "max_duration": 6, "subject_lock": True},
        "hailuo-s2v": {"max_refs": 1, "max_duration": 6, "subject_lock": True},
        "wan-2.1": {"max_refs": 1, "max_duration": 5, "lora": True},
    }

    @property
    def provider_name(self) -> str:
        return "fal.ai"

    @property
    def supported_models(self) -> List[str]:
        return list(self.MODEL_ENDPOINTS.keys())

    @property
    def env_key_name(self) -> str:
        return "FAL_API_KEY"

    def _get_default_base_url(self) -> str:
        return "https://fal.run"

    @property
    def max_reference_images(self) -> int:
        return 4  # Kling supports up to 4

    @property
    def supports_audio(self) -> bool:
        return True  # Veo 3 and Kling 2.6 support audio

    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """
        Generate a video using fal.ai.

        Args:
            request: Generation request parameters

        Returns:
            VideoGenerationResult with the generated video
        """
        result = VideoGenerationResult(
            provider=self.provider_name,
            prompt=request.prompt,
            reference_images=request.reference_images,
        )

        try:
            # Determine model and endpoint
            model = request.model or "kling-2.5"
            endpoint = self._get_endpoint(model, request)
            result.model = model

            # Build request payload
            payload = self._build_payload(model, request)

            logger.info(f"Generating video with {model} via fal.ai")
            logger.debug(f"Endpoint: {endpoint}")
            logger.debug(f"Payload: {payload}")

            # Make API request
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/{endpoint}",
                json=payload,
            )

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                result.error_message = f"API error: {response.status_code} - {response.text}"
                return result

            data = response.json()

            # Handle async vs sync response
            if "request_id" in data:
                # Async - need to poll for result
                result.job_id = data["request_id"]
                result.status = GenerationStatus.PROCESSING
                result = await self.wait_for_completion(result.job_id)
            else:
                # Sync - result is immediate
                result = self._parse_response(data, result)

            return result

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            return result

    def _get_endpoint(self, model: str, request: GenerationRequest) -> str:
        """Get the appropriate endpoint based on model and request type."""
        base_model = model.replace("-i2v", "")

        # If we have a first frame or reference images, use I2V variant
        if request.first_frame or request.reference_images:
            i2v_model = f"{base_model}-i2v"
            if i2v_model in self.MODEL_ENDPOINTS:
                return self.MODEL_ENDPOINTS[i2v_model]

        # Use base model
        if model in self.MODEL_ENDPOINTS:
            return self.MODEL_ENDPOINTS[model]

        # Fallback
        return self.MODEL_ENDPOINTS.get(base_model, self.MODEL_ENDPOINTS["kling-2.5"])

    def _build_payload(
        self,
        model: str,
        request: GenerationRequest,
    ) -> Dict[str, Any]:
        """Build the API request payload."""
        payload = {
            "prompt": request.prompt,
        }

        # Duration
        if request.duration:
            if "kling" in model:
                payload["duration"] = str(request.duration)
            elif "veo" in model:
                payload["duration"] = request.duration
            else:
                payload["duration"] = request.duration

        # Aspect ratio
        if request.aspect_ratio:
            payload["aspect_ratio"] = request.aspect_ratio

        # Negative prompt
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        # Seed for reproducibility
        if request.seed is not None:
            payload["seed"] = request.seed

        # Reference images
        if request.reference_images:
            refs = self.prepare_reference_images(request.reference_images)
            if "kling" in model and "elements" in model:
                # Kling Elements format
                payload["elements"] = [
                    {"image_url": ref.get("url") or ref.get("data")}
                    for ref in refs
                ]
            elif "hailuo" in model and "s2v" in model:
                # Hailuo Subject-to-Video
                payload["subject_image_url"] = refs[0].get("url") or refs[0].get("data")
            elif "veo" in model:
                # Veo reference format
                payload["reference_images"] = [
                    {"image_url": ref.get("url") or ref.get("data")}
                    for ref in refs
                ]
            else:
                # Generic image-to-video
                payload["image_url"] = refs[0].get("url") or refs[0].get("data")

        # First frame (for I2V)
        if request.first_frame:
            ref = self.prepare_reference_images([request.first_frame])[0]
            payload["image_url"] = ref.get("url") or ref.get("data")

        # Audio (for supported models)
        if request.with_audio and model in ["veo-3", "kling-2.6"]:
            payload["enable_audio"] = True

        # Extra params
        if request.extra_params:
            payload.update(request.extra_params)

        return payload

    def _parse_response(
        self,
        data: Dict[str, Any],
        result: VideoGenerationResult,
    ) -> VideoGenerationResult:
        """Parse the API response into a VideoGenerationResult."""
        # Get video URL
        if "video" in data:
            video_data = data["video"]
            if isinstance(video_data, dict):
                result.video_url = video_data.get("url")
            else:
                result.video_url = video_data
        elif "video_url" in data:
            result.video_url = data["video_url"]
        elif "output" in data:
            result.video_url = data["output"]

        # Status
        if result.video_url:
            result.status = GenerationStatus.COMPLETED
            result.completed_at = datetime.now()
        else:
            result.status = GenerationStatus.FAILED
            result.error_message = "No video URL in response"

        # Seed (if returned)
        if "seed" in data:
            result.seed = data["seed"]

        # Store raw response for debugging
        result.generation_params["raw_response"] = data

        return result

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """Check the status of an async generation job."""
        result = VideoGenerationResult(job_id=job_id, provider=self.provider_name)

        try:
            client = await self._get_client()
            response = await client.get(
                f"https://queue.fal.run/fal-ai/requests/{job_id}/status"
            )

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                result.error_message = f"Status check failed: {response.status_code}"
                return result

            data = response.json()
            status = data.get("status", "").lower()

            if status == "completed":
                # Fetch the actual result
                result_response = await client.get(
                    f"https://queue.fal.run/fal-ai/requests/{job_id}"
                )
                if result_response.status_code == 200:
                    result = self._parse_response(result_response.json(), result)
            elif status in ("failed", "error"):
                result.status = GenerationStatus.FAILED
                result.error_message = data.get("error", "Unknown error")
            elif status in ("pending", "in_queue"):
                result.status = GenerationStatus.PENDING
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
        """Download the generated video to local storage."""
        if not result.video_url:
            raise ValueError("No video URL available to download")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        client = await self._get_client()
        response = await client.get(result.video_url)

        if response.status_code != 200:
            raise Exception(f"Download failed: {response.status_code}")

        with open(output_path, "wb") as f:
            f.write(response.content)

        result.video_path = str(output_path)
        logger.info(f"Video downloaded to: {output_path}")

        return str(output_path)

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    async def generate_with_kling(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        duration: int = 5,
        model: str = "kling-2.5",
        **kwargs,
    ) -> VideoGenerationResult:
        """Convenience method for Kling generation."""
        request = GenerationRequest(
            prompt=prompt,
            reference_images=reference_images or [],
            duration=duration,
            model=model,
            **kwargs,
        )
        return await self.generate_video(request)

    async def generate_with_veo(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        duration: int = 8,
        with_audio: bool = True,
        fast: bool = False,
        **kwargs,
    ) -> VideoGenerationResult:
        """Convenience method for Veo generation."""
        model = "veo-3-fast" if fast else "veo-3"
        request = GenerationRequest(
            prompt=prompt,
            reference_images=reference_images or [],
            duration=duration,
            model=model,
            with_audio=with_audio,
            **kwargs,
        )
        return await self.generate_video(request)

    async def generate_with_hailuo(
        self,
        prompt: str,
        subject_image: Optional[str] = None,
        duration: int = 6,
        **kwargs,
    ) -> VideoGenerationResult:
        """Convenience method for Hailuo S2V (subject lock) generation."""
        model = "hailuo-s2v" if subject_image else "hailuo-02"
        request = GenerationRequest(
            prompt=prompt,
            reference_images=[subject_image] if subject_image else [],
            duration=duration,
            model=model,
            **kwargs,
        )
        return await self.generate_video(request)
