"""
AI Video Series Producer
========================

A comprehensive framework for creating AI-generated video series with
consistent characters, styles, and context management.

Features:
- Multi-provider API support (Veo, Kling, Runway, Hailuo, Luma, Sora)
- Character bible management for consistency
- Scene chaining and frame continuity
- n8n workflow integration
- Context preservation across episodes

Usage:
    from ai_video_producer import VideoProducer

    producer = VideoProducer()
    producer.load_character_bible("context/character_bible.yaml")

    video = producer.generate_scene(
        character="protagonist",
        action="walking through the city",
        location="street",
        duration=5
    )
"""

__version__ = "0.1.0"
__author__ = "AI Video Series Producer"

from .api import get_provider, list_providers
from .context import CharacterBible, SceneTracker
from .workflow import VideoProducer, SceneChainer

__all__ = [
    "VideoProducer",
    "CharacterBible",
    "SceneTracker",
    "SceneChainer",
    "get_provider",
    "list_providers",
]
