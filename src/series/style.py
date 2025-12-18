"""
Visual Style Models
===================

Style definitions and quality presets for consistent visual output.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class QualityPreset(Enum):
    """
    Pre-configured quality presets for different use cases.

    Each preset balances generation speed, quality, and cost.
    """

    # Fast generation for previews and iterations
    DRAFT = "draft"

    # Balanced for most production use
    BALANCED = "balanced"

    # High quality for final output
    HIGH = "high"

    # Maximum quality with all enhancements
    CINEMATIC = "cinematic"

    def get_settings(self) -> Dict[str, Any]:
        """Get the settings for this preset."""
        presets = {
            QualityPreset.DRAFT: {
                "model": "veo-3-fast",
                "duration": 5,
                "resolution": "480p",
                "with_audio": False,
                "guidance_scale": 0.5,
            },
            QualityPreset.BALANCED: {
                "model": "kling-2.5",
                "duration": 5,
                "resolution": "720p",
                "with_audio": False,
                "guidance_scale": 0.7,
            },
            QualityPreset.HIGH: {
                "model": "kling-2.6",
                "duration": 10,
                "resolution": "1080p",
                "with_audio": False,
                "guidance_scale": 0.8,
            },
            QualityPreset.CINEMATIC: {
                "model": "veo-3",
                "duration": 8,
                "resolution": "1080p",
                "with_audio": True,
                "guidance_scale": 0.9,
            },
        }
        return presets.get(self, presets[QualityPreset.BALANCED])


@dataclass
class ColorPalette:
    """Color palette for consistent visual style."""

    primary: str = ""  # Main color theme
    secondary: str = ""
    accent: str = ""
    background: str = ""

    # Mood-based colors
    warm_tones: List[str] = field(default_factory=list)
    cool_tones: List[str] = field(default_factory=list)

    def to_prompt_fragment(self) -> str:
        """Build a prompt fragment describing the color palette."""
        parts = []
        if self.primary:
            parts.append(f"primarily {self.primary}")
        if self.warm_tones:
            parts.append(f"warm tones ({', '.join(self.warm_tones)})")
        if self.cool_tones:
            parts.append(f"cool tones ({', '.join(self.cool_tones)})")
        return ", ".join(parts) if parts else ""


@dataclass
class LightingStyle:
    """Lighting configuration for visual consistency."""

    type: str = "natural"  # natural, studio, dramatic, soft, hard
    direction: str = ""  # front, side, back, overhead, low-angle
    quality: str = ""  # soft, hard, diffused
    color_temperature: str = ""  # warm, neutral, cool
    time_of_day: str = ""  # golden hour, midday, dusk, night

    # Special effects
    rim_light: bool = False
    ambient_occlusion: bool = False
    volumetric: bool = False

    def to_prompt_fragment(self) -> str:
        """Build a prompt fragment describing the lighting."""
        parts = []

        if self.type:
            parts.append(f"{self.type} lighting")

        if self.time_of_day:
            parts.append(self.time_of_day)
        elif self.direction:
            parts.append(f"{self.direction} light")

        if self.quality:
            parts.append(f"{self.quality} light quality")

        if self.color_temperature:
            parts.append(f"{self.color_temperature} color temperature")

        if self.volumetric:
            parts.append("volumetric lighting")

        if self.rim_light:
            parts.append("rim lighting")

        return ", ".join(parts) if parts else ""


@dataclass
class CameraStyle:
    """Camera configuration for consistent framing."""

    # Default framing
    default_shot: str = "medium"  # close-up, medium, wide, extreme wide
    default_angle: str = "eye-level"  # eye-level, low, high, dutch

    # Movement preferences
    preferred_movements: List[str] = field(default_factory=list)
    # e.g., ["slow pan", "steady", "tracking"]

    # Technical
    depth_of_field: str = ""  # shallow, deep
    lens_style: str = ""  # cinematic, documentary, telephoto

    def to_prompt_fragment(self, override_shot: Optional[str] = None) -> str:
        """Build a prompt fragment describing the camera."""
        parts = []

        shot = override_shot or self.default_shot
        if shot:
            parts.append(f"{shot} shot")

        if self.default_angle and self.default_angle != "eye-level":
            parts.append(f"{self.default_angle} angle")

        if self.depth_of_field:
            parts.append(f"{self.depth_of_field} depth of field")

        if self.lens_style:
            parts.append(f"{self.lens_style}")

        return ", ".join(parts) if parts else ""


@dataclass
class VisualStyle:
    """
    Complete visual style definition for a series.

    Maintains consistency across all generated content through:
    - Style modifiers added to all prompts
    - Negative prompts to avoid unwanted elements
    - Color, lighting, and camera preferences
    """

    # Style name and description
    name: str = ""
    description: str = ""

    # Overall aesthetic
    aesthetic: str = "cinematic"  # cinematic, anime, photorealistic, stylized
    mood: str = ""  # dark, bright, moody, cheerful, mysterious
    era: str = ""  # modern, vintage, futuristic, period

    # Components
    colors: ColorPalette = field(default_factory=ColorPalette)
    lighting: LightingStyle = field(default_factory=LightingStyle)
    camera: CameraStyle = field(default_factory=CameraStyle)

    # Prompt modifiers (applied to all generations)
    style_modifiers: List[str] = field(default_factory=lambda: [
        "cinematic",
        "professional lighting",
        "high quality",
    ])

    # Things to avoid
    negative_modifiers: List[str] = field(default_factory=lambda: [
        "blurry",
        "distorted",
        "low quality",
        "amateur",
        "watermark",
        "text",
    ])

    # Reference style images
    style_references: List[str] = field(default_factory=list)

    def build_style_prompt(self) -> str:
        """Build the style portion of a prompt."""
        parts = []

        # Aesthetic
        if self.aesthetic:
            parts.append(self.aesthetic)

        # Mood
        if self.mood:
            parts.append(self.mood)

        # Era
        if self.era:
            parts.append(self.era)

        # Lighting
        lighting_fragment = self.lighting.to_prompt_fragment()
        if lighting_fragment:
            parts.append(lighting_fragment)

        # Style modifiers
        parts.extend(self.style_modifiers)

        return ", ".join(parts)

    def get_negative_prompt(self) -> str:
        """Get the negative prompt."""
        return ", ".join(self.negative_modifiers)

    def build_complete_prompt(
        self,
        subject: str,
        action: str = "",
        location: str = "",
        camera_override: Optional[str] = None,
    ) -> str:
        """
        Build a complete prompt with all style elements.

        Args:
            subject: Main subject (character, object)
            action: What's happening
            location: Where it's happening
            camera_override: Override default camera settings

        Returns:
            Complete prompt string
        """
        parts = []

        # Subject and action
        if subject:
            parts.append(subject)
        if action:
            parts.append(action)

        # Location
        if location:
            parts.append(f"in {location}")

        # Camera
        camera_fragment = self.camera.to_prompt_fragment(camera_override)
        if camera_fragment:
            parts.append(camera_fragment)

        # Style
        style_fragment = self.build_style_prompt()
        if style_fragment:
            parts.append(style_fragment)

        return ", ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "aesthetic": self.aesthetic,
            "mood": self.mood,
            "era": self.era,
            "style_modifiers": self.style_modifiers,
            "negative_modifiers": self.negative_modifiers,
            "style_references": self.style_references,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualStyle":
        """Create VisualStyle from dictionary."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            aesthetic=data.get("aesthetic", "cinematic"),
            mood=data.get("mood", ""),
            era=data.get("era", ""),
            style_modifiers=data.get("style_modifiers", []),
            negative_modifiers=data.get("negative_modifiers", []),
            style_references=data.get("style_references", []),
        )


# =============================================================================
# Pre-built Style Presets
# =============================================================================


class StylePresets:
    """Collection of pre-built visual style presets."""

    @staticmethod
    def cinematic() -> VisualStyle:
        """Hollywood-style cinematic look."""
        return VisualStyle(
            name="Cinematic",
            description="Professional Hollywood-style cinematography",
            aesthetic="cinematic",
            mood="dramatic",
            lighting=LightingStyle(
                type="dramatic",
                quality="soft",
                color_temperature="warm",
                rim_light=True,
            ),
            camera=CameraStyle(
                default_shot="medium",
                depth_of_field="shallow",
                lens_style="cinematic anamorphic",
            ),
            style_modifiers=[
                "cinematic",
                "film grain",
                "professional color grading",
                "shallow depth of field",
                "dramatic lighting",
            ],
        )

    @staticmethod
    def anime() -> VisualStyle:
        """Anime/animation style."""
        return VisualStyle(
            name="Anime",
            description="Japanese animation style",
            aesthetic="anime",
            mood="vibrant",
            colors=ColorPalette(
                primary="vibrant colors",
                warm_tones=["pink", "orange"],
                cool_tones=["blue", "purple"],
            ),
            style_modifiers=[
                "anime style",
                "cel shading",
                "vibrant colors",
                "clean lines",
                "detailed backgrounds",
            ],
            negative_modifiers=[
                "photorealistic",
                "3D render",
                "low quality",
                "distorted face",
            ],
        )

    @staticmethod
    def documentary() -> VisualStyle:
        """Documentary/naturalistic style."""
        return VisualStyle(
            name="Documentary",
            description="Naturalistic documentary style",
            aesthetic="photorealistic",
            mood="authentic",
            lighting=LightingStyle(
                type="natural",
                quality="soft",
            ),
            camera=CameraStyle(
                default_shot="medium",
                lens_style="documentary",
            ),
            style_modifiers=[
                "documentary style",
                "natural lighting",
                "authentic",
                "handheld camera feel",
            ],
        )

    @staticmethod
    def noir() -> VisualStyle:
        """Film noir style."""
        return VisualStyle(
            name="Noir",
            description="Classic film noir aesthetic",
            aesthetic="cinematic",
            mood="dark and mysterious",
            era="1940s noir",
            colors=ColorPalette(
                primary="high contrast black and white",
            ),
            lighting=LightingStyle(
                type="dramatic",
                direction="side",
                quality="hard",
                volumetric=True,
            ),
            style_modifiers=[
                "film noir",
                "high contrast",
                "dramatic shadows",
                "black and white",
                "moody atmosphere",
            ],
        )

    @staticmethod
    def scifi() -> VisualStyle:
        """Science fiction style."""
        return VisualStyle(
            name="Sci-Fi",
            description="Futuristic science fiction aesthetic",
            aesthetic="cinematic",
            mood="futuristic",
            era="futuristic",
            colors=ColorPalette(
                primary="neon",
                cool_tones=["cyan", "blue", "purple"],
            ),
            lighting=LightingStyle(
                type="dramatic",
                color_temperature="cool",
                rim_light=True,
                volumetric=True,
            ),
            style_modifiers=[
                "science fiction",
                "futuristic",
                "neon lighting",
                "high tech",
                "cinematic",
            ],
        )
