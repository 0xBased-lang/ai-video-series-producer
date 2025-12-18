"""
Video Producer
==============

Main orchestration class for generating videos with consistent
characters and style across a series.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
import yaml

from ..api import get_provider, get_best_provider
from ..api.base import GenerationRequest, VideoGenerationResult, GenerationStatus
from ..context import CharacterBible, SceneTracker, ReferenceManager

logger = logging.getLogger(__name__)


class VideoProducer:
    """
    Main class for producing AI-generated video series.

    Handles:
    - Character and style consistency
    - Scene generation and chaining
    - Context preservation
    - Multi-provider support
    """

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        character_bible_path: Optional[Union[str, Path]] = None,
        output_path: Union[str, Path] = "./output",
        provider: Optional[str] = None,
    ):
        """
        Initialize the video producer.

        Args:
            config_path: Path to defaults.yaml configuration
            character_bible_path: Path to character_bible.yaml
            output_path: Base path for output files
            provider: Default provider name (or auto-select)
        """
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize components
        self.character_bible = CharacterBible(character_bible_path)
        self.scene_tracker = SceneTracker(
            db_path=self.output_path / "context" / "history.db"
        )
        self.reference_manager = ReferenceManager(
            base_path=self.output_path / "references"
        )

        # Provider setup
        self.default_provider_name = provider or self.config.get("default_provider", "fal")
        self._providers: Dict[str, Any] = {}

        logger.info(f"VideoProducer initialized")
        logger.info(f"  Output path: {self.output_path}")
        logger.info(f"  Default provider: {self.default_provider_name}")

    def _load_config(self, config_path: Optional[Union[str, Path]]) -> Dict:
        """Load configuration from file or use defaults."""
        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                return yaml.safe_load(f)

        # Default configuration
        return {
            "default_provider": "fal",
            "default_model": "kling-2.5",
            "default_duration": 5,
            "default_resolution": "720p",
            "default_aspect_ratio": "16:9",
            "max_retries": 3,
        }

    def _get_provider(self, provider_name: Optional[str] = None):
        """Get or create a provider instance."""
        name = provider_name or self.default_provider_name

        if name not in self._providers:
            self._providers[name] = get_provider(name)

        return self._providers[name]

    # -------------------------------------------------------------------------
    # High-Level Generation Methods
    # -------------------------------------------------------------------------

    async def generate_scene(
        self,
        character_id: str,
        action: str,
        location_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        scene_number: Optional[int] = None,
        duration: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        use_references: bool = True,
        chain_from_previous: bool = True,
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Generate a scene with a character.

        This is the main method for generating video clips that maintain
        character consistency across the series.

        Args:
            character_id: ID of the character (from character bible)
            action: What the character is doing
            location_id: Optional location ID
            episode_id: Episode this scene belongs to
            scene_number: Scene number within episode
            duration: Video duration in seconds
            provider: Override default provider
            model: Override default model
            use_references: Whether to use reference images
            chain_from_previous: Whether to chain from previous scene
            **kwargs: Additional generation parameters

        Returns:
            VideoGenerationResult with the generated video
        """
        # Build the prompt using character bible
        prompt = self.character_bible.build_scene_prompt(
            character_id=character_id,
            action=action,
            location_id=location_id,
            camera_direction=kwargs.get("camera_direction"),
            outfit_variant=kwargs.get("outfit_variant"),
        )

        # Get reference images
        reference_images = []
        if use_references:
            reference_images = self.character_bible.get_reference_images_for_scene(
                character_id=character_id,
                location_id=location_id,
                max_images=4,
            )

        # Get chaining context
        first_frame = None
        if chain_from_previous and episode_id:
            prev_context = self._get_chaining_context(episode_id)
            if prev_context:
                first_frame = prev_context.get("last_frame_path")
                # Modify prompt for continuation
                prompt = f"Seamless continuation. {prompt}"

        # Create scene record
        scene = None
        if episode_id:
            scene = self.scene_tracker.create_scene(
                episode_id=episode_id,
                scene_number=scene_number or self._get_next_scene_number(episode_id),
                prompt=prompt,
                character_id=character_id,
                location_id=location_id,
                reference_images=reference_images,
            )

        # Build generation request
        request = GenerationRequest(
            prompt=prompt,
            reference_images=reference_images,
            first_frame=first_frame,
            duration=duration or self.config.get("default_duration", 5),
            resolution=kwargs.get("resolution", self.config.get("default_resolution", "720p")),
            aspect_ratio=kwargs.get("aspect_ratio", self.config.get("default_aspect_ratio", "16:9")),
            negative_prompt=self.character_bible.get_negative_prompt(),
            model=model or self.config.get("default_model"),
            seed=kwargs.get("seed"),
            with_audio=kwargs.get("with_audio", False),
        )

        # Generate
        provider_instance = self._get_provider(provider)

        try:
            if scene:
                self.scene_tracker.update_scene_status(
                    scene.scene_id, "generating"
                )

            result = await provider_instance.generate_video(request)

            # Download video if successful
            if result.status == GenerationStatus.COMPLETED and result.video_url:
                video_filename = self._generate_filename(
                    character_id, episode_id, scene_number
                )
                video_path = self.output_path / "videos" / video_filename
                video_path.parent.mkdir(parents=True, exist_ok=True)

                await provider_instance.download_video(result, video_path)

                # Extract last frame for chaining
                last_frame_path = await self._extract_last_frame(
                    result.video_path,
                    scene.scene_id if scene else None,
                )
                result.last_frame_path = last_frame_path

            # Update scene record
            if scene:
                self.scene_tracker.update_scene_status(
                    scene.scene_id,
                    "completed" if result.status == GenerationStatus.COMPLETED else "failed",
                    video_path=result.video_path,
                    video_url=result.video_url,
                    last_frame_path=result.last_frame_path,
                    seed=result.seed,
                    provider=result.provider,
                    model=result.model,
                    error_message=result.error_message,
                )

            return result

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            if scene:
                self.scene_tracker.update_scene_status(
                    scene.scene_id, "failed", error_message=str(e)
                )
            raise

    async def generate_episode(
        self,
        series_id: str,
        episode_number: int,
        scenes: List[Dict[str, Any]],
        title: str = "",
        **kwargs,
    ) -> List[VideoGenerationResult]:
        """
        Generate an entire episode from scene definitions.

        Args:
            series_id: Series identifier
            episode_number: Episode number
            scenes: List of scene definitions, each containing:
                - character_id: Character for the scene
                - action: What happens
                - location_id: Optional location
                - duration: Optional duration
            title: Episode title
            **kwargs: Default parameters for all scenes

        Returns:
            List of VideoGenerationResult objects
        """
        # Create episode
        episode = self.scene_tracker.create_episode(
            series_id=series_id,
            episode_number=episode_number,
            title=title,
        )

        results = []

        for i, scene_def in enumerate(scenes):
            logger.info(f"Generating scene {i + 1}/{len(scenes)}")

            result = await self.generate_scene(
                episode_id=episode.episode_id,
                scene_number=i + 1,
                chain_from_previous=i > 0,  # Chain after first scene
                **scene_def,
                **kwargs,
            )

            results.append(result)

            # Small delay between generations
            await asyncio.sleep(1)

        return results

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    async def quick_generate(
        self,
        prompt: str,
        reference_image: Optional[str] = None,
        duration: int = 5,
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Quick generation without character bible.

        Useful for testing or one-off generations.

        Args:
            prompt: Generation prompt
            reference_image: Optional reference image path
            duration: Video duration
            **kwargs: Additional parameters

        Returns:
            VideoGenerationResult
        """
        request = GenerationRequest(
            prompt=prompt,
            reference_images=[reference_image] if reference_image else [],
            duration=duration,
            **kwargs,
        )

        provider = self._get_provider()
        return await provider.generate_video(request)

    async def regenerate_scene(
        self,
        scene_id: str,
        prompt_override: Optional[str] = None,
        **kwargs,
    ) -> VideoGenerationResult:
        """
        Regenerate a scene with optional modifications.

        Args:
            scene_id: ID of the scene to regenerate
            prompt_override: Optional new prompt
            **kwargs: Override parameters

        Returns:
            VideoGenerationResult
        """
        scene = self.scene_tracker.get_scene(scene_id)
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")

        # Use original parameters with overrides
        return await self.generate_scene(
            character_id=scene.character_id,
            action="",  # Will use prompt override or original
            location_id=scene.location_id,
            episode_id=scene.episode_id,
            scene_number=scene.scene_number,
            duration=kwargs.get("duration", scene.duration),
            provider=kwargs.get("provider", scene.provider),
            model=kwargs.get("model", scene.model),
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_chaining_context(self, episode_id: str) -> Optional[Dict[str, Any]]:
        """Get context for chaining from previous scene."""
        last_scene = self.scene_tracker.get_last_scene_in_episode(episode_id)
        if last_scene and last_scene.status == "completed":
            return {
                "scene_id": last_scene.scene_id,
                "last_frame_path": last_scene.last_frame_path,
                "seed": last_scene.seed,
            }
        return None

    def _get_next_scene_number(self, episode_id: str) -> int:
        """Get the next scene number for an episode."""
        scenes = self.scene_tracker.get_scenes_for_episode(episode_id)
        if not scenes:
            return 1
        return max(s.scene_number for s in scenes) + 1

    def _generate_filename(
        self,
        character_id: str,
        episode_id: Optional[str],
        scene_number: Optional[int],
    ) -> str:
        """Generate a filename for a video."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if episode_id and scene_number:
            return f"{episode_id}_scene{scene_number:03d}_{timestamp}.mp4"
        elif character_id:
            return f"{character_id}_{timestamp}.mp4"
        else:
            return f"video_{timestamp}.mp4"

    async def _extract_last_frame(
        self,
        video_path: Optional[str],
        scene_id: Optional[str],
    ) -> Optional[str]:
        """Extract the last frame from a video for chaining."""
        if not video_path or not Path(video_path).exists():
            return None

        try:
            # Use ffmpeg to extract last frame
            import subprocess

            frame_path = Path(video_path).with_suffix(".last_frame.jpg")

            # Get video duration first
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path,
                ],
                capture_output=True,
                text=True,
            )

            duration = float(result.stdout.strip())
            last_frame_time = max(0, duration - 0.1)

            # Extract frame
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(last_frame_time),
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",
                    str(frame_path),
                ],
                capture_output=True,
            )

            if frame_path.exists():
                # Save to reference manager if we have scene_id
                if scene_id:
                    self.reference_manager.save_extracted_frame(
                        scene_id,
                        frame_path.read_bytes(),
                        frame_type="last",
                    )
                return str(frame_path)

        except Exception as e:
            logger.warning(f"Could not extract last frame: {e}")

        return None

    # -------------------------------------------------------------------------
    # Configuration Methods
    # -------------------------------------------------------------------------

    def load_character_bible(self, path: Union[str, Path]) -> None:
        """Load a character bible from file."""
        self.character_bible.load(path)

    def set_default_provider(self, provider: str) -> None:
        """Set the default provider."""
        self.default_provider_name = provider

    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        from ..api import list_providers
        return list_providers()

    # -------------------------------------------------------------------------
    # Context Management
    # -------------------------------------------------------------------------

    def get_series_context(self, series_id: str) -> Dict[str, Any]:
        """
        Get the full context for a series.

        Useful for exporting or debugging.
        """
        return {
            "series": {
                "name": self.character_bible.series_name,
                "description": self.character_bible.series_description,
            },
            "characters": list(self.character_bible.characters.keys()),
            "locations": list(self.character_bible.locations.keys()),
            "style": {
                "modifiers": self.character_bible.visual_style.style_modifiers,
                "negative": self.character_bible.visual_style.negative_modifiers,
            },
        }

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            await provider.close()
        self._providers.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
