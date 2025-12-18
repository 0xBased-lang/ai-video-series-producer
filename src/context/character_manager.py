"""
Character Bible Manager
=======================

Manages character definitions, visual descriptions, and reference images
to ensure consistent character representation across all video generations.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import yaml

logger = logging.getLogger(__name__)


@dataclass
class VisualFeatures:
    """Visual characteristics of a character."""
    age: str = ""
    gender: str = ""
    ethnicity: str = ""
    build: str = ""
    height: str = ""

    # Facial features
    face_shape: str = ""
    eyes: str = ""
    hair: str = ""
    skin: str = ""
    distinguishing_features: str = ""

    # Default outfit
    default_top: str = ""
    default_bottom: str = ""
    default_accessories: str = ""

    def to_prompt_fragment(self) -> str:
        """Convert visual features to a prompt fragment."""
        parts = []

        # Age and basic description
        if self.age:
            parts.append(self.age)
        if self.gender:
            parts.append(self.gender)
        if self.ethnicity:
            parts.append(self.ethnicity)
        if self.build:
            parts.append(f"{self.build} build")

        # Hair and eyes
        if self.hair:
            parts.append(f"{self.hair} hair")
        if self.eyes:
            parts.append(f"{self.eyes} eyes")

        # Distinguishing features
        if self.distinguishing_features:
            parts.append(self.distinguishing_features)

        return ", ".join(parts)

    def outfit_to_prompt(self) -> str:
        """Convert outfit to prompt fragment."""
        parts = []
        if self.default_top:
            parts.append(f"wearing {self.default_top}")
        if self.default_bottom:
            parts.append(self.default_bottom)
        if self.default_accessories:
            parts.append(self.default_accessories)
        return ", ".join(parts)


@dataclass
class Character:
    """A character in the video series."""

    # Identity
    name: str
    role: str = "background"  # protagonist, secondary, background
    importance: str = "background"  # primary, secondary, background

    # Visual features
    visual: VisualFeatures = field(default_factory=VisualFeatures)

    # Reference images (paths)
    references: Dict[str, str] = field(default_factory=dict)
    # e.g., {"front": "path/to/front.jpg", "profile": "path/to/profile.jpg"}

    # Pre-built prompt fragments
    prompt_fragments: Dict[str, str] = field(default_factory=dict)
    # e.g., {"identity": "30yo woman...", "outfit": "wearing..."}

    # Personality (for action descriptions)
    personality_traits: List[str] = field(default_factory=list)
    mannerisms: List[str] = field(default_factory=list)
    movement_style: str = ""

    # LoRA training (if applicable)
    lora_url: Optional[str] = None
    lora_trigger_word: Optional[str] = None
    lora_weight: float = 0.8

    # Generation tracking
    best_generation_id: Optional[str] = None
    generation_count: int = 0

    def get_identity_prompt(self) -> str:
        """Get the character identity prompt fragment."""
        if "identity" in self.prompt_fragments:
            return self.prompt_fragments["identity"]
        return self.visual.to_prompt_fragment()

    def get_outfit_prompt(self, variant: Optional[str] = None) -> str:
        """Get the character outfit prompt fragment."""
        if variant and f"outfit_{variant}" in self.prompt_fragments:
            return self.prompt_fragments[f"outfit_{variant}"]
        if "outfit" in self.prompt_fragments:
            return self.prompt_fragments["outfit"]
        return self.visual.outfit_to_prompt()

    def get_full_prompt(self, action: str = "", variant: Optional[str] = None) -> str:
        """Get full character prompt with action."""
        parts = [
            self.get_identity_prompt(),
            self.get_outfit_prompt(variant),
        ]
        if action:
            parts.append(action)
        return ", ".join(filter(None, parts))

    def get_reference_images(self, max_count: int = 4) -> List[str]:
        """Get reference image paths."""
        images = list(self.references.values())
        return images[:max_count]

    def get_primary_reference(self) -> Optional[str]:
        """Get the primary reference image (front-facing preferred)."""
        for key in ["front", "primary", "main", "three_quarter"]:
            if key in self.references:
                return self.references[key]
        if self.references:
            return list(self.references.values())[0]
        return None


@dataclass
class Location:
    """A location/set in the video series."""

    name: str
    description: str = ""
    reference: Optional[str] = None

    # Prompt fragments for different moods/times
    prompt_fragments: Dict[str, str] = field(default_factory=dict)
    mood_variants: Dict[str, str] = field(default_factory=dict)

    def get_setting_prompt(self, mood: Optional[str] = None) -> str:
        """Get the location setting prompt."""
        if mood and mood in self.mood_variants:
            return self.mood_variants[mood]
        if "setting" in self.prompt_fragments:
            return self.prompt_fragments["setting"]
        return self.description


@dataclass
class VisualStyle:
    """Series-wide visual style definition."""

    description: str = ""
    style_reference: Optional[str] = None

    # Modifiers to append to all prompts
    style_modifiers: List[str] = field(default_factory=list)
    negative_modifiers: List[str] = field(default_factory=list)

    # Camera preferences
    default_camera_movement: str = "steady"
    preferred_angles: List[str] = field(default_factory=list)
    avoid_angles: List[str] = field(default_factory=list)

    def get_style_suffix(self) -> str:
        """Get style modifiers as prompt suffix."""
        return ", ".join(self.style_modifiers)

    def get_negative_prompt(self) -> str:
        """Get negative prompt from modifiers."""
        return ", ".join(self.negative_modifiers)


class CharacterBible:
    """
    Manages the character bible for a video series.

    The character bible contains all characters, locations, and visual style
    information needed to maintain consistency across video generations.
    """

    def __init__(self, bible_path: Optional[Union[str, Path]] = None):
        """
        Initialize the character bible.

        Args:
            bible_path: Path to character_bible.yaml file
        """
        self.bible_path = Path(bible_path) if bible_path else None

        # Series metadata
        self.series_name: str = ""
        self.series_description: str = ""
        self.genre: str = ""
        self.tone: str = ""

        # Visual style
        self.visual_style = VisualStyle()

        # Characters and locations
        self.characters: Dict[str, Character] = {}
        self.locations: Dict[str, Location] = {}

        # Prompt templates
        self.prompt_templates: Dict[str, str] = {}

        # Load if path provided
        if self.bible_path and self.bible_path.exists():
            self.load(self.bible_path)

    def load(self, path: Union[str, Path]) -> None:
        """Load character bible from YAML file."""
        path = Path(path)

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Series metadata
        series = data.get("series", {})
        self.series_name = series.get("name", "")
        self.series_description = series.get("description", "")
        self.genre = series.get("genre", "")
        self.tone = series.get("tone", "")

        # Visual style
        style_data = data.get("visual_style", {})
        self.visual_style = VisualStyle(
            description=style_data.get("style_description", ""),
            style_reference=style_data.get("style_reference"),
            style_modifiers=style_data.get("style_modifiers", []),
            negative_modifiers=style_data.get("negative_modifiers", []),
            default_camera_movement=style_data.get("camera_style", {}).get("default_movement", "steady"),
            preferred_angles=style_data.get("camera_style", {}).get("preferred_angles", []),
            avoid_angles=style_data.get("camera_style", {}).get("avoid_angles", []),
        )

        # Characters
        for char_id, char_data in data.get("characters", {}).items():
            self.characters[char_id] = self._parse_character(char_data)

        # Locations
        for loc_id, loc_data in data.get("locations", {}).items():
            self.locations[loc_id] = self._parse_location(loc_data)

        # Prompt templates
        self.prompt_templates = data.get("prompt_templates", {})

        logger.info(f"Loaded character bible from {path}")
        logger.info(f"  - {len(self.characters)} characters")
        logger.info(f"  - {len(self.locations)} locations")

    def _parse_character(self, data: Dict) -> Character:
        """Parse character data from YAML."""
        visual_data = data.get("visual", {})
        face_data = visual_data.get("face", {})
        outfit_data = visual_data.get("default_outfit", {})

        visual = VisualFeatures(
            age=visual_data.get("age", ""),
            gender=visual_data.get("gender", ""),
            ethnicity=visual_data.get("ethnicity", ""),
            build=visual_data.get("build", ""),
            height=visual_data.get("height", ""),
            face_shape=face_data.get("shape", ""),
            eyes=face_data.get("eyes", ""),
            hair=face_data.get("hair", ""),
            skin=face_data.get("skin", ""),
            distinguishing_features=face_data.get("distinguishing", ""),
            default_top=outfit_data.get("top", ""),
            default_bottom=outfit_data.get("bottom", ""),
            default_accessories=outfit_data.get("accessories", ""),
        )

        personality = data.get("personality", {})

        return Character(
            name=data.get("name", ""),
            role=data.get("role", "background"),
            importance=data.get("importance", "background"),
            visual=visual,
            references=data.get("references", {}),
            prompt_fragments=data.get("prompt_fragments", {}),
            personality_traits=personality.get("traits", []),
            mannerisms=personality.get("mannerisms", []),
            movement_style=personality.get("movement_style", ""),
        )

    def _parse_location(self, data: Dict) -> Location:
        """Parse location data from YAML."""
        return Location(
            name=data.get("name", ""),
            description=data.get("description", ""),
            reference=data.get("reference"),
            prompt_fragments=data.get("prompt_fragments", {}),
            mood_variants=data.get("mood_variants", {}),
        )

    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """Save character bible to YAML file."""
        path = Path(path) if path else self.bible_path
        if not path:
            raise ValueError("No path specified for saving")

        data = {
            "series": {
                "name": self.series_name,
                "description": self.series_description,
                "genre": self.genre,
                "tone": self.tone,
            },
            "visual_style": {
                "style_description": self.visual_style.description,
                "style_reference": self.visual_style.style_reference,
                "style_modifiers": self.visual_style.style_modifiers,
                "negative_modifiers": self.visual_style.negative_modifiers,
                "camera_style": {
                    "default_movement": self.visual_style.default_camera_movement,
                    "preferred_angles": self.visual_style.preferred_angles,
                    "avoid_angles": self.visual_style.avoid_angles,
                },
            },
            "characters": {
                char_id: self._serialize_character(char)
                for char_id, char in self.characters.items()
            },
            "locations": {
                loc_id: self._serialize_location(loc)
                for loc_id, loc in self.locations.items()
            },
            "prompt_templates": self.prompt_templates,
        }

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Saved character bible to {path}")

    def _serialize_character(self, char: Character) -> Dict:
        """Serialize character to dictionary."""
        return {
            "name": char.name,
            "role": char.role,
            "importance": char.importance,
            "visual": {
                "age": char.visual.age,
                "gender": char.visual.gender,
                "ethnicity": char.visual.ethnicity,
                "build": char.visual.build,
                "height": char.visual.height,
                "face": {
                    "shape": char.visual.face_shape,
                    "eyes": char.visual.eyes,
                    "hair": char.visual.hair,
                    "skin": char.visual.skin,
                    "distinguishing": char.visual.distinguishing_features,
                },
                "default_outfit": {
                    "top": char.visual.default_top,
                    "bottom": char.visual.default_bottom,
                    "accessories": char.visual.default_accessories,
                },
            },
            "references": char.references,
            "prompt_fragments": char.prompt_fragments,
            "personality": {
                "traits": char.personality_traits,
                "mannerisms": char.mannerisms,
                "movement_style": char.movement_style,
            },
        }

    def _serialize_location(self, loc: Location) -> Dict:
        """Serialize location to dictionary."""
        return {
            "name": loc.name,
            "description": loc.description,
            "reference": loc.reference,
            "prompt_fragments": loc.prompt_fragments,
            "mood_variants": loc.mood_variants,
        }

    # -------------------------------------------------------------------------
    # Character Access
    # -------------------------------------------------------------------------

    def get_character(self, char_id: str) -> Optional[Character]:
        """Get a character by ID."""
        return self.characters.get(char_id)

    def get_location(self, loc_id: str) -> Optional[Location]:
        """Get a location by ID."""
        return self.locations.get(loc_id)

    def add_character(self, char_id: str, character: Character) -> None:
        """Add a new character."""
        self.characters[char_id] = character

    def add_location(self, loc_id: str, location: Location) -> None:
        """Add a new location."""
        self.locations[loc_id] = location

    # -------------------------------------------------------------------------
    # Prompt Building
    # -------------------------------------------------------------------------

    def build_scene_prompt(
        self,
        character_id: str,
        action: str,
        location_id: Optional[str] = None,
        location_mood: Optional[str] = None,
        camera_direction: Optional[str] = None,
        outfit_variant: Optional[str] = None,
    ) -> str:
        """
        Build a complete scene prompt.

        Args:
            character_id: Character identifier
            action: What the character is doing
            location_id: Location identifier (optional)
            location_mood: Mood variant for location (optional)
            camera_direction: Camera movement/angle (optional)
            outfit_variant: Outfit variant name (optional)

        Returns:
            Complete prompt string
        """
        parts = []

        # Location
        if location_id:
            location = self.get_location(location_id)
            if location:
                parts.append(location.get_setting_prompt(location_mood))

        # Character
        character = self.get_character(character_id)
        if character:
            parts.append(character.get_full_prompt(action, outfit_variant))

        # Camera
        if camera_direction:
            parts.append(camera_direction)

        # Style modifiers
        style_suffix = self.visual_style.get_style_suffix()
        if style_suffix:
            parts.append(style_suffix)

        return ". ".join(filter(None, parts))

    def build_continuation_prompt(
        self,
        character_id: str,
        action: str,
        **kwargs,
    ) -> str:
        """Build a prompt for scene continuation (chaining)."""
        base_prompt = self.build_scene_prompt(character_id, action, **kwargs)
        return f"Seamless continuation from previous scene. {base_prompt}"

    def get_reference_images_for_scene(
        self,
        character_id: str,
        location_id: Optional[str] = None,
        max_images: int = 4,
    ) -> List[str]:
        """
        Get reference images for a scene.

        Returns character references, optionally with location reference.
        """
        images = []

        # Character references
        character = self.get_character(character_id)
        if character:
            char_refs = character.get_reference_images(max_images - 1)
            images.extend(char_refs)

        # Location reference
        if location_id and len(images) < max_images:
            location = self.get_location(location_id)
            if location and location.reference:
                images.append(location.reference)

        return images[:max_images]

    def get_negative_prompt(self) -> str:
        """Get the negative prompt for generations."""
        return self.visual_style.get_negative_prompt()
