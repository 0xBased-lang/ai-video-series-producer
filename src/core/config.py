"""
Configuration System
====================

Centralized, validated configuration management with typed dataclasses.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import yaml

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class VideoConfig:
    """Video output settings."""

    duration: int = 5
    resolution: str = "720p"
    aspect_ratio: str = "16:9"
    fps: int = 24
    format: str = "mp4"

    # Validation constraints
    VALID_RESOLUTIONS = {"480p", "720p", "1080p", "4k"}
    VALID_ASPECT_RATIOS = {"16:9", "9:16", "4:3", "1:1", "21:9"}
    VALID_FORMATS = {"mp4", "webm", "mov"}

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate configuration values."""
        if not 1 <= self.duration <= 60:
            raise ConfigurationError(
                f"Duration must be 1-60 seconds, got {self.duration}",
                config_key="video.duration",
            )
        if self.resolution not in self.VALID_RESOLUTIONS:
            raise ConfigurationError(
                f"Invalid resolution: {self.resolution}",
                config_key="video.resolution",
            )
        if self.aspect_ratio not in self.VALID_ASPECT_RATIOS:
            raise ConfigurationError(
                f"Invalid aspect ratio: {self.aspect_ratio}",
                config_key="video.aspect_ratio",
            )


@dataclass
class GenerationConfig:
    """Generation settings."""

    preferred_provider: str = "fal"
    preferred_model: str = "kling-2.5"
    fallback_provider: Optional[str] = "google"
    fallback_model: Optional[str] = "veo-3-fast"
    quality_preset: str = "balanced"
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 300

    # Provider-specific settings
    provider_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    VALID_PROVIDERS = {"fal", "google", "runway", "piapi", "replicate"}
    VALID_PRESETS = {"fast", "balanced", "quality", "cinematic"}

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate configuration values."""
        if self.preferred_provider not in self.VALID_PROVIDERS:
            raise ConfigurationError(
                f"Invalid provider: {self.preferred_provider}",
                config_key="generation.preferred_provider",
            )
        if self.quality_preset not in self.VALID_PRESETS:
            raise ConfigurationError(
                f"Invalid preset: {self.quality_preset}",
                config_key="generation.quality_preset",
            )
        if not 1 <= self.max_retries <= 10:
            raise ConfigurationError(
                f"max_retries must be 1-10, got {self.max_retries}",
                config_key="generation.max_retries",
            )


@dataclass
class ReferenceConfig:
    """Reference image settings."""

    max_images: int = 4
    preferred_format: str = "png"
    max_size_mb: int = 10
    auto_resize: bool = True
    auto_optimize: bool = True
    preserve_aspect_ratio: bool = True

    # Recommended dimensions
    character_dimensions: str = "1024x1024"
    scene_dimensions: str = "1920x1080"


@dataclass
class ConsistencyConfig:
    """Character/style consistency settings."""

    character_weight: float = 0.7
    style_weight: float = 0.5
    scene_weight: float = 0.3
    use_last_frame: bool = True
    overlap_frames: int = 1
    min_consistency_score: float = 0.7
    auto_retry_on_drift: bool = True

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate weight values."""
        for name, value in [
            ("character_weight", self.character_weight),
            ("style_weight", self.style_weight),
            ("scene_weight", self.scene_weight),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ConfigurationError(
                    f"{name} must be 0.0-1.0, got {value}",
                    config_key=f"consistency.{name}",
                )


@dataclass
class ChainingConfig:
    """Scene chaining settings."""

    enabled: bool = True
    method: str = "last_frame"
    extract_last_frame: bool = True
    frame_quality: int = 95
    transition_type: str = "seamless"
    transition_prompt_suffix: str = ", continuing from previous scene"

    VALID_METHODS = {"last_frame", "reference_lock", "style_anchor"}
    VALID_TRANSITIONS = {"seamless", "cut", "fade"}


@dataclass
class OutputConfig:
    """Output and storage settings."""

    base_path: str = "./output"
    organize_by: str = "series"
    naming_pattern: str = "{series}_{episode}_{scene}_{take}"
    save_metadata: bool = True
    metadata_format: str = "json"
    generate_thumbnails: bool = True
    thumbnail_size: str = "320x180"


@dataclass
class QualityConfig:
    """Quality review settings."""

    auto_review: bool = False
    review_provider: str = "claude"
    check_character_consistency: bool = True
    check_style_consistency: bool = True
    check_motion_quality: bool = True
    check_artifacts: bool = True
    min_quality_score: float = 0.7
    auto_reject_below: float = 0.5
    auto_approve_above: float = 0.9


@dataclass
class PerformanceConfig:
    """Performance and rate limiting settings."""

    max_concurrent_generations: int = 3
    max_concurrent_uploads: int = 5
    cache_enabled: bool = True
    cache_ttl: int = 3600
    requests_per_minute: int = 10


# =============================================================================
# Main Configuration Class
# =============================================================================


@dataclass
class Config:
    """
    Main configuration container with validation and loading.

    Provides a unified interface to all configuration settings with:
    - Type-safe access to configuration values
    - Validation on load and modification
    - Environment variable interpolation
    - Sensible defaults for all values
    """

    video: VideoConfig = field(default_factory=VideoConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    references: ReferenceConfig = field(default_factory=ReferenceConfig)
    consistency: ConsistencyConfig = field(default_factory=ConsistencyConfig)
    chaining: ChainingConfig = field(default_factory=ChainingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    # Raw config for provider-specific extensions
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def load(cls, path: Optional[Union[str, Path]] = None) -> "Config":
        """
        Load configuration from file with environment variable interpolation.

        Args:
            path: Path to YAML config file (defaults.yaml)

        Returns:
            Validated Config instance
        """
        # Default search paths
        search_paths = [
            Path("./config/defaults.yaml"),
            Path("./defaults.yaml"),
            Path.home() / ".video-producer" / "config.yaml",
        ]

        if path:
            search_paths.insert(0, Path(path))

        config_data = {}

        for search_path in search_paths:
            if search_path.exists():
                logger.info(f"Loading config from: {search_path}")
                try:
                    with open(search_path, "r") as f:
                        config_data = yaml.safe_load(f) or {}
                    break
                except yaml.YAMLError as e:
                    raise ConfigurationError(
                        f"Invalid YAML in config file: {e}",
                        config_key=str(search_path),
                    )
        else:
            logger.info("No config file found, using defaults")

        # Interpolate environment variables
        config_data = cls._interpolate_env_vars(config_data)

        return cls.from_dict(config_data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary with validation."""
        try:
            return cls(
                video=VideoConfig(**data.get("video", {})),
                generation=GenerationConfig(**data.get("generation", {})),
                references=ReferenceConfig(**data.get("references", {})),
                consistency=ConsistencyConfig(**data.get("consistency", {})),
                chaining=ChainingConfig(**data.get("chaining", {})),
                output=OutputConfig(**data.get("output", {})),
                quality=QualityConfig(**data.get("quality", {})),
                performance=PerformanceConfig(**data.get("performance", {})),
                _raw=data,
            )
        except TypeError as e:
            raise ConfigurationError(f"Invalid configuration: {e}")

    @staticmethod
    def _interpolate_env_vars(data: Any) -> Any:
        """Recursively interpolate ${VAR} patterns with environment variables."""
        if isinstance(data, str):
            # Handle ${VAR} and ${VAR:-default} patterns
            import re

            pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

            def replace(match):
                var_name = match.group(1)
                default = match.group(2) or ""
                return os.environ.get(var_name, default)

            return re.sub(pattern, replace, data)
        elif isinstance(data, dict):
            return {k: Config._interpolate_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Config._interpolate_env_vars(item) for item in data]
        return data

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        from dataclasses import asdict

        result = {}
        for section in ["video", "generation", "references", "consistency", "chaining", "output", "quality", "performance"]:
            result[section] = asdict(getattr(self, section))
        return result

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """Get generation preset by name."""
        presets = self._raw.get("generation", {}).get("presets", {})
        if preset_name not in presets:
            raise ConfigurationError(
                f"Preset not found: {preset_name}",
                config_key=f"generation.presets.{preset_name}",
            )
        return presets[preset_name]

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get provider-specific configuration."""
        return self.generation.provider_settings.get(provider, {})


# =============================================================================
# Convenience Functions
# =============================================================================


_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance (lazily loaded)."""
    global _global_config
    if _global_config is None:
        _global_config = Config.load()
    return _global_config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config


def reset_config() -> None:
    """Reset global configuration to None (forces reload on next access)."""
    global _global_config
    _global_config = None
