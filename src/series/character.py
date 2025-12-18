"""
Character Models
================

Character definition and styling for consistent identity across generations.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class CharacterType(Enum):
    """Type of character."""

    PROTAGONIST = "protagonist"
    ANTAGONIST = "antagonist"
    SUPPORTING = "supporting"
    BACKGROUND = "background"


@dataclass
class CharacterStyle:
    """
    Visual styling for a character.

    Defines the character's appearance characteristics
    that should remain consistent across generations.
    """

    # Physical appearance
    age_range: str = ""  # e.g., "25-30", "elderly", "teenager"
    gender: str = ""
    ethnicity: str = ""
    body_type: str = ""

    # Face
    face_shape: str = ""
    eye_color: str = ""
    hair_color: str = ""
    hair_style: str = ""
    facial_hair: str = ""
    distinguishing_features: List[str] = field(default_factory=list)

    # Clothing (default outfit)
    default_outfit: str = ""
    outfit_variants: Dict[str, str] = field(default_factory=dict)

    # Voice/mannerisms (for audio-enabled generation)
    voice_description: str = ""
    mannerisms: List[str] = field(default_factory=list)

    def build_prompt_fragment(self, include_outfit: bool = True) -> str:
        """Build a prompt fragment describing this character's appearance."""
        parts = []

        # Demographics
        if self.age_range:
            parts.append(self.age_range)
        if self.gender:
            parts.append(self.gender)
        if self.ethnicity:
            parts.append(self.ethnicity)

        # Physical
        if self.body_type:
            parts.append(self.body_type)

        # Face
        if self.hair_color and self.hair_style:
            parts.append(f"{self.hair_color} {self.hair_style} hair")
        elif self.hair_color:
            parts.append(f"{self.hair_color} hair")

        if self.eye_color:
            parts.append(f"{self.eye_color} eyes")

        if self.facial_hair:
            parts.append(self.facial_hair)

        # Distinguishing features
        if self.distinguishing_features:
            parts.extend(self.distinguishing_features)

        # Outfit
        if include_outfit and self.default_outfit:
            parts.append(f"wearing {self.default_outfit}")

        return ", ".join(parts)

    def get_outfit(self, variant: Optional[str] = None) -> str:
        """Get outfit description, optionally for a specific variant."""
        if variant and variant in self.outfit_variants:
            return self.outfit_variants[variant]
        return self.default_outfit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "age_range": self.age_range,
            "gender": self.gender,
            "ethnicity": self.ethnicity,
            "body_type": self.body_type,
            "face_shape": self.face_shape,
            "eye_color": self.eye_color,
            "hair_color": self.hair_color,
            "hair_style": self.hair_style,
            "facial_hair": self.facial_hair,
            "distinguishing_features": self.distinguishing_features,
            "default_outfit": self.default_outfit,
            "outfit_variants": self.outfit_variants,
            "voice_description": self.voice_description,
            "mannerisms": self.mannerisms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterStyle":
        """Create from dictionary."""
        return cls(
            age_range=data.get("age_range", ""),
            gender=data.get("gender", ""),
            ethnicity=data.get("ethnicity", ""),
            body_type=data.get("body_type", ""),
            face_shape=data.get("face_shape", ""),
            eye_color=data.get("eye_color", ""),
            hair_color=data.get("hair_color", ""),
            hair_style=data.get("hair_style", ""),
            facial_hair=data.get("facial_hair", ""),
            distinguishing_features=data.get("distinguishing_features", []),
            default_outfit=data.get("default_outfit", ""),
            outfit_variants=data.get("outfit_variants", {}),
            voice_description=data.get("voice_description", ""),
            mannerisms=data.get("mannerisms", []),
        )


@dataclass
class Character:
    """
    A character in the video series.

    Characters maintain consistent visual identity through:
    - Detailed style description
    - Reference images
    - Prompt fragments for generation
    """

    # Identity
    character_id: str = ""
    name: str = ""
    role: str = ""  # e.g., "main character", "love interest", "mentor"
    character_type: CharacterType = CharacterType.SUPPORTING

    # Description
    description: str = ""  # Narrative description
    backstory: str = ""
    personality_traits: List[str] = field(default_factory=list)

    # Visual style
    style: CharacterStyle = field(default_factory=CharacterStyle)

    # Reference images (paths)
    reference_images: Dict[str, str] = field(default_factory=dict)
    # e.g., {"front": "path/to/front.jpg", "side": "path/to/side.jpg"}

    # Prompt engineering
    prompt_prefix: str = ""  # Added before character description
    prompt_suffix: str = ""  # Added after character description

    # Generation settings
    preferred_seed: Optional[int] = None  # For reproducibility

    def build_prompt(
        self,
        action: str,
        location: Optional[str] = None,
        outfit_variant: Optional[str] = None,
        camera: Optional[str] = None,
        include_style: bool = True,
    ) -> str:
        """
        Build a complete prompt for generating this character.

        Args:
            action: What the character is doing
            location: Where the scene takes place
            outfit_variant: Specific outfit to use
            camera: Camera direction/angle
            include_style: Whether to include style description

        Returns:
            Complete prompt string
        """
        parts = []

        # Prefix
        if self.prompt_prefix:
            parts.append(self.prompt_prefix)

        # Character identity
        identity = f"{self.name}"
        if include_style:
            style_desc = self.style.build_prompt_fragment()
            if style_desc:
                identity += f", {style_desc}"

        # Outfit override
        if outfit_variant:
            outfit = self.style.get_outfit(outfit_variant)
            if outfit:
                identity += f", wearing {outfit}"

        parts.append(identity)

        # Action
        if action:
            parts.append(action)

        # Location
        if location:
            parts.append(f"in {location}")

        # Camera
        if camera:
            parts.append(f", {camera}")

        # Suffix
        if self.prompt_suffix:
            parts.append(self.prompt_suffix)

        return ", ".join(filter(None, parts))

    def get_reference_image(self, view: str = "front") -> Optional[str]:
        """Get a reference image path for the specified view."""
        return self.reference_images.get(view) or self.get_primary_reference()

    def get_primary_reference(self) -> Optional[str]:
        """Get the primary reference image."""
        if not self.reference_images:
            return None
        # Prefer front view, then any available
        return self.reference_images.get("front") or next(iter(self.reference_images.values()))

    def get_all_references(self, max_images: int = 4) -> List[str]:
        """Get all reference images up to the limit."""
        refs = list(self.reference_images.values())
        return refs[:max_images]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "character_id": self.character_id,
            "name": self.name,
            "role": self.role,
            "character_type": self.character_type.value,
            "description": self.description,
            "backstory": self.backstory,
            "personality_traits": self.personality_traits,
            "style": self.style.to_dict(),
            "reference_images": self.reference_images,
            "prompt_prefix": self.prompt_prefix,
            "prompt_suffix": self.prompt_suffix,
            "preferred_seed": self.preferred_seed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        """Create Character from dictionary."""
        return cls(
            character_id=data.get("character_id", ""),
            name=data.get("name", ""),
            role=data.get("role", ""),
            character_type=CharacterType(data.get("character_type", "supporting")),
            description=data.get("description", ""),
            backstory=data.get("backstory", ""),
            personality_traits=data.get("personality_traits", []),
            style=CharacterStyle.from_dict(data.get("style", {})),
            reference_images=data.get("reference_images", {}),
            prompt_prefix=data.get("prompt_prefix", ""),
            prompt_suffix=data.get("prompt_suffix", ""),
            preferred_seed=data.get("preferred_seed"),
        )


# =============================================================================
# Character Builder for Fluent Interface
# =============================================================================


class CharacterBuilder:
    """
    Fluent builder for creating characters.

    Example:
        character = (
            CharacterBuilder("hero")
            .name("Alex Chen")
            .role("protagonist")
            .age("28")
            .gender("female")
            .hair("black", "shoulder-length wavy")
            .eyes("brown")
            .outfit("leather jacket over white t-shirt, dark jeans")
            .feature("small scar on left cheek")
            .reference("front", "refs/alex_front.jpg")
            .reference("side", "refs/alex_side.jpg")
            .build()
        )
    """

    def __init__(self, character_id: str):
        self._character_id = character_id
        self._name = ""
        self._role = ""
        self._type = CharacterType.SUPPORTING
        self._description = ""
        self._style = CharacterStyle()
        self._references: Dict[str, str] = {}
        self._prompt_prefix = ""
        self._prompt_suffix = ""

    def name(self, name: str) -> "CharacterBuilder":
        """Set character name."""
        self._name = name
        return self

    def role(self, role: str) -> "CharacterBuilder":
        """Set character role."""
        self._role = role
        return self

    def as_protagonist(self) -> "CharacterBuilder":
        """Set as protagonist."""
        self._type = CharacterType.PROTAGONIST
        return self

    def as_antagonist(self) -> "CharacterBuilder":
        """Set as antagonist."""
        self._type = CharacterType.ANTAGONIST
        return self

    def description(self, description: str) -> "CharacterBuilder":
        """Set narrative description."""
        self._description = description
        return self

    def age(self, age_range: str) -> "CharacterBuilder":
        """Set age range."""
        self._style.age_range = age_range
        return self

    def gender(self, gender: str) -> "CharacterBuilder":
        """Set gender."""
        self._style.gender = gender
        return self

    def ethnicity(self, ethnicity: str) -> "CharacterBuilder":
        """Set ethnicity."""
        self._style.ethnicity = ethnicity
        return self

    def body(self, body_type: str) -> "CharacterBuilder":
        """Set body type."""
        self._style.body_type = body_type
        return self

    def hair(self, color: str, style: str = "") -> "CharacterBuilder":
        """Set hair color and style."""
        self._style.hair_color = color
        self._style.hair_style = style
        return self

    def eyes(self, color: str) -> "CharacterBuilder":
        """Set eye color."""
        self._style.eye_color = color
        return self

    def facial_hair(self, description: str) -> "CharacterBuilder":
        """Set facial hair."""
        self._style.facial_hair = description
        return self

    def feature(self, feature: str) -> "CharacterBuilder":
        """Add a distinguishing feature."""
        self._style.distinguishing_features.append(feature)
        return self

    def outfit(self, outfit: str) -> "CharacterBuilder":
        """Set default outfit."""
        self._style.default_outfit = outfit
        return self

    def outfit_variant(self, name: str, outfit: str) -> "CharacterBuilder":
        """Add an outfit variant."""
        self._style.outfit_variants[name] = outfit
        return self

    def reference(self, view: str, path: str) -> "CharacterBuilder":
        """Add a reference image."""
        self._references[view] = path
        return self

    def prompt_prefix(self, prefix: str) -> "CharacterBuilder":
        """Set prompt prefix."""
        self._prompt_prefix = prefix
        return self

    def prompt_suffix(self, suffix: str) -> "CharacterBuilder":
        """Set prompt suffix."""
        self._prompt_suffix = suffix
        return self

    def build(self) -> Character:
        """Build the character."""
        return Character(
            character_id=self._character_id,
            name=self._name,
            role=self._role,
            character_type=self._type,
            description=self._description,
            style=self._style,
            reference_images=self._references,
            prompt_prefix=self._prompt_prefix,
            prompt_suffix=self._prompt_suffix,
        )
