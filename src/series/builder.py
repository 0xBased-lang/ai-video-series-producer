"""
Series Builder
==============

Fluent builder pattern for clean series establishment.

This provides a simple, readable interface for setting up a video series
with all its characters, style settings, and production configuration.
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from .series import Series, Episode, Scene, SeriesStatus
from .character import Character, CharacterBuilder, CharacterType
from .style import VisualStyle, QualityPreset, StylePresets

logger = logging.getLogger(__name__)


class SeriesBuilder:
    """
    Fluent builder for creating video series with clean, readable syntax.

    Example:
        series = (
            SeriesBuilder("My Series")
            .description("An epic adventure story")
            .genre("action")

            # Visual style
            .style(StylePresets.cinematic())
            .quality(QualityPreset.HIGH)

            # Characters
            .character(
                CharacterBuilder("hero")
                .name("Alex")
                .age("30")
                .gender("female")
                .hair("auburn", "shoulder-length")
                .eyes("green")
                .outfit("leather jacket, dark jeans")
                .reference("front", "refs/alex.jpg")
                .build()
            )
            .character(
                CharacterBuilder("mentor")
                .name("Marcus")
                .age("55")
                .gender("male")
                .hair("gray", "short")
                .build()
            )

            # Production settings
            .provider("fal")
            .model("kling-2.5")
            .output_path("./output/my_series")

            # Build the series
            .build()
        )
    """

    def __init__(self, name: str):
        """
        Initialize the series builder.

        Args:
            name: Name of the series
        """
        self._name = name
        self._description = ""
        self._genre = ""

        # Characters
        self._characters: Dict[str, Character] = {}

        # Locations
        self._locations: Dict[str, Dict[str, Any]] = {}

        # Style
        self._style: Optional[VisualStyle] = None
        self._quality_preset: QualityPreset = QualityPreset.BALANCED

        # Production settings
        self._provider = "fal"
        self._model = "kling-2.5"
        self._duration = 5
        self._aspect_ratio = "16:9"
        self._output_path = "./output"

        # Episodes (pre-planned)
        self._episodes: List[Episode] = []

    # -------------------------------------------------------------------------
    # Basic Metadata
    # -------------------------------------------------------------------------

    def description(self, description: str) -> "SeriesBuilder":
        """Set series description."""
        self._description = description
        return self

    def genre(self, genre: str) -> "SeriesBuilder":
        """Set series genre."""
        self._genre = genre
        return self

    # -------------------------------------------------------------------------
    # Characters
    # -------------------------------------------------------------------------

    def character(self, character: Character) -> "SeriesBuilder":
        """Add a character to the series."""
        self._characters[character.character_id] = character
        return self

    def protagonist(
        self,
        character_id: str,
        name: str,
        **kwargs,
    ) -> "SeriesBuilder":
        """
        Add a protagonist character with minimal configuration.

        Args:
            character_id: Unique identifier for the character
            name: Character name
            **kwargs: Additional character attributes
        """
        char = Character(
            character_id=character_id,
            name=name,
            character_type=CharacterType.PROTAGONIST,
            **kwargs,
        )
        self._characters[character_id] = char
        return self

    def supporting_character(
        self,
        character_id: str,
        name: str,
        **kwargs,
    ) -> "SeriesBuilder":
        """Add a supporting character."""
        char = Character(
            character_id=character_id,
            name=name,
            character_type=CharacterType.SUPPORTING,
            **kwargs,
        )
        self._characters[character_id] = char
        return self

    # -------------------------------------------------------------------------
    # Locations
    # -------------------------------------------------------------------------

    def location(
        self,
        location_id: str,
        name: str,
        description: str = "",
        reference_image: Optional[str] = None,
        **kwargs,
    ) -> "SeriesBuilder":
        """
        Add a location to the series.

        Args:
            location_id: Unique identifier
            name: Location name
            description: Prompt-friendly description
            reference_image: Reference image path
        """
        self._locations[location_id] = {
            "name": name,
            "description": description,
            "reference_image": reference_image,
            **kwargs,
        }
        return self

    # -------------------------------------------------------------------------
    # Visual Style
    # -------------------------------------------------------------------------

    def style(self, style: VisualStyle) -> "SeriesBuilder":
        """Set the visual style."""
        self._style = style
        return self

    def cinematic_style(self) -> "SeriesBuilder":
        """Use cinematic style preset."""
        self._style = StylePresets.cinematic()
        return self

    def anime_style(self) -> "SeriesBuilder":
        """Use anime style preset."""
        self._style = StylePresets.anime()
        return self

    def documentary_style(self) -> "SeriesBuilder":
        """Use documentary style preset."""
        self._style = StylePresets.documentary()
        return self

    def noir_style(self) -> "SeriesBuilder":
        """Use noir style preset."""
        self._style = StylePresets.noir()
        return self

    def scifi_style(self) -> "SeriesBuilder":
        """Use sci-fi style preset."""
        self._style = StylePresets.scifi()
        return self

    def quality(self, preset: QualityPreset) -> "SeriesBuilder":
        """Set quality preset."""
        self._quality_preset = preset
        return self

    def draft_quality(self) -> "SeriesBuilder":
        """Use draft quality for fast iteration."""
        self._quality_preset = QualityPreset.DRAFT
        return self

    def high_quality(self) -> "SeriesBuilder":
        """Use high quality preset."""
        self._quality_preset = QualityPreset.HIGH
        return self

    def cinematic_quality(self) -> "SeriesBuilder":
        """Use cinematic quality preset."""
        self._quality_preset = QualityPreset.CINEMATIC
        return self

    # -------------------------------------------------------------------------
    # Production Settings
    # -------------------------------------------------------------------------

    def provider(self, provider: str) -> "SeriesBuilder":
        """Set the video generation provider."""
        self._provider = provider
        return self

    def model(self, model: str) -> "SeriesBuilder":
        """Set the video generation model."""
        self._model = model
        return self

    def duration(self, seconds: int) -> "SeriesBuilder":
        """Set default scene duration."""
        self._duration = seconds
        return self

    def aspect_ratio(self, ratio: str) -> "SeriesBuilder":
        """Set default aspect ratio."""
        self._aspect_ratio = ratio
        return self

    def widescreen(self) -> "SeriesBuilder":
        """Use 16:9 widescreen."""
        self._aspect_ratio = "16:9"
        return self

    def vertical(self) -> "SeriesBuilder":
        """Use 9:16 vertical (social media)."""
        self._aspect_ratio = "9:16"
        return self

    def square(self) -> "SeriesBuilder":
        """Use 1:1 square."""
        self._aspect_ratio = "1:1"
        return self

    def output_path(self, path: Union[str, Path]) -> "SeriesBuilder":
        """Set output directory."""
        self._output_path = str(path)
        return self

    # -------------------------------------------------------------------------
    # Episodes
    # -------------------------------------------------------------------------

    def episode(
        self,
        title: str = "",
        description: str = "",
        scenes: Optional[List[Dict[str, Any]]] = None,
    ) -> "SeriesBuilder":
        """
        Add a pre-planned episode.

        Args:
            title: Episode title
            description: Episode description
            scenes: List of scene definitions
        """
        episode = Episode(
            episode_number=len(self._episodes) + 1,
            title=title,
            description=description,
        )

        if scenes:
            for i, scene_def in enumerate(scenes):
                scene = Scene(
                    scene_number=i + 1,
                    action=scene_def.get("action", ""),
                    character_ids=scene_def.get("character_ids", [scene_def.get("character_id")]) if scene_def.get("character_id") or scene_def.get("character_ids") else [],
                    location_id=scene_def.get("location_id"),
                    duration=scene_def.get("duration", self._duration),
                    camera_direction=scene_def.get("camera"),
                    dialogue=scene_def.get("dialogue"),
                )
                episode.scenes.append(scene)

        self._episodes.append(episode)
        return self

    # -------------------------------------------------------------------------
    # Build & Export
    # -------------------------------------------------------------------------

    def build(self) -> Series:
        """Build the series."""
        # Apply quality preset settings
        quality_settings = self._quality_preset.get_settings()

        series = Series(
            name=self._name,
            description=self._description,
            genre=self._genre,
            character_ids=list(self._characters.keys()),
            default_provider=self._provider,
            default_model=quality_settings.get("model", self._model),
            default_duration=self._duration,
            default_aspect_ratio=self._aspect_ratio,
            quality_preset=self._quality_preset.value,
            output_path=self._output_path,
            episodes=self._episodes,
        )

        # Store full character data for export
        series._characters = self._characters
        series._locations = self._locations
        series._style = self._style or StylePresets.cinematic()

        return series

    def save(self, path: Union[str, Path]) -> "SeriesBuilder":
        """
        Save the series configuration to a file.

        Args:
            path: Path to save (YAML or JSON based on extension)
        """
        series = self.build()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self._to_export_format(series)

        if path.suffix in (".yaml", ".yml"):
            with open(path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        logger.info(f"Series configuration saved to: {path}")
        return self

    def _to_export_format(self, series: Series) -> Dict[str, Any]:
        """Convert to export format."""
        return {
            "series": {
                "name": series.name,
                "description": series.description,
                "genre": series.genre,
            },
            "characters": {
                cid: char.to_dict()
                for cid, char in self._characters.items()
            },
            "locations": self._locations,
            "visual_style": self._style.to_dict() if self._style else {},
            "production": {
                "provider": self._provider,
                "model": self._model,
                "quality_preset": self._quality_preset.value,
                "default_duration": self._duration,
                "default_aspect_ratio": self._aspect_ratio,
            },
            "episodes": [ep.to_dict() for ep in self._episodes],
        }

    @classmethod
    def load(cls, path: Union[str, Path]) -> "SeriesBuilder":
        """
        Load a series configuration from file.

        Args:
            path: Path to configuration file (YAML or JSON)

        Returns:
            Configured SeriesBuilder
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Series config not found: {path}")

        with open(path, "r") as f:
            if path.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        # Build from loaded data
        series_data = data.get("series", {})
        builder = cls(series_data.get("name", "Untitled"))
        builder._description = series_data.get("description", "")
        builder._genre = series_data.get("genre", "")

        # Characters
        for cid, char_data in data.get("characters", {}).items():
            char = Character.from_dict({**char_data, "character_id": cid})
            builder._characters[cid] = char

        # Locations
        builder._locations = data.get("locations", {})

        # Style
        style_data = data.get("visual_style", {})
        if style_data:
            builder._style = VisualStyle.from_dict(style_data)

        # Production settings
        prod = data.get("production", {})
        builder._provider = prod.get("provider", "fal")
        builder._model = prod.get("model", "kling-2.5")
        builder._duration = prod.get("default_duration", 5)
        builder._aspect_ratio = prod.get("default_aspect_ratio", "16:9")

        preset_name = prod.get("quality_preset", "balanced")
        builder._quality_preset = QualityPreset(preset_name)

        logger.info(f"Loaded series configuration from: {path}")
        return builder


# =============================================================================
# Convenience Functions
# =============================================================================


def create_series(name: str) -> SeriesBuilder:
    """
    Start building a new series.

    This is the primary entry point for series creation.

    Example:
        series = (
            create_series("My Adventure")
            .description("An epic journey")
            .cinematic_style()
            .high_quality()
            .character(
                CharacterBuilder("hero")
                .name("Alex")
                .build()
            )
            .build()
        )
    """
    return SeriesBuilder(name)


def load_series(path: Union[str, Path]) -> SeriesBuilder:
    """
    Load an existing series configuration.

    Args:
        path: Path to the series configuration file

    Returns:
        SeriesBuilder with loaded configuration
    """
    return SeriesBuilder.load(path)


def quick_series(
    name: str,
    protagonist_name: str,
    protagonist_description: str = "",
    style: str = "cinematic",
    quality: str = "balanced",
) -> Series:
    """
    Create a simple series with minimal configuration.

    For quick testing or simple projects.

    Args:
        name: Series name
        protagonist_name: Main character's name
        protagonist_description: Character description
        style: Style preset name
        quality: Quality preset name

    Returns:
        Configured Series object
    """
    builder = SeriesBuilder(name)

    # Style
    style_map = {
        "cinematic": StylePresets.cinematic(),
        "anime": StylePresets.anime(),
        "documentary": StylePresets.documentary(),
        "noir": StylePresets.noir(),
        "scifi": StylePresets.scifi(),
    }
    builder._style = style_map.get(style, StylePresets.cinematic())

    # Quality
    builder._quality_preset = QualityPreset(quality)

    # Protagonist
    builder.protagonist(
        "protagonist",
        protagonist_name,
        description=protagonist_description,
    )

    return builder.build()
