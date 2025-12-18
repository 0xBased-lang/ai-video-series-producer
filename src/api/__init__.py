"""
API Integration Layer
=====================

Provides unified access to multiple video generation APIs.

Supported Providers:
- fal.ai (unified API for Kling, Veo, Hailuo, Wan)
- Google Veo (direct API)
- Runway Gen-4
- PiAPI (Kling specialist)
- MiniMax Hailuo
- Luma AI
- Replicate (open source + LoRA)
- AIMLAPI (unified)
- OpenAI Sora

Usage:
    from src.api import get_provider

    provider = get_provider("fal")
    result = await provider.generate_video(
        prompt="A person walking",
        reference_images=["path/to/ref.jpg"],
        duration=5
    )
"""

from .base import BaseVideoProvider, VideoGenerationResult
from .factory import get_provider, list_providers, get_best_provider

__all__ = [
    "BaseVideoProvider",
    "VideoGenerationResult",
    "get_provider",
    "list_providers",
    "get_best_provider",
]
