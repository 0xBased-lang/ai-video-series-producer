"""
Context Management System
=========================

Manages character bibles, scene tracking, and generation history
to maintain consistency across video series episodes.

Components:
- CharacterBible: Character definitions and reference management
- SceneTracker: Generation history and scene continuity
- ReferenceManager: Reference image organization and retrieval
"""

from .character_manager import CharacterBible, Character, Location
from .scene_tracker import SceneTracker, Scene, Episode
from .reference_manager import ReferenceManager

__all__ = [
    "CharacterBible",
    "Character",
    "Location",
    "SceneTracker",
    "Scene",
    "Episode",
    "ReferenceManager",
]
