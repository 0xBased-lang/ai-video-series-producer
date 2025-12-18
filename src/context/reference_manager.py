"""
Reference Manager
=================

Manages reference images for characters, locations, and styles.
Handles image organization, optimization, and retrieval.
"""

import hashlib
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Union
import json

logger = logging.getLogger(__name__)


@dataclass
class ReferenceImage:
    """A reference image with metadata."""
    path: str
    category: str  # character, location, style, prop
    entity_id: str  # character_id, location_id, etc.
    variant: str = "default"  # front, profile, full_body, etc.
    hash: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: Optional[int] = None


class ReferenceManager:
    """
    Manages reference images for the video series.

    Provides:
    - Organized storage structure
    - Image optimization
    - Quick retrieval by entity
    - Hash-based deduplication
    """

    def __init__(
        self,
        base_path: Union[str, Path] = "references",
        auto_create: bool = True,
    ):
        """
        Initialize the reference manager.

        Args:
            base_path: Base directory for reference images
            auto_create: Create directories if they don't exist
        """
        self.base_path = Path(base_path)

        # Subdirectories
        self.characters_path = self.base_path / "characters"
        self.locations_path = self.base_path / "locations"
        self.styles_path = self.base_path / "styles"
        self.props_path = self.base_path / "props"
        self.frames_path = self.base_path / "frames"  # Extracted frames

        if auto_create:
            self._create_directories()

        # Index of all references
        self._index: Dict[str, ReferenceImage] = {}
        self._load_index()

    def _create_directories(self) -> None:
        """Create the directory structure."""
        for path in [
            self.characters_path,
            self.locations_path,
            self.styles_path,
            self.props_path,
            self.frames_path,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """Load the reference index from disk."""
        index_path = self.base_path / "index.json"
        if index_path.exists():
            with open(index_path, "r") as f:
                data = json.load(f)
                for key, ref_data in data.items():
                    self._index[key] = ReferenceImage(**ref_data)

    def _save_index(self) -> None:
        """Save the reference index to disk."""
        index_path = self.base_path / "index.json"
        data = {
            key: {
                "path": ref.path,
                "category": ref.category,
                "entity_id": ref.entity_id,
                "variant": ref.variant,
                "hash": ref.hash,
                "width": ref.width,
                "height": ref.height,
                "size_bytes": ref.size_bytes,
            }
            for key, ref in self._index.items()
        }
        with open(index_path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _compute_hash(file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]

    # -------------------------------------------------------------------------
    # Adding References
    # -------------------------------------------------------------------------

    def add_character_reference(
        self,
        character_id: str,
        source_path: Union[str, Path],
        variant: str = "default",
        copy: bool = True,
    ) -> ReferenceImage:
        """
        Add a reference image for a character.

        Args:
            character_id: Character identifier
            source_path: Path to the source image
            variant: Variant name (front, profile, full_body, etc.)
            copy: Whether to copy the file or just reference it

        Returns:
            ReferenceImage object
        """
        return self._add_reference(
            category="character",
            entity_id=character_id,
            source_path=source_path,
            variant=variant,
            copy=copy,
        )

    def add_location_reference(
        self,
        location_id: str,
        source_path: Union[str, Path],
        variant: str = "default",
        copy: bool = True,
    ) -> ReferenceImage:
        """Add a reference image for a location."""
        return self._add_reference(
            category="location",
            entity_id=location_id,
            source_path=source_path,
            variant=variant,
            copy=copy,
        )

    def add_style_reference(
        self,
        style_name: str,
        source_path: Union[str, Path],
        copy: bool = True,
    ) -> ReferenceImage:
        """Add a style reference image."""
        return self._add_reference(
            category="style",
            entity_id=style_name,
            source_path=source_path,
            variant="default",
            copy=copy,
        )

    def _add_reference(
        self,
        category: str,
        entity_id: str,
        source_path: Union[str, Path],
        variant: str,
        copy: bool,
    ) -> ReferenceImage:
        """Internal method to add a reference."""
        source_path = Path(source_path)

        if not source_path.exists():
            raise FileNotFoundError(f"Source image not found: {source_path}")

        # Determine destination path
        category_path = {
            "character": self.characters_path,
            "location": self.locations_path,
            "style": self.styles_path,
            "prop": self.props_path,
        }.get(category, self.base_path)

        # Create entity subdirectory
        entity_path = category_path / entity_id
        entity_path.mkdir(parents=True, exist_ok=True)

        # Destination filename
        ext = source_path.suffix.lower()
        dest_filename = f"{variant}{ext}"
        dest_path = entity_path / dest_filename

        # Copy or reference
        if copy:
            shutil.copy2(source_path, dest_path)
            final_path = str(dest_path)
        else:
            final_path = str(source_path)

        # Compute hash and get size
        file_hash = self._compute_hash(Path(final_path))
        size_bytes = Path(final_path).stat().st_size

        # Try to get dimensions (requires PIL)
        width, height = None, None
        try:
            from PIL import Image
            with Image.open(final_path) as img:
                width, height = img.size
        except ImportError:
            pass

        # Create reference object
        ref = ReferenceImage(
            path=final_path,
            category=category,
            entity_id=entity_id,
            variant=variant,
            hash=file_hash,
            width=width,
            height=height,
            size_bytes=size_bytes,
        )

        # Add to index
        key = f"{category}:{entity_id}:{variant}"
        self._index[key] = ref
        self._save_index()

        logger.info(f"Added {category} reference: {key}")
        return ref

    # -------------------------------------------------------------------------
    # Retrieving References
    # -------------------------------------------------------------------------

    def get_character_references(
        self,
        character_id: str,
        variants: Optional[List[str]] = None,
        max_count: Optional[int] = None,
    ) -> List[str]:
        """
        Get reference image paths for a character.

        Args:
            character_id: Character identifier
            variants: Specific variants to get (e.g., ["front", "profile"])
            max_count: Maximum number of images to return

        Returns:
            List of image paths
        """
        return self._get_references(
            category="character",
            entity_id=character_id,
            variants=variants,
            max_count=max_count,
        )

    def get_location_references(
        self,
        location_id: str,
        variants: Optional[List[str]] = None,
    ) -> List[str]:
        """Get reference image paths for a location."""
        return self._get_references(
            category="location",
            entity_id=location_id,
            variants=variants,
        )

    def get_style_reference(self, style_name: str) -> Optional[str]:
        """Get the style reference image path."""
        refs = self._get_references(
            category="style",
            entity_id=style_name,
            max_count=1,
        )
        return refs[0] if refs else None

    def _get_references(
        self,
        category: str,
        entity_id: str,
        variants: Optional[List[str]] = None,
        max_count: Optional[int] = None,
    ) -> List[str]:
        """Internal method to get references."""
        prefix = f"{category}:{entity_id}:"

        refs = [
            ref.path
            for key, ref in self._index.items()
            if key.startswith(prefix)
            and (variants is None or ref.variant in variants)
        ]

        # Prioritize certain variants
        priority = ["front", "primary", "main", "default", "three_quarter", "full_body"]

        def sort_key(path: str) -> int:
            for ref in self._index.values():
                if ref.path == path:
                    try:
                        return priority.index(ref.variant)
                    except ValueError:
                        return len(priority)
            return len(priority)

        refs.sort(key=sort_key)

        if max_count:
            refs = refs[:max_count]

        return refs

    # -------------------------------------------------------------------------
    # Frame Extraction
    # -------------------------------------------------------------------------

    def save_extracted_frame(
        self,
        scene_id: str,
        frame_data: bytes,
        frame_type: str = "last",  # first, last, thumbnail
        format: str = "jpg",
    ) -> str:
        """
        Save an extracted frame from a video.

        Args:
            scene_id: Scene identifier
            frame_data: Raw image bytes
            frame_type: Type of frame (first, last, thumbnail)
            format: Image format

        Returns:
            Path to saved frame
        """
        # Create scene directory
        scene_path = self.frames_path / scene_id
        scene_path.mkdir(parents=True, exist_ok=True)

        # Save frame
        frame_filename = f"{frame_type}_frame.{format}"
        frame_path = scene_path / frame_filename

        with open(frame_path, "wb") as f:
            f.write(frame_data)

        logger.debug(f"Saved {frame_type} frame for {scene_id}: {frame_path}")
        return str(frame_path)

    def get_last_frame(self, scene_id: str) -> Optional[str]:
        """Get the last frame path for a scene."""
        scene_path = self.frames_path / scene_id
        for ext in ["jpg", "png", "webp"]:
            frame_path = scene_path / f"last_frame.{ext}"
            if frame_path.exists():
                return str(frame_path)
        return None

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def list_characters(self) -> List[str]:
        """List all characters with references."""
        characters = set()
        for key in self._index:
            if key.startswith("character:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    characters.add(parts[1])
        return sorted(characters)

    def list_locations(self) -> List[str]:
        """List all locations with references."""
        locations = set()
        for key in self._index:
            if key.startswith("location:"):
                parts = key.split(":")
                if len(parts) >= 2:
                    locations.add(parts[1])
        return sorted(locations)

    def get_reference_count(self, entity_id: str) -> int:
        """Get the number of references for an entity."""
        count = 0
        for key in self._index:
            if f":{entity_id}:" in key:
                count += 1
        return count

    def cleanup_orphaned(self) -> int:
        """Remove references to non-existent files."""
        removed = 0
        keys_to_remove = []

        for key, ref in self._index.items():
            if not Path(ref.path).exists():
                keys_to_remove.append(key)
                removed += 1

        for key in keys_to_remove:
            del self._index[key]

        if removed:
            self._save_index()
            logger.info(f"Removed {removed} orphaned references")

        return removed
