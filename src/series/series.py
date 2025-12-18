"""
Series Models
=============

Core data models for series, episodes, and scenes.
"""

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class SeriesStatus(Enum):
    """Status of a series."""

    DRAFT = "draft"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EpisodeStatus(Enum):
    """Status of an episode."""

    PLANNED = "planned"
    SCRIPTED = "scripted"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    PUBLISHED = "published"


class SceneStatus(Enum):
    """Status of a scene."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVISION = "needs_revision"


@dataclass
class Scene:
    """
    A single scene within an episode.

    Scenes are the atomic unit of video generation - each scene
    produces one video clip that maintains character and style consistency.
    """

    # Identity
    scene_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    scene_number: int = 1
    take_number: int = 1

    # Content
    action: str = ""  # What happens in the scene
    dialogue: Optional[str] = None
    notes: Optional[str] = None

    # Characters and location
    character_ids: List[str] = field(default_factory=list)
    location_id: Optional[str] = None

    # Camera
    camera_direction: Optional[str] = None  # e.g., "close-up", "wide shot", "tracking"
    camera_movement: Optional[str] = None  # e.g., "pan left", "zoom in", "steady"

    # Technical
    duration: int = 5  # seconds
    aspect_ratio: str = "16:9"
    with_audio: bool = False

    # Generation
    prompt_override: Optional[str] = None  # Custom prompt if auto-generation not desired
    reference_images: List[str] = field(default_factory=list)
    first_frame: Optional[str] = None  # For chaining
    seed: Optional[int] = None

    # Results
    status: SceneStatus = SceneStatus.PENDING
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    last_frame_path: Optional[str] = None
    thumbnail_path: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    generation_time_seconds: Optional[float] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "scene_id": self.scene_id,
            "scene_number": self.scene_number,
            "take_number": self.take_number,
            "action": self.action,
            "dialogue": self.dialogue,
            "character_ids": self.character_ids,
            "location_id": self.location_id,
            "camera_direction": self.camera_direction,
            "duration": self.duration,
            "status": self.status.value,
            "video_path": self.video_path,
            "video_url": self.video_url,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Episode:
    """
    An episode containing multiple scenes.

    Episodes group related scenes together and manage the overall
    narrative flow and production status.
    """

    # Identity
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    episode_number: int = 1
    title: str = ""
    description: str = ""

    # Content
    scenes: List[Scene] = field(default_factory=list)

    # Production
    status: EpisodeStatus = EpisodeStatus.PLANNED
    estimated_duration_seconds: int = 0
    actual_duration_seconds: int = 0

    # Output
    output_path: Optional[str] = None
    combined_video_path: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def add_scene(self, scene: Scene) -> None:
        """Add a scene to the episode."""
        scene.scene_number = len(self.scenes) + 1
        self.scenes.append(scene)
        self._update_estimated_duration()

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get a scene by ID."""
        for scene in self.scenes:
            if scene.scene_id == scene_id:
                return scene
        return None

    def get_pending_scenes(self) -> List[Scene]:
        """Get all scenes that need generation."""
        return [s for s in self.scenes if s.status == SceneStatus.PENDING]

    def get_completed_scenes(self) -> List[Scene]:
        """Get all completed scenes."""
        return [s for s in self.scenes if s.status == SceneStatus.COMPLETED]

    def _update_estimated_duration(self) -> None:
        """Update estimated duration based on scenes."""
        self.estimated_duration_seconds = sum(s.duration for s in self.scenes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "episode_id": self.episode_id,
            "episode_number": self.episode_number,
            "title": self.title,
            "description": self.description,
            "scenes": [s.to_dict() for s in self.scenes],
            "status": self.status.value,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Series:
    """
    A video series containing multiple episodes.

    The Series is the top-level container that holds:
    - Series metadata (name, description, genre)
    - Character definitions
    - Visual style settings
    - Episodes and their scenes
    - Production state and history
    """

    # Identity
    series_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    genre: str = ""

    # Content
    episodes: List[Episode] = field(default_factory=list)

    # Characters (IDs referencing CharacterBible)
    character_ids: List[str] = field(default_factory=list)

    # Production settings
    status: SeriesStatus = SeriesStatus.DRAFT
    default_provider: str = "fal"
    default_model: str = "kling-2.5"
    default_duration: int = 5
    default_aspect_ratio: str = "16:9"

    # Quality settings
    quality_preset: str = "balanced"
    target_consistency_score: float = 0.8

    # Output
    output_path: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    def add_episode(self, episode: Episode) -> None:
        """Add an episode to the series."""
        episode.episode_number = len(self.episodes) + 1
        self.episodes.append(episode)
        self.updated_at = datetime.now()

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get an episode by ID."""
        for episode in self.episodes:
            if episode.episode_id == episode_id:
                return episode
        return None

    def get_episode_by_number(self, number: int) -> Optional[Episode]:
        """Get an episode by number."""
        for episode in self.episodes:
            if episode.episode_number == number:
                return episode
        return None

    def get_latest_episode(self) -> Optional[Episode]:
        """Get the most recent episode."""
        if not self.episodes:
            return None
        return max(self.episodes, key=lambda e: e.episode_number)

    def get_total_scenes(self) -> int:
        """Get total number of scenes across all episodes."""
        return sum(len(e.scenes) for e in self.episodes)

    def get_completed_scenes(self) -> int:
        """Get count of completed scenes."""
        return sum(len(e.get_completed_scenes()) for e in self.episodes)

    def get_production_progress(self) -> float:
        """Get production progress as a percentage (0.0 - 1.0)."""
        total = self.get_total_scenes()
        if total == 0:
            return 0.0
        return self.get_completed_scenes() / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "series_id": self.series_id,
            "name": self.name,
            "description": self.description,
            "genre": self.genre,
            "episodes": [e.to_dict() for e in self.episodes],
            "character_ids": self.character_ids,
            "status": self.status.value,
            "default_provider": self.default_provider,
            "default_model": self.default_model,
            "quality_preset": self.quality_preset,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Series":
        """Create Series from dictionary."""
        series = cls(
            series_id=data.get("series_id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            description=data.get("description", ""),
            genre=data.get("genre", ""),
            character_ids=data.get("character_ids", []),
            status=SeriesStatus(data.get("status", "draft")),
            default_provider=data.get("default_provider", "fal"),
            default_model=data.get("default_model", "kling-2.5"),
            quality_preset=data.get("quality_preset", "balanced"),
            version=data.get("version", "1.0.0"),
        )

        # Parse episodes
        for ep_data in data.get("episodes", []):
            episode = Episode(
                episode_id=ep_data.get("episode_id"),
                episode_number=ep_data.get("episode_number", 1),
                title=ep_data.get("title", ""),
                description=ep_data.get("description", ""),
                status=EpisodeStatus(ep_data.get("status", "planned")),
            )

            # Parse scenes
            for scene_data in ep_data.get("scenes", []):
                scene = Scene(
                    scene_id=scene_data.get("scene_id"),
                    scene_number=scene_data.get("scene_number", 1),
                    action=scene_data.get("action", ""),
                    character_ids=scene_data.get("character_ids", []),
                    location_id=scene_data.get("location_id"),
                    duration=scene_data.get("duration", 5),
                    status=SceneStatus(scene_data.get("status", "pending")),
                    video_path=scene_data.get("video_path"),
                )
                episode.scenes.append(scene)

            series.episodes.append(episode)

        return series
