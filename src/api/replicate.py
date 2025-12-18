"""
Replicate Provider
==================

Open source video models with LoRA training support.

Features:
- HunyuanVideo with LoRA
- Wan 2.1 with LoRA
- Custom model training
- Pay-per-use pricing
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


@register_provider("replicate")
class ReplicateProvider(BaseVideoProvider):
    """
    Replicate provider for open source video models.

    Supports LoRA training for custom character consistency.
    """

    @property
    def provider_name(self) -> str:
        return "Replicate"

    @property
    def supported_models(self) -> List[str]:
        return [
            "zsxkib/hunyuan-video-lora",
            "fofr/wan2.1-with-lora",
            "google/veo-3.1",
            "luma/ray",
        ]

    @property
    def env_key_name(self) -> str:
        return "REPLICATE_API_TOKEN"

    def _get_default_base_url(self) -> str:
        return "https://api.replicate.com/v1"

    @property
    def supports_lora(self) -> bool:
        return True

    async def generate_video(
        self,
        request: GenerationRequest,
    ) -> VideoGenerationResult:
        """Generate video via Replicate."""
        result = VideoGenerationResult(
            provider=self.provider_name,
            prompt=request.prompt,
            model=request.model or "zsxkib/hunyuan-video-lora",
        )

        try:
            model_id = request.model or "zsxkib/hunyuan-video-lora"
            payload = self._build_payload(request)

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/predictions",
                json={
                    "version": self._get_model_version(model_id),
                    "input": payload,
                },
            )

            if response.status_code not in (200, 201):
                result.status = GenerationStatus.FAILED
                result.error_message = f"API error: {response.status_code}"
                return result

            data = response.json()
            result.job_id = data.get("id")
            result.status = GenerationStatus.PROCESSING

            # Poll for completion
            result = await self.wait_for_completion(result.job_id)
            return result

        except Exception as e:
            result.status = GenerationStatus.FAILED
            result.error_message = str(e)
            return result

    def _get_model_version(self, model_id: str) -> str:
        """Get the latest version hash for a model."""
        # In production, you'd fetch this from the API
        # For now, return placeholder
        versions = {
            "zsxkib/hunyuan-video-lora": "latest",
            "fofr/wan2.1-with-lora": "latest",
        }
        return versions.get(model_id, "latest")

    def _build_payload(self, request: GenerationRequest) -> Dict[str, Any]:
        """Build Replicate input payload."""
        payload = {
            "prompt": request.prompt,
        }

        # LoRA weights (custom character training)
        if request.extra_params.get("lora_url"):
            payload["lora_url"] = request.extra_params["lora_url"]
            payload["lora_scale"] = request.extra_params.get("lora_scale", 0.8)

        # Trigger word for LoRA
        if request.extra_params.get("trigger_word"):
            payload["prompt"] = f"{request.extra_params['trigger_word']} {request.prompt}"

        # Reference image
        if request.reference_images:
            img = request.reference_images[0]
            if img.startswith(("http://", "https://")):
                payload["image"] = img
            else:
                b64 = self.encode_image_to_base64(img)
                mime = self.get_mime_type(img)
                payload["image"] = f"data:{mime};base64,{b64}"

        # Duration/frames
        if request.duration:
            payload["num_frames"] = request.duration * 24  # Assuming 24fps

        if request.seed is not None:
            payload["seed"] = request.seed

        return payload

    async def check_status(self, job_id: str) -> VideoGenerationResult:
        """Check prediction status."""
        result = VideoGenerationResult(job_id=job_id, provider=self.provider_name)

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/predictions/{job_id}")

            if response.status_code != 200:
                result.status = GenerationStatus.FAILED
                return result

            data = response.json()
            status = data.get("status", "").lower()

            if status == "succeeded":
                result.status = GenerationStatus.COMPLETED
                output = data.get("output")
                if isinstance(output, list):
                    result.video_url = output[0]
                else:
                    result.video_url = output
                result.completed_at = datetime.now()
            elif status == "failed":
                result.status = GenerationStatus.FAILED
                result.error_message = data.get("error", "Failed")
            elif status == "canceled":
                result.status = GenerationStatus.CANCELLED
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
        """Download video."""
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

    # -------------------------------------------------------------------------
    # LoRA Training
    # -------------------------------------------------------------------------

    async def train_lora(
        self,
        training_images: List[str],
        trigger_word: str,
        model_name: str,
        steps: int = 1000,
    ) -> Dict[str, Any]:
        """
        Train a custom LoRA for character consistency.

        Args:
            training_images: List of image paths (15-30 recommended)
            trigger_word: Word to trigger the trained character
            model_name: Name for the trained model
            steps: Training steps

        Returns:
            Training job info including LoRA URL when complete
        """
        # In production, this would:
        # 1. Upload images to Replicate
        # 2. Start training job
        # 3. Return job info for polling

        logger.info(
            f"LoRA training would start with {len(training_images)} images, "
            f"trigger word: '{trigger_word}', steps: {steps}"
        )

        return {
            "status": "placeholder",
            "message": "Implement with Replicate training API",
            "docs": "https://replicate.com/zsxkib/hunyuan-video-lora/train",
        }
