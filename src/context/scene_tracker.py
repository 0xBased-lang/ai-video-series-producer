"""
Scene Tracker
=============

Tracks generation history, manages scene continuity, and provides
context for frame chaining across episodes.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """A single scene/clip in an episode."""

    # Identity
    scene_id: str
    episode_id: str
    scene_number: int

    # Generation info
    prompt: str
    character_id: Optional[str] = None
    location_id: Optional[str] = None

    # Result
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    last_frame_path: Optional[str] = None

    # Generation parameters
    provider: Optional[str] = None
    model: Optional[str] = None
    seed: Optional[int] = None
    duration: int = 5
    resolution: str = "720p"
    reference_images: List[str] = field(default_factory=list)

    # Chaining
    previous_scene_id: Optional[str] = None
    next_scene_id: Optional[str] = None

    # Quality
    quality_score: Optional[float] = None
    consistency_score: Optional[float] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Status
    status: str = "pending"  # pending, generating, completed, failed
    error_message: Optional[str] = None
    take_number: int = 1

    # Full generation params for reproducibility
    generation_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        """Create from dictionary."""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("completed_at"), str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**data)


@dataclass
class Episode:
    """An episode containing multiple scenes."""

    episode_id: str
    series_id: str
    episode_number: int
    title: str = ""
    description: str = ""

    # Scenes in order
    scene_ids: List[str] = field(default_factory=list)

    # Status
    status: str = "draft"  # draft, in_progress, completed, published
    total_duration: float = 0.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return data


class SceneTracker:
    """
    Tracks all scenes and episodes in a video series.

    Provides:
    - Scene generation history
    - Frame chaining context
    - Reproducibility through parameter storage
    - Quality tracking
    """

    def __init__(self, db_path: Union[str, Path] = "context/generations/history.db"):
        """
        Initialize the scene tracker.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory caches
        self._scenes: Dict[str, Scene] = {}
        self._episodes: Dict[str, Episode] = {}

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Scenes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                scene_id TEXT PRIMARY KEY,
                episode_id TEXT,
                scene_number INTEGER,
                prompt TEXT,
                character_id TEXT,
                location_id TEXT,
                video_path TEXT,
                video_url TEXT,
                thumbnail_path TEXT,
                last_frame_path TEXT,
                provider TEXT,
                model TEXT,
                seed INTEGER,
                duration INTEGER,
                resolution TEXT,
                reference_images TEXT,
                previous_scene_id TEXT,
                next_scene_id TEXT,
                quality_score REAL,
                consistency_score REAL,
                created_at TEXT,
                completed_at TEXT,
                status TEXT,
                error_message TEXT,
                take_number INTEGER,
                generation_params TEXT
            )
        """)

        # Episodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                series_id TEXT,
                episode_number INTEGER,
                title TEXT,
                description TEXT,
                scene_ids TEXT,
                status TEXT,
                total_duration REAL,
                created_at TEXT,
                completed_at TEXT
            )
        """)

        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenes_episode
            ON scenes(episode_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenes_status
            ON scenes(status)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Initialized scene tracker database at {self.db_path}")

    # -------------------------------------------------------------------------
    # Scene Management
    # -------------------------------------------------------------------------

    def create_scene(
        self,
        episode_id: str,
        scene_number: int,
        prompt: str,
        character_id: Optional[str] = None,
        location_id: Optional[str] = None,
        **kwargs,
    ) -> Scene:
        """
        Create a new scene.

        Args:
            episode_id: Episode this scene belongs to
            scene_number: Order in the episode
            prompt: Generation prompt
            character_id: Character identifier
            location_id: Location identifier
            **kwargs: Additional scene parameters

        Returns:
            New Scene object
        """
        scene_id = f"{episode_id}_scene_{scene_number:03d}"

        # Handle take numbers (multiple attempts)
        existing = self.get_scene(scene_id)
        take_number = 1
        if existing:
            take_number = existing.take_number + 1
            scene_id = f"{scene_id}_take_{take_number:02d}"

        scene = Scene(
            scene_id=scene_id,
            episode_id=episode_id,
            scene_number=scene_number,
            prompt=prompt,
            character_id=character_id,
            location_id=location_id,
            take_number=take_number,
            **kwargs,
        )

        # Link to previous scene
        previous_scene = self.get_last_scene_in_episode(episode_id)
        if previous_scene:
            scene.previous_scene_id = previous_scene.scene_id
            previous_scene.next_scene_id = scene.scene_id
            self.save_scene(previous_scene)

        self.save_scene(scene)

        logger.info(f"Created scene {scene_id}")
        return scene

    def save_scene(self, scene: Scene) -> None:
        """Save a scene to the database."""
        self._scenes[scene.scene_id] = scene

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO scenes (
                scene_id, episode_id, scene_number, prompt, character_id,
                location_id, video_path, video_url, thumbnail_path,
                last_frame_path, provider, model, seed, duration, resolution,
                reference_images, previous_scene_id, next_scene_id,
                quality_score, consistency_score, created_at, completed_at,
                status, error_message, take_number, generation_params
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scene.scene_id,
            scene.episode_id,
            scene.scene_number,
            scene.prompt,
            scene.character_id,
            scene.location_id,
            scene.video_path,
            scene.video_url,
            scene.thumbnail_path,
            scene.last_frame_path,
            scene.provider,
            scene.model,
            scene.seed,
            scene.duration,
            scene.resolution,
            json.dumps(scene.reference_images),
            scene.previous_scene_id,
            scene.next_scene_id,
            scene.quality_score,
            scene.consistency_score,
            scene.created_at.isoformat() if scene.created_at else None,
            scene.completed_at.isoformat() if scene.completed_at else None,
            scene.status,
            scene.error_message,
            scene.take_number,
            json.dumps(scene.generation_params),
        ))

        conn.commit()
        conn.close()

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get a scene by ID."""
        if scene_id in self._scenes:
            return self._scenes[scene_id]

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM scenes WHERE scene_id = ?", (scene_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            scene = self._row_to_scene(dict(row))
            self._scenes[scene_id] = scene
            return scene

        return None

    def _row_to_scene(self, row: Dict) -> Scene:
        """Convert database row to Scene object."""
        return Scene(
            scene_id=row["scene_id"],
            episode_id=row["episode_id"],
            scene_number=row["scene_number"],
            prompt=row["prompt"],
            character_id=row["character_id"],
            location_id=row["location_id"],
            video_path=row["video_path"],
            video_url=row["video_url"],
            thumbnail_path=row["thumbnail_path"],
            last_frame_path=row["last_frame_path"],
            provider=row["provider"],
            model=row["model"],
            seed=row["seed"],
            duration=row["duration"] or 5,
            resolution=row["resolution"] or "720p",
            reference_images=json.loads(row["reference_images"] or "[]"),
            previous_scene_id=row["previous_scene_id"],
            next_scene_id=row["next_scene_id"],
            quality_score=row["quality_score"],
            consistency_score=row["consistency_score"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            status=row["status"] or "pending",
            error_message=row["error_message"],
            take_number=row["take_number"] or 1,
            generation_params=json.loads(row["generation_params"] or "{}"),
        )

    def get_scenes_for_episode(self, episode_id: str) -> List[Scene]:
        """Get all scenes for an episode, in order."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM scenes
            WHERE episode_id = ?
            ORDER BY scene_number, take_number DESC
        """, (episode_id,))

        rows = cursor.fetchall()
        conn.close()

        scenes = [self._row_to_scene(dict(row)) for row in rows]

        # Keep only latest take for each scene number
        latest_scenes = {}
        for scene in scenes:
            key = scene.scene_number
            if key not in latest_scenes or scene.take_number > latest_scenes[key].take_number:
                latest_scenes[key] = scene

        return sorted(latest_scenes.values(), key=lambda s: s.scene_number)

    def get_last_scene_in_episode(self, episode_id: str) -> Optional[Scene]:
        """Get the last scene in an episode."""
        scenes = self.get_scenes_for_episode(episode_id)
        return scenes[-1] if scenes else None

    def update_scene_status(
        self,
        scene_id: str,
        status: str,
        video_path: Optional[str] = None,
        video_url: Optional[str] = None,
        last_frame_path: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> Optional[Scene]:
        """Update a scene's status and results."""
        scene = self.get_scene(scene_id)
        if not scene:
            return None

        scene.status = status

        if video_path:
            scene.video_path = video_path
        if video_url:
            scene.video_url = video_url
        if last_frame_path:
            scene.last_frame_path = last_frame_path
        if error_message:
            scene.error_message = error_message

        if status == "completed":
            scene.completed_at = datetime.now()

        # Update any additional kwargs
        for key, value in kwargs.items():
            if hasattr(scene, key):
                setattr(scene, key, value)

        self.save_scene(scene)
        return scene

    # -------------------------------------------------------------------------
    # Episode Management
    # -------------------------------------------------------------------------

    def create_episode(
        self,
        series_id: str,
        episode_number: int,
        title: str = "",
        description: str = "",
    ) -> Episode:
        """Create a new episode."""
        episode_id = f"{series_id}_ep_{episode_number:03d}"

        episode = Episode(
            episode_id=episode_id,
            series_id=series_id,
            episode_number=episode_number,
            title=title,
            description=description,
        )

        self.save_episode(episode)

        logger.info(f"Created episode {episode_id}")
        return episode

    def save_episode(self, episode: Episode) -> None:
        """Save an episode to the database."""
        self._episodes[episode.episode_id] = episode

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO episodes (
                episode_id, series_id, episode_number, title, description,
                scene_ids, status, total_duration, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            episode.episode_id,
            episode.series_id,
            episode.episode_number,
            episode.title,
            episode.description,
            json.dumps(episode.scene_ids),
            episode.status,
            episode.total_duration,
            episode.created_at.isoformat() if episode.created_at else None,
            episode.completed_at.isoformat() if episode.completed_at else None,
        ))

        conn.commit()
        conn.close()

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Get an episode by ID."""
        if episode_id in self._episodes:
            return self._episodes[episode_id]

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM episodes WHERE episode_id = ?", (episode_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            episode = Episode(
                episode_id=row["episode_id"],
                series_id=row["series_id"],
                episode_number=row["episode_number"],
                title=row["title"],
                description=row["description"],
                scene_ids=json.loads(row["scene_ids"] or "[]"),
                status=row["status"],
                total_duration=row["total_duration"] or 0.0,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            )
            self._episodes[episode_id] = episode
            return episode

        return None

    # -------------------------------------------------------------------------
    # Chaining Support
    # -------------------------------------------------------------------------

    def get_previous_scene_context(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """
        Get context from the previous scene for chaining.

        Returns dict with last_frame_path, seed, and other useful info.
        """
        scene = self.get_scene(scene_id)
        if not scene or not scene.previous_scene_id:
            return None

        prev_scene = self.get_scene(scene.previous_scene_id)
        if not prev_scene:
            return None

        return {
            "scene_id": prev_scene.scene_id,
            "last_frame_path": prev_scene.last_frame_path,
            "video_path": prev_scene.video_path,
            "seed": prev_scene.seed,
            "model": prev_scene.model,
            "provider": prev_scene.provider,
            "prompt": prev_scene.prompt,
            "character_id": prev_scene.character_id,
        }

    def get_chain_context(self, episode_id: str) -> List[Dict[str, Any]]:
        """Get full chain context for an episode."""
        scenes = self.get_scenes_for_episode(episode_id)
        return [
            {
                "scene_number": s.scene_number,
                "scene_id": s.scene_id,
                "status": s.status,
                "last_frame_path": s.last_frame_path,
                "seed": s.seed,
            }
            for s in scenes
        ]

    # -------------------------------------------------------------------------
    # Export/Import
    # -------------------------------------------------------------------------

    def export_episode_metadata(self, episode_id: str) -> Dict[str, Any]:
        """Export episode and scene metadata for sharing/backup."""
        episode = self.get_episode(episode_id)
        if not episode:
            return {}

        scenes = self.get_scenes_for_episode(episode_id)

        return {
            "episode": episode.to_dict(),
            "scenes": [s.to_dict() for s in scenes],
            "exported_at": datetime.now().isoformat(),
        }

    def export_to_json(self, output_path: Union[str, Path]) -> None:
        """Export all data to JSON file."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get all episodes
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM episodes")
        episodes = [dict(row) for row in cursor.fetchall()]

        # Get all scenes
        cursor.execute("SELECT * FROM scenes")
        scenes = [dict(row) for row in cursor.fetchall()]

        conn.close()

        data = {
            "episodes": episodes,
            "scenes": scenes,
            "exported_at": datetime.now().isoformat(),
        }

        output_path = Path(output_path)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported scene data to {output_path}")
