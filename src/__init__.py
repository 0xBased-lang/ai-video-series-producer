"""
AI Video Series Producer
========================

A comprehensive framework for creating AI-generated video series with
consistent characters, styles, and context management.

Features:
- Multi-provider API support (fal.ai, Google Veo, Runway, PiAPI, Replicate)
- Fluent series builder for clean project setup
- Character consistency through reference images and prompts
- Scene chaining with automatic frame continuity
- Quality presets and style templates
- n8n workflow integration

Quick Start:
    from src import create_series, CharacterBuilder

    # Create a series with the fluent builder
    series = (
        create_series("My Adventure")
        .description("An epic journey of discovery")
        .cinematic_style()
        .high_quality()
        .character(
            CharacterBuilder("hero")
            .name("Alex Chen")
            .age("30")
            .gender("female")
            .hair("auburn", "shoulder-length")
            .eyes("green")
            .outfit("leather jacket, dark jeans")
            .reference("front", "refs/alex.jpg")
            .build()
        )
        .location("city", "Downtown", "busy city street at night")
        .provider("fal")
        .output_path("./output")
        .build()
    )

Legacy Usage:
    from src import VideoProducer

    producer = VideoProducer()
    video = await producer.generate_scene(
        character_id="protagonist",
        action="walking through the city",
        location_id="street",
    )
"""

__version__ = "0.2.0"
__author__ = "AI Video Series Producer"

# =============================================================================
# New Clean API (Recommended)
# =============================================================================

# Series Builder - Primary interface for creating series
from .series.builder import (
    SeriesBuilder,
    create_series,
    load_series,
    quick_series,
)

# Character Builder - Fluent character creation
from .series.character import (
    Character,
    CharacterBuilder,
    CharacterStyle,
    CharacterType,
)

# Style System - Visual style and quality presets
from .series.style import (
    VisualStyle,
    QualityPreset,
    StylePresets,
    ColorPalette,
    LightingStyle,
    CameraStyle,
)

# Series Models - Data structures
from .series.series import (
    Series,
    Episode,
    Scene,
    SeriesStatus,
    EpisodeStatus,
    SceneStatus,
)

# Core Utilities
from .core.config import Config, get_config
from .core.exceptions import (
    VideoProducerError,
    ConfigurationError,
    ProviderError,
    GenerationError,
    ValidationError,
    SecurityError,
)
from .core.security import PathValidator, sanitize_filename

# =============================================================================
# Legacy API (Still Supported)
# =============================================================================

from .api import get_provider, list_providers
from .context import CharacterBible, SceneTracker
from .workflow import VideoProducer, SceneChainer

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__version__",

    # New API - Series Builder
    "SeriesBuilder",
    "create_series",
    "load_series",
    "quick_series",

    # New API - Characters
    "Character",
    "CharacterBuilder",
    "CharacterStyle",
    "CharacterType",

    # New API - Style
    "VisualStyle",
    "QualityPreset",
    "StylePresets",
    "ColorPalette",
    "LightingStyle",
    "CameraStyle",

    # New API - Series Models
    "Series",
    "Episode",
    "Scene",
    "SeriesStatus",
    "EpisodeStatus",
    "SceneStatus",

    # Core
    "Config",
    "get_config",
    "PathValidator",
    "sanitize_filename",

    # Exceptions
    "VideoProducerError",
    "ConfigurationError",
    "ProviderError",
    "GenerationError",
    "ValidationError",
    "SecurityError",

    # Legacy API
    "VideoProducer",
    "CharacterBible",
    "SceneTracker",
    "SceneChainer",
    "get_provider",
    "list_providers",
]
