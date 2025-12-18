"""
Series Module
=============

Unified series establishment and management for AI video production.

This module provides a clean, simplified interface for:
- Creating and managing video series
- Defining characters with consistent visual identity
- Establishing visual style and quality standards
- Orchestrating episode generation
"""

from .builder import SeriesBuilder
from .series import Series, Episode, Scene
from .character import Character, CharacterStyle
from .style import VisualStyle, QualityPreset

__all__ = [
    # Builder pattern for clean series creation
    "SeriesBuilder",
    # Core models
    "Series",
    "Episode",
    "Scene",
    "Character",
    "CharacterStyle",
    "VisualStyle",
    "QualityPreset",
]
