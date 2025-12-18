"""
Google Veo Provider
===================

Direct integration with Google's Veo video generation API
via Gemini API or Vertex AI.

Features:
- Up to 3 reference images for consistency
- Scene extension for longer videos
- Native audio generation (Veo 3.1)
- First/last frame control
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


@register_provider("google")
class GoogleVeoProvider(BaseVideoProvider):
    """
    Google Veo video generation provider.

    Uses the Gemini API for video generation with Veo models.
    Supports reference images, scene extension, and audio.
    """

    @property
    def provider_name(self) -> str:
        return "Google Veo"

    @property
    def supported_models(self) -> List[str]:
        return ["veo-3.1", "veo-3.1-fast", "veo-2"]

    @property
    def env_key_name(self) -> str:
        return "GOOGLE_API_KEY"

    def _get_default_base_url(self) -> str:
        return "https://generativelanguage.googleapis.com/v1beta"

    @property
    def max_reference_images(self) -> int:
        return 3

    @property
    def supports_audio(self) -> bool:
        return True

    @property
    def supports_scene_extension(self) -> bool:
        return True

    @property
    def max_duration(self) -> int:
        return 8  # Base duration, extendable via scene extension

    def _get_headers(self) -> Dict[str, str]:
        """Google API uses API key as query param, not header."""
        return {
            "Content-Type": "application/json",
        }

    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """
        Generate a video using Google Veo.

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
            model = request.model or "veo-3.1-generate-preview"
            result.model = model

            # Build endpoint URL with API key
            endpoint = f"{self.base_url}/models/{model}:generateVideo"
            if self.api_key:
                endpoint += f"?key={self.api_key}"

            # Build request payload
            payload = self._build_payload(request)

            logger.info(f"Generating video with Google Veo: {model}")
            logger.debug(f"Payload: {payload}")

            # Make API request
            client = await self._get_client()
            response = await client.post(endpoint, json=payload)

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                result.error_message = f"API error: {response.status_code} - {response.text}"
                return result

            data = response.json()

            # Veo returns an operation ID for async processing
            if "name" in data:
                result.job_id = data["name"]
                result.status = GenerationStatus.PROCESSING

                # Poll for completion
                result = await self._poll_operation(result.job_id, result)
            else:
                result.status = GenerationStatus.FAILED
                result.error_message = "No operation ID in response"

            return result

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            return result

    def _build_payload(self, request: GenerationRequest) -> Dict[str, Any]:
        """Build the Veo API request payload."""
        payload = {
            "instances": [{
                "prompt": request.prompt,
            }],
            "parameters": {
                "aspectRatio": request.aspect_ratio or "16:9",
                "personGeneration": "allow_all",  # Allow person generation
            }
        }

        # Duration (Veo uses "sampleCount" or similar)
        # Note: Veo 3.1 generates 8s videos by default

        # Reference images (up to 3)
        if request.reference_images:
            references = []
            for img_path in request.reference_images[:3]:
                if img_path.startswith(("http://", "https://")):
                    references.append({"uri": img_path})
                else:
                    # Encode local file
                    mime_type = self.get_mime_type(img_path)
                    b64_data = self.encode_image_to_base64(img_path)
                    references.append({
                        "bytesBase64Encoded": b64_data,
                        "mimeType": mime_type,
                    })

            payload["instances"][0]["referenceImages"] = references

        # First frame (image-to-video)
        if request.first_frame:
            if request.first_frame.startswith(("http://", "https://")):
                payload["instances"][0]["image"] = {"uri": request.first_frame}
            else:
                mime_type = self.get_mime_type(request.first_frame)
                b64_data = self.encode_image_to_base64(request.first_frame)
                payload["instances"][0]["image"] = {
                    "bytesBase64Encoded": b64_data,
                    "mimeType": mime_type,
                }

        # Audio generation
        if request.with_audio:
            payload["parameters"]["generateAudio"] = True

        # Seed
        if request.seed is not None:
            payload["parameters"]["seed"] = request.seed

        # Negative prompt
        if request.negative_prompt:
            payload["instances"][0]["negativePrompt"] = request.negative_prompt

        return payload

    async def _poll_operation(
        self,
        operation_name: str,
        result: VideoGenerationResult,
        max_attempts: int = 60,
        poll_interval: float = 5.0,
    ) -> VideoGenerationResult:
        """Poll for operation completion."""
        client = await self._get_client()

        for attempt in range(max_attempts):
            try:
                endpoint = f"{self.base_url}/{operation_name}"
                if self.api_key:
                    endpoint += f"?key={self.api_key}"

                response = await client.get(endpoint)

                if response.status_code != 200:
                    logger.warning(f"Poll failed: {response.status_code}")
                    await asyncio.sleep(poll_interval)
                    continue

                data = response.json()

                if data.get("done"):
                    # Operation complete
                    if "error" in data:
                        result.status = GenerationStatus.FAILED
                        result.error_message = data["error"].get("message", "Unknown error")
                    elif "response" in data:
                        result = self._parse_response(data["response"], result)
                    return result

                logger.debug(f"Operation in progress, attempt {attempt + 1}")
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Poll error: {e}")
                await asyncio.sleep(poll_interval)

        result.status = GenerationStatus.FAILED
        result.error_message = "Timeout waiting for generation"
        return result

    def _parse_response(
        self,
        data: Dict[str, Any],
        result: VideoGenerationResult,
    ) -> VideoGenerationResult:
        """Parse the Veo response."""
        # Get video from response
        if "generatedVideos" in data:
            videos = data["generatedVideos"]
            if videos:
                video = videos[0]
                if "video" in video:
                    video_data = video["video"]
                    if "uri" in video_data:
                        result.video_url = video_data["uri"]
                    elif "bytesBase64Encoded" in video_data:
                        # Video returned as base64 - need to save
                        result.generation_params["video_base64"] = video_data["bytesBase64Encoded"]

        if result.video_url or "video_base64" in result.generation_params:
            result.status = GenerationStatus.COMPLETED
            result.completed_at = datetime.now()
        else:
            result.status = GenerationStatus.FAILED
            result.error_message = "No video in response"

        return result

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """Check the status of a generation job."""
        result = VideoGenerationResult(job_id=job_id, provider=self.provider_name)
        return await self._poll_operation(job_id, result, max_attempts=1)

    async def download_video(
        self,
        result: VideoGenerationResult,
        output_path: Union[str, Path],
    ) -> str:
        """Download the generated video."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if result.video_url:
            # Download from URL
            client = await self._get_client()
            response = await client.get(result.video_url)

            if response.status_code != 200:
                raise Exception(f"Download failed: {response.status_code}")

            with open(output_path, "wb") as f:
                f.write(response.content)

        elif "video_base64" in result.generation_params:
            # Decode base64
            import base64
            video_data = base64.b64decode(result.generation_params["video_base64"])
            with open(output_path, "wb") as f:
                f.write(video_data)
        else:
            raise ValueError("No video available to download")

        result.video_path = str(output_path)
        return str(output_path)

    # -------------------------------------------------------------------------
    # Scene Extension
    # -------------------------------------------------------------------------

    async def extend_video(
        self,
        previous_video: Union[str, VideoGenerationResult],
        prompt: str,
        duration: int = 8,
    ) -> VideoGenerationResult:
        """
        Extend a video by generating a continuation.

        Uses the last second of the previous video to ensure continuity.

        Args:
            previous_video: Path to previous video or VideoGenerationResult
            prompt: Prompt for the extension
            duration: Duration of the new segment

        Returns:
            VideoGenerationResult for the extended segment
        """
        # Extract last frame from previous video
        if isinstance(previous_video, VideoGenerationResult):
            video_path = previous_video.video_path or previous_video.video_url
        else:
            video_path = previous_video

        # Note: In production, you'd extract the last frame here
        # For now, we'll use the prompt with continuation context

        continuation_prompt = f"Seamless continuation: {prompt}"

        request = GenerationRequest(
            prompt=continuation_prompt,
            duration=duration,
            # If we had the last frame, we'd set it here:
            # first_frame=last_frame_path,
        )

        return await self.generate_video(request)
